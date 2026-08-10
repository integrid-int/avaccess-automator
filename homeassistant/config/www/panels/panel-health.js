import {
  applyAssignment,
  applyRoutePlan,
  createEmptyAssignments,
  getAssignmentForProgram,
  getAssignmentForTv,
  listBusyEncoderIds,
  loadAssignments,
  resolveSendPresetId,
  saveAssignments,
} from "./assignment-store.js";
import {
  GUIDE_CHANNELS,
  PRESETS,
  SPECTRUM_ZIP,
  SPORTS,
  STORAGE_KEY,
  TOKENS,
  filterGuideChannels,
  range,
} from "./panel-data.js";
import { buildRoutePlan, stripedTvs } from "./route-planner.js";

const DEFAULT_STATE = {
  screen: "browse-sport",
  sportId: SPORTS[0]?.id ?? null,
  guideQuery: "",
  selectedContent: null,
  selectedTvs: [],
  selectedPresetId: null,
  destMode: "presets",
  contentMode: "sports",
  entryPath: "content",
  groupMode: null,
  selectedPrograms: [],
  lastPlan: null,
  liveCommit: false,
};

const LIVE_BLOCKED_WARNING = "Live blocked: inventory not ready";
const INVENTORY_JSON_URL = "/local/avaccess/inventory.json";

const SCREEN_TITLES = {
  "browse-sport": "Sports",
  "browse-guide": "Guide",
  "browse-tvs": "TVs",
  destination: "Destination",
  "content-picker": "Content Picker",
  "program-picker": "Program Picker",
};

class PanelHealth extends HTMLElement {
  constructor() {
    super();
    this._hass = null;
    this._panel = null;
    this._state = { ...DEFAULT_STATE };
    this._assignments = createEmptyAssignments();
    this._boundClick = this._onClick.bind(this);
    this._boundInput = this._onInput.bind(this);
    this._eventsBound = false;
    this._inventoryLiveReady = false;
    this._inventoryLoaded = false;
    this._liveCommitSynced = false;
  }

  get hass() {
    return this._hass;
  }

  set hass(hass) {
    this._hass = hass;
    this._syncLiveCommitFromHass();
    this.render();
  }

  set panel(panelConfig) {
    this._panel = panelConfig;
    this.render();
  }

  connectedCallback() {
    this._assignments = this._loadAssignments();
    if (!this._eventsBound) {
      this.addEventListener("click", this._boundClick);
      this.addEventListener("input", this._boundInput);
      this._eventsBound = true;
    }
    this._loadInventoryLiveReady();
    this.render();
  }

  disconnectedCallback() {
    if (this._eventsBound) {
      this.removeEventListener("click", this._boundClick);
      this.removeEventListener("input", this._boundInput);
      this._eventsBound = false;
    }
  }

  _loadAssignments() {
    const storage = this._storage();
    return storage ? loadAssignments(storage, STORAGE_KEY) : createEmptyAssignments();
  }

  _saveAssignments(assignments) {
    const storage = this._storage();
    if (storage) {
      saveAssignments(storage, STORAGE_KEY, assignments);
    }
    this._assignments = assignments;
  }

  _storage() {
    try {
      return globalThis.localStorage ?? null;
    } catch {
      return null;
    }
  }

  _setState(nextState) {
    this._state = { ...this._state, ...nextState };
    this.render();
  }

  async _loadInventoryLiveReady() {
    try {
      const response = await fetch(INVENTORY_JSON_URL);
      if (!response.ok) {
        this._inventoryLiveReady = false;
      } else {
        const inventory = await response.json();
        this._inventoryLiveReady = isInventoryLiveReady(inventory);
      }
    } catch {
      this._inventoryLiveReady = false;
    }
    this._inventoryLoaded = true;
    if (this._state.liveCommit && !this._inventoryLiveReady) {
      this._state = { ...this._state, liveCommit: false };
    }
    this._syncLiveCommitFromHass();
    if (this.isConnected) this.render();
  }

  _syncLiveCommitFromHass() {
    if (this._liveCommitSynced || !this._inventoryLoaded || !this._hass?.states) return;
    const entity = this._hass.states["input_boolean.avaccess_live_commit"];
    if (!entity) return;
    this._liveCommitSynced = true;
    const liveCommit = entity.state === "on" && this._inventoryLiveReady;
    if (this._state.liveCommit !== liveCommit) {
      this._state = { ...this._state, liveCommit };
    }
  }

  _planSendLabel() {
    return this._state.liveCommit ? "Live Send" : "Dry-run Send";
  }

  _renderLiveCommitToggle() {
    const ready = this._inventoryLiveReady;
    const active = this._state.liveCommit;
    const tip = ready
      ? "When on, Send executes IR+UDP via Home Assistant"
      : "Live blocked: fill inventory hostnames (no REPLACE_ME) and export inventory.json";
    return `
      <div class="live-commit-row">
        <button
          type="button"
          class="live-commit-toggle ${active ? "is-active" : ""}"
          data-action="toggle-live-commit"
          title="${escapeAttr(tip)}"
          ${ready ? "" : "disabled aria-disabled=\"true\""}
          aria-pressed="${active ? "true" : "false"}"
        >
          Live commit
        </button>
        <span class="live-commit-hint">${ready ? (active ? "Live" : "Dry-run") : "Inventory not live-ready"}</span>
      </div>
    `;
  }

  _captureGuideSearchCaret() {
    const active = this.querySelector?.('[data-action="guide-search"]');
    if (!active || document.activeElement !== active) return null;
    return {
      value: active.value,
      start: active.selectionStart,
      end: active.selectionEnd,
    };
  }

  _restoreGuideSearchCaret(snapshot) {
    if (!snapshot) return;
    const input = this.querySelector('[data-action="guide-search"]');
    if (!input) return;
    input.focus({ preventScroll: true });
    try {
      const start = snapshot.start ?? input.value.length;
      const end = snapshot.end ?? start;
      input.setSelectionRange(start, end);
    } catch {
      // Some input types reject selection ranges; focus alone is enough.
    }
  }

  _routeBadgeHtml(routeId) {
    const route = getAssignmentForProgram(this._assignments, routeId);
    if (!route?.tvs?.length) return "";
    const count = route.tvs.length;
    const preview = route.tvs.slice(0, 3).join(", ");
    const label = count <= 3 ? `TVs ${preview}` : `${count} TVs`;
    return `<span class="route-badge">${escapeHtml(label)}</span>`;
  }

  _renderGameCard(
    game,
    { kicker, selected = false, cta = "Choose destination", action = "select-game" } = {}
  ) {
    const selectedClass = selected ? "is-selected" : "";
    const actionAttr = action === "toggle-program" ? 'data-action="toggle-program"' : 'data-action="select-game"';
    return `
      <button type="button" class="content-card ${selectedClass}" ${actionAttr} data-value="${escapeAttr(game.id)}">
        <span class="card-kicker">${escapeHtml(kicker)}</span>
        <span class="matchup">
          <span class="team">
            <img class="team-logo" src="${escapeAttr(game.awayLogo)}" alt="" width="36" height="36" loading="lazy">
            <span>${escapeHtml(game.away)}</span>
          </span>
          <span class="at" aria-hidden="true">@</span>
          <span class="team">
            <img class="team-logo" src="${escapeAttr(game.homeLogo)}" alt="" width="36" height="36" loading="lazy">
            <span>${escapeHtml(game.home)}</span>
          </span>
        </span>
        <span class="card-meta">
          <span>${escapeHtml(cta)}</span>
          ${this._routeBadgeHtml(game.id)}
        </span>
      </button>
    `;
  }

  _activeSport() {
    return SPORTS.find((sport) => sport.id === this._state.sportId) ?? SPORTS[0];
  }

  _selectedContentLabel() {
    const content = this._state.selectedContent;
    if (!content) return "No content selected";
    if (content.kind === "channel") return `${content.number} ${content.name}`;
    return `${content.away} @ ${content.home}`;
  }

  _onClick(event) {
    const target = event.target.closest?.("[data-action]");
    if (!target) return;

    const { action, value } = target.dataset;
    if (action === "open-sport" || action === "select-sport") {
      this._setState({
        screen: "browse-sport",
        sportId: value || this._state.sportId,
        contentMode: "sports",
        entryPath: "content",
        groupMode: null,
        selectedPrograms: [],
      });
      return;
    }
    if (action === "open-guide") {
      this._setState({
        screen: "browse-guide",
        contentMode: "guide",
        entryPath: "content",
        groupMode: null,
        selectedPrograms: [],
      });
      return;
    }
    if (action === "open-tvs") {
      this._setState({
        screen: "browse-tvs",
        entryPath: "tv",
        destMode: "presets",
        selectedContent: null,
        selectedPresetId: null,
        groupMode: null,
        selectedPrograms: [],
        selectedTvs: [],
      });
      return;
    }
    if (action === "select-game") {
      this._selectGame(value);
      return;
    }
    if (action === "select-channel") {
      this._selectChannel(value);
      return;
    }
    if (action === "open-destination") {
      this._setState({ screen: "destination" });
      return;
    }
    if (action === "set-dest-mode") {
      this._setDestMode(value);
      return;
    }
    if (action === "set-tv-browse-mode") {
      this._setDestMode(value);
      return;
    }
    if (action === "next-choose-content") {
      if (this._state.selectedTvs.length > 0) {
        const preset = PRESETS.find((item) => item.id === this._state.selectedPresetId);
        const groupMode =
          this._state.destMode === "tvs" ? "adhoc" : (preset?.mode ?? "adhoc");
        this._setState({
          screen: "content-picker",
          selectedContent: null,
          selectedPrograms: [],
          groupMode,
        });
      }
      return;
    }
    if (action === "set-content-mode") {
      this._setState({
        contentMode: value === "guide" ? "guide" : "sports",
        selectedContent: null,
      });
      return;
    }
    if (action === "select-group") {
      this._selectGroup(value);
      return;
    }
    if (action === "toggle-program") {
      this._toggleProgram(value);
      return;
    }
    if (action === "clear-programs") {
      this._setState({ selectedPrograms: [] });
      return;
    }
    if (action === "toggle-tv") {
      this._toggleTv(Number(value));
      return;
    }
    if (action === "clear-tvs") {
      this._setState({ selectedTvs: [], selectedPresetId: null, groupMode: null });
      return;
    }
    if (action === "send-destination" || action === "save-route") {
      this._sendDestination();
      return;
    }
    if (action === "send-tv-first") {
      this._sendTvFirst();
      return;
    }
    if (action === "toggle-live-commit") {
      if (!this._inventoryLiveReady) return;
      this._setState({ liveCommit: !this._state.liveCommit });
      return;
    }
    if (action === "send-plan") {
      this._sendPlan();
      return;
    }
    if (action === "dismiss-plan") {
      this._setState({ lastPlan: null });
      return;
    }
    if (action === "back-browse") {
      this._backToBrowse();
    }
  }

  _onInput(event) {
    const target = event.target;
    if (target?.dataset?.action === "guide-search") {
      this._setState({ guideQuery: target.value });
    }
  }

  _browseScreenForContent() {
    if (this._state.entryPath === "tv") return "browse-tvs";
    return this._state.contentMode === "guide" ? "browse-guide" : "browse-sport";
  }

  _seedDestinationTvs(routeId) {
    const assignment = getAssignmentForProgram(this._assignments, routeId);
    return [...(assignment?.tvs ?? [])].sort((a, b) => a - b);
  }

  _seedDestinationMode(routeId) {
    const assignment = getAssignmentForProgram(this._assignments, routeId);
    if (!assignment?.tvs?.length) return "presets";
    return assignment.presetId ? "presets" : "tvs";
  }

  _seedDestinationPresetId(routeId) {
    return getAssignmentForProgram(this._assignments, routeId)?.presetId ?? null;
  }

  _setDestMode(value) {
    const destMode = value === "presets" ? "presets" : "tvs";
    if (destMode === "tvs") {
      this._setState({
        destMode,
        selectedPresetId: null,
        groupMode: "adhoc",
      });
      return;
    }
    const preset = PRESETS.find((item) => item.id === this._state.selectedPresetId);
    this._setState({
      destMode,
      groupMode: preset?.mode ?? null,
    });
  }

  _deriveGroupMode(destMode, selectedPresetId) {
    if (destMode === "tvs") return "adhoc";
    return PRESETS.find((item) => item.id === selectedPresetId)?.mode ?? null;
  }

  _shouldSendViaPlan() {
    const mode = this._state.destMode === "tvs" ? "adhoc" : this._state.groupMode;
    return mode === "adhoc" || mode === "preset_1" || mode === "preset_2" || mode === "preset_3";
  }

  _selectGame(gameId) {
    const game = SPORTS.flatMap((item) => item.games.map((sportGame) => ({ sport: item, game: sportGame }))).find(
      (item) => item.game.id === gameId
    );
    if (!game) return;
    const selectedContent = { ...game.game, kind: "game", sportId: game.sport.id };
    if (this._state.entryPath === "tv") {
      this._setState({
        screen: "content-picker",
        selectedContent,
        sportId: game.sport.id,
        contentMode: "sports",
      });
      return;
    }
    const selectedPresetId = this._seedDestinationPresetId(game.game.id);
    const destMode = this._seedDestinationMode(game.game.id);
    this._setState({
      screen: "destination",
      selectedContent,
      selectedTvs: this._seedDestinationTvs(game.game.id),
      selectedPresetId,
      destMode,
      contentMode: "sports",
      entryPath: "content",
      groupMode: this._deriveGroupMode(destMode, selectedPresetId),
      selectedPrograms: [],
    });
  }

  _selectChannel(channelId) {
    const channel = GUIDE_CHANNELS.find((item) => item.id === channelId);
    if (!channel) return;
    const selectedContent = { ...channel, kind: "channel" };
    if (this._state.entryPath === "tv") {
      this._setState({
        screen: "content-picker",
        selectedContent,
        contentMode: "guide",
      });
      return;
    }
    const selectedPresetId = this._seedDestinationPresetId(channel.id);
    const destMode = this._seedDestinationMode(channel.id);
    this._setState({
      screen: "destination",
      selectedContent,
      selectedTvs: this._seedDestinationTvs(channel.id),
      selectedPresetId,
      destMode,
      contentMode: "guide",
      entryPath: "content",
      groupMode: this._deriveGroupMode(destMode, selectedPresetId),
      selectedPrograms: [],
    });
  }

  _activePreset() {
    return PRESETS.find((item) => item.id === this._state.selectedPresetId) ?? null;
  }

  _programCapacity() {
    const preset = this._activePreset();
    if (preset) return preset.programCapacity;
    if (this._state.groupMode === "preset_2") return 4;
    if (this._state.groupMode === "preset_3") return 9;
    return 1;
  }

  _toProgram(content) {
    if (!content) return null;
    if (content.kind === "channel") {
      return {
        id: content.id,
        kind: "channel",
        label: `${content.number} ${content.name}`,
        channel: content.number,
        channelNumber: String(content.number),
      };
    }
    return {
      id: content.id,
      kind: "game",
      sportId: content.sportId ?? null,
      label: `${content.away} @ ${content.home}`,
      channel: content.channel,
      channelNumber: null,
    };
  }

  _findContentById(contentId) {
    for (const sport of SPORTS) {
      const game = sport.games.find((item) => item.id === contentId);
      if (game) return { ...game, kind: "game", sportId: sport.id };
    }
    const channel = GUIDE_CHANNELS.find((item) => item.id === contentId);
    if (channel) return { ...channel, kind: "channel" };
    return null;
  }

  _selectGroup(presetId) {
    const preset = PRESETS.find((item) => item.id === presetId);
    if (!preset) return;
    if (preset.programCapacity > 1) {
      this._setState({
        groupMode: preset.mode,
        selectedPresetId: presetId,
        selectedTvs: [],
        selectedPrograms: [],
        selectedContent: null,
        destMode: "presets",
        screen: "program-picker",
        contentMode: "sports",
      });
      return;
    }
    this._setState({
      groupMode: preset.mode,
      selectedTvs: [...preset.tvs],
      selectedPresetId: presetId,
      destMode: "presets",
    });
  }

  _toggleProgram(contentId) {
    const content = this._findContentById(contentId);
    if (!content) return;
    const program = this._toProgram(content);
    const existing = this._state.selectedPrograms;
    const index = existing.findIndex((item) => item.id === program.id);
    if (index >= 0) {
      this._setState({
        selectedPrograms: existing.filter((item) => item.id !== program.id),
      });
      return;
    }
    const capacity = this._programCapacity();
    if (existing.length >= capacity) return;
    this._setState({
      selectedPrograms: [...existing, program],
      contentMode: content.kind === "channel" ? "guide" : "sports",
      sportId: content.sportId ?? this._state.sportId,
    });
  }

  _toggleTv(tv) {
    if (!Number.isInteger(tv)) return;
    const selected = new Set(this._state.selectedTvs);
    if (selected.has(tv)) selected.delete(tv);
    else selected.add(tv);
    this._setState({
      selectedTvs: Array.from(selected).sort((a, b) => a - b),
      selectedPresetId: null,
      destMode: "tvs",
      groupMode: "adhoc",
    });
  }

  _backToBrowse() {
    this._setState({ screen: this._browseScreenForContent() });
  }

  _speculativePlan(programs = this._state.selectedPrograms) {
    if (!this._state.groupMode) return null;
    return buildRoutePlan({
      mode: this._state.groupMode,
      programs,
      selectedTvs: this._state.selectedTvs,
      busyEncoderIds: listBusyEncoderIds(this._assignments),
      commit: "dry_run",
    });
  }

  async _sendPlan() {
    const groupMode = this._state.destMode === "tvs" ? "adhoc" : this._state.groupMode;
    if (!groupMode) return;
    let programs = this._state.selectedPrograms;
    if ((!programs || programs.length === 0) && this._state.selectedContent) {
      programs = [this._toProgram(this._state.selectedContent)];
    }
    const liveRequested = this._state.liveCommit;
    const liveReady = this._inventoryLiveReady;
    const commit = liveRequested && liveReady ? "live" : "dry_run";
    const plan = buildRoutePlan({
      mode: groupMode,
      programs,
      selectedTvs: this._state.selectedTvs,
      busyEncoderIds: listBusyEncoderIds(this._assignments),
      commit,
    });
    if (plan.error) {
      this._setState({ lastPlan: plan, groupMode });
      return;
    }

    const warnings = [...(plan.warnings ?? [])];
    if (liveRequested && !liveReady) {
      warnings.push(LIVE_BLOCKED_WARNING);
    }

    const assignments = applyRoutePlan(this._assignments, plan);
    this._saveAssignments(assignments);

    let lastPlan = { ...plan, warnings };
    if (liveRequested && liveReady && this.hass?.callService) {
      try {
        const plan_b64 = btoa(unescape(encodeURIComponent(JSON.stringify(plan))));
        const response = await this.hass.callService(
          "shell_command",
          "avaccess_execute_route_plan",
          {
            plan_b64,
            live: true,
          }
        );
        const report = parseLiveExecuteReport(response);
        if (report) {
          lastPlan = mergeLiveReportIntoPlan(lastPlan, report);
        }
      } catch (error) {
        const message = `Live execute failed: ${error?.message ?? error}`;
        warnings.push(message);
        lastPlan = { ...lastPlan, warnings, error: lastPlan.error ?? message };
      }
    }

    this._setState({
      lastPlan,
      selectedPrograms: [],
      selectedContent: null,
      groupMode: null,
      selectedPresetId: null,
      selectedTvs: [],
      screen: this._browseScreenForContent(),
    });
  }

  _sendDestination() {
    const content = this._state.selectedContent;
    if (!content) return;

    // Planner modes (including leftover preset_2/3) never fall through to applyAssignment.
    if (this._shouldSendViaPlan()) {
      const groupMode = this._state.destMode === "tvs" ? "adhoc" : this._state.groupMode;
      const programs =
        (groupMode === "preset_2" || groupMode === "preset_3") && this._state.selectedPrograms.length > 0
          ? this._state.selectedPrograms
          : [this._toProgram(content)];
      this._state = {
        ...this._state,
        groupMode,
        selectedPrograms: programs,
      };
      this._sendPlan();
      return;
    }

    const selectedTvs = [...this._state.selectedTvs].sort((a, b) => a - b);
    const assignments = applyAssignment(this._assignments, {
      routeId: content.id,
      kind: content.kind,
      sportId: content.sportId,
      label: this._selectedContentLabel(),
      channel: content.channel ?? content.number,
      presetId: resolveSendPresetId({
        destMode: this._state.destMode,
        selectedPresetId: this._state.selectedPresetId,
        selectedTvs,
        presets: PRESETS,
      }),
      tvs: selectedTvs,
    });
    this._saveAssignments(assignments);
    this._setState({
      groupMode: null,
      selectedPrograms: [],
      screen: this._browseScreenForContent(),
    });
  }

  _sendTvFirst() {
    if (!this._state.selectedContent || this._state.selectedTvs.length === 0) return;
    if (this._shouldSendViaPlan()) {
      this._state = {
        ...this._state,
        groupMode: this._state.destMode === "tvs" ? "adhoc" : this._state.groupMode,
        selectedPrograms: [this._toProgram(this._state.selectedContent)],
      };
      this._sendPlan();
      return;
    }
    this._sendDestination();
  }

  _selectedTvsLabel() {
    return this._state.selectedTvs.length ? this._state.selectedTvs.join(", ") : "None selected";
  }

  _renderChipRow() {
    const sport = this._activeSport();
    return `
      <nav class="chips" aria-label="Panel screens">
        ${SPORTS.map(
          (item) => `
            <button
              type="button"
              class="chip ${this._state.screen === "browse-sport" && item.id === sport.id ? "is-active" : ""}"
              data-action="select-sport"
              data-value="${escapeAttr(item.id)}"
            >
              <span>${escapeHtml(item.icon)}</span>${escapeHtml(item.chipTitle ?? item.title)}
            </button>
          `
        ).join("")}
        <button type="button" class="chip ${this._state.screen === "browse-guide" ? "is-active" : ""}" data-action="open-guide">
          Guide
        </button>
        <button type="button" class="chip ${this._state.screen === "browse-tvs" ? "is-active" : ""}" data-action="open-tvs">
          TVs
        </button>
      </nav>
    `;
  }

  _renderScreen() {
    if (this._state.screen === "browse-guide") return this._renderGuideScreen();
    if (this._state.screen === "browse-tvs") return this._renderTvsScreen();
    if (this._state.screen === "destination") return this._renderDestinationScreen();
    if (this._state.screen === "content-picker") return this._renderContentPickerScreen();
    if (this._state.screen === "program-picker") return this._renderProgramPickerScreen();
    return this._renderSportScreen();
  }

  _renderSportScreen() {
    const sport = this._activeSport();
    return `
      <section class="screen">
        <div class="screen-heading">
          <p class="eyebrow">Browse sport</p>
          <h2>${escapeHtml(sport.title)}</h2>
        </div>
        <div class="card-grid">
          ${sport.games
            .map((game) =>
              this._renderGameCard(game, {
                kicker: `${game.channel} - ${game.tipoff}`,
                cta: "Choose destination",
              })
            )
            .join("")}
        </div>
      </section>
    `;
  }

  _renderGuideScreen() {
    const channels = filterGuideChannels(GUIDE_CHANNELS, this._state.guideQuery);
    return `
      <section class="screen">
        <div class="screen-heading">
          <p class="eyebrow">Browse guide</p>
          <h2 aria-label="Spectrum · ZIP 27403">Spectrum · ZIP ${escapeHtml(SPECTRUM_ZIP)} · Xumo</h2>
        </div>
        <label class="search">
          <span>Search by channel, name, or category</span>
          <input data-action="guide-search" value="${escapeAttr(this._state.guideQuery)}" placeholder="ESPN, 206, Sports">
        </label>
        <div class="list">
          ${channels
            .map(
              (channel) => `
                <button type="button" class="guide-row" data-action="select-channel" data-value="${escapeAttr(channel.id)}">
                  <b>${escapeHtml(channel.number)}</b>
                  <span>${escapeHtml(channel.name)}</span>
                  <em>${escapeHtml(channel.category)}</em>
                  ${this._routeBadgeHtml(channel.id)}
                </button>
              `
            )
            .join("")}
        </div>
      </section>
    `;
  }

  _renderTvsScreen() {
    const selectedCount = this._state.selectedTvs.length;
    return `
      <section class="screen">
        <div class="screen-heading">
          <p class="eyebrow">Browse TVs</p>
          <h2>Select TVs first</h2>
        </div>
        <div class="mode-toggle" role="group" aria-label="TV browse mode">
          <button type="button" class="${this._state.destMode === "presets" ? "is-active" : ""}" data-action="set-tv-browse-mode" data-value="presets">
            Presets
          </button>
          <button type="button" class="${this._state.destMode === "tvs" ? "is-active" : ""}" data-action="set-tv-browse-mode" data-value="tvs">
            Pick TVs
          </button>
        </div>
        <div class="destination-body">
          ${this._state.destMode === "presets" ? this._renderPresetChoices() : this._renderTvGrid()}
        </div>
        <button
          type="button"
          class="primary-action"
          data-action="next-choose-content"
          ${selectedCount === 0 ? "disabled aria-disabled=\"true\"" : ""}
        >
          Next: Choose content
        </button>
      </section>
    `;
  }

  _renderDestinationScreen() {
    const content = this._state.selectedContent;
    const isAdhoc = this._state.destMode === "tvs" || this._state.groupMode === "adhoc";
    const viaPlan = this._shouldSendViaPlan();
    const programs = content ? [this._toProgram(content)] : [];
    const speculative =
      isAdhoc && content && this._state.selectedTvs.length > 0
        ? buildRoutePlan({
            mode: "adhoc",
            programs,
            selectedTvs: this._state.selectedTvs,
            busyEncoderIds: listBusyEncoderIds(this._assignments),
            commit: "dry_run",
          })
        : null;
    const noFreeEncoders = speculative?.error === "No free encoders";
    const sendDisabled =
      !content || this._state.selectedTvs.length === 0 || Boolean(speculative?.error);
    const sendLabel = viaPlan
      ? this._planSendLabel()
      : `Send to ${this._state.selectedTvs.length} TV${this._state.selectedTvs.length === 1 ? "" : "s"}`;
    return `
      <section class="screen">
        <div class="screen-heading">
          <p class="eyebrow">Destination</p>
          <h2>${escapeHtml(this._selectedContentLabel())}</h2>
          <button type="button" class="link-button" data-action="back-browse">Back to browse</button>
        </div>
        <div class="mode-toggle" role="group" aria-label="Destination mode">
          <button type="button" class="${this._state.destMode === "presets" ? "is-active" : ""}" data-action="set-dest-mode" data-value="presets">
            Presets
          </button>
          <button type="button" class="${this._state.destMode === "tvs" ? "is-active" : ""}" data-action="set-dest-mode" data-value="tvs">
            Pick TVs
          </button>
        </div>
        ${noFreeEncoders ? `<div class="plan-error-banner">No free encoders</div>` : ""}
        <div class="destination-body">
          ${this._state.destMode === "presets" ? this._renderPresetChoices() : this._renderTvGrid()}
        </div>
        <button
          type="button"
          class="primary-action"
          data-action="send-destination"
          ${sendDisabled ? "disabled aria-disabled=\"true\"" : ""}
        >
          ${sendLabel}
        </button>
      </section>
    `;
  }

  _renderPresetChoices() {
    return `
      <div class="preset-row">
        ${PRESETS.map((preset) => {
          const active = this._state.selectedPresetId === preset.id ? "is-active" : "";
          return `
            <button type="button" class="preset-chip ${active}" data-action="select-group" data-value="${escapeAttr(preset.id)}">
              <b>${escapeHtml(preset.shortLabel)}</b>
              <span>${escapeHtml(preset.description)}</span>
            </button>
          `;
        }).join("")}
      </div>
    `;
  }

  _programLabel(program) {
    return program?.label ?? "Empty";
  }

  _renderSlotStrip() {
    const capacity = this._programCapacity();
    const stripeCount = this._activePreset()?.stripeCount ?? capacity;
    const slots = Array.from({ length: capacity }, (_, index) => {
      const program = this._state.selectedPrograms[index];
      const ordinal = index + 1;
      const tvs = program ? stripedTvs(stripeCount, ordinal) : [];
      const preview = program
        ? `ENC-${String(ordinal).padStart(2, "0")} · TVs ${tvs.slice(0, 4).join(", ")}${tvs.length > 4 ? "…" : ""}`
        : "Empty";
      return `
        <div class="slot-chip ${program ? "is-filled" : ""}">
          <b>Slot ${ordinal}: ${escapeHtml(program ? this._programLabel(program) : "—")}</b>
          <span>${escapeHtml(preview)}</span>
        </div>
      `;
    });
    return `<div class="slot-strip" aria-label="Program slots">${slots.join("")}</div>`;
  }

  _renderDryRunSummary() {
    const plan = this._state.lastPlan;
    if (!plan) return "";
    const summaryLabel = plan.commit === "live" ? "Live summary" : "Dry-run summary";
    const error = plan.error
      ? `<p class="plan-error">${escapeHtml(plan.error)}</p>`
      : "";
    const warnings = (plan.warnings ?? [])
      .map((warning) => `<p class="plan-warning">${escapeHtml(warning)}</p>`)
      .join("");
    const slots = (plan.slots ?? [])
      .map((slot) => {
        const status =
          slot.status && slot.status !== "planned"
            ? ` · ${escapeHtml(slot.status)}${
                slot.status === "error" && (slot.error || slot.message)
                  ? `: ${escapeHtml(slot.error || slot.message)}`
                  : ""
              }`
            : "";
        return `
          <li>
            <b>${escapeHtml(slot.encoderId)}</b>
            · ${escapeHtml(slot.program?.label ?? "Program")}
            · TVs ${escapeHtml((slot.tvs ?? []).join(", "))}
            ${status}
          </li>
        `;
      })
      .join("");
    return `
      <aside class="dry-run-summary" aria-live="polite">
        <div class="dry-run-heading">
          <p class="eyebrow">${summaryLabel}</p>
          <button type="button" class="link-button" data-action="dismiss-plan">Dismiss</button>
        </div>
        ${error}
        ${warnings}
        ${slots ? `<ul class="plan-slots">${slots}</ul>` : ""}
        ${!plan.error && !slots ? "<p>No slots planned.</p>" : ""}
      </aside>
    `;
  }

  _renderProgramPickerScreen() {
    const preset = this._activePreset();
    const heading = preset?.label ?? "Programs";
    const speculative = this._speculativePlan();
    const sendDisabled =
      this._state.selectedPrograms.length === 0 || Boolean(speculative?.error);
    return `
      <section class="screen">
        <div class="screen-heading">
          <div>
            <p class="eyebrow">Group programs</p>
            <h2>${escapeHtml(heading)}</h2>
          </div>
          <button type="button" class="link-button" data-action="back-browse">Back</button>
        </div>
        ${this._renderSlotStrip()}
        <div class="tv-toolbar">
          <span>${this._state.selectedPrograms.length} / ${this._programCapacity()} programs</span>
          <button type="button" data-action="clear-programs">Clear programs</button>
        </div>
        <div class="mode-toggle" role="group" aria-label="Content mode">
          <button type="button" class="${this._state.contentMode === "sports" ? "is-active" : ""}" data-action="set-content-mode" data-value="sports">
            Sports
          </button>
          <button type="button" class="${this._state.contentMode === "guide" ? "is-active" : ""}" data-action="set-content-mode" data-value="guide">
            Guide
          </button>
        </div>
        ${this._state.contentMode === "guide" ? this._renderGuideProgramOptions() : this._renderSportsProgramOptions()}
        <button
          type="button"
          class="primary-action"
          data-action="send-plan"
          ${sendDisabled ? "disabled aria-disabled=\"true\"" : ""}
        >
          ${this._planSendLabel()}
        </button>
      </section>
    `;
  }

  _renderSportsProgramOptions() {
    const selectedIds = new Set(this._state.selectedPrograms.map((item) => item.id));
    return `
      <div class="content-stack">
        ${SPORTS.map(
          (sport) => `
            <div class="content-section">
              <h3>${escapeHtml(sport.title)}</h3>
              <div class="card-grid">
                ${sport.games
                  .map((game) =>
                    this._renderGameCard(game, {
                      kicker: `${sport.chipTitle ?? sport.title} - ${game.channel} - ${game.tipoff}`,
                      selected: selectedIds.has(game.id),
                      cta: selectedIds.has(game.id) ? "Selected for slot" : "Add to slots",
                      action: "toggle-program",
                    })
                  )
                  .join("")}
              </div>
            </div>
          `
        ).join("")}
      </div>
    `;
  }

  _renderGuideProgramOptions() {
    const channels = filterGuideChannels(GUIDE_CHANNELS, this._state.guideQuery);
    const selectedIds = new Set(this._state.selectedPrograms.map((item) => item.id));
    return `
      <label class="search">
        <span>Search by channel, name, or category</span>
        <input data-action="guide-search" value="${escapeAttr(this._state.guideQuery)}" placeholder="ESPN, 206, Sports">
      </label>
      <div class="list">
        ${channels
          .map((channel) => {
            const selected = selectedIds.has(channel.id) ? "is-selected" : "";
            return `
              <button type="button" class="guide-row ${selected}" data-action="toggle-program" data-value="${escapeAttr(channel.id)}">
                <b>${escapeHtml(channel.number)}</b>
                <span>${escapeHtml(channel.name)}</span>
                <em>${escapeHtml(channel.category)}</em>
                ${this._routeBadgeHtml(channel.id)}
              </button>
            `;
          })
          .join("")}
      </div>
    `;
  }

  _renderContentPickerScreen() {
    const tvFirst = this._state.entryPath === "tv";
    const programs = this._state.selectedContent
      ? [this._toProgram(this._state.selectedContent)]
      : [];
    const speculative =
      tvFirst && (this._state.groupMode === "adhoc" || this._state.groupMode === "preset_1")
        ? this._speculativePlan(programs)
        : null;
    const noFreeEncoders = speculative?.error === "No free encoders";
    const sendDisabled =
      !this._state.selectedContent ||
      this._state.selectedTvs.length === 0 ||
      Boolean(speculative?.error);
    const usePlanSend = this._state.groupMode === "adhoc" || this._state.groupMode === "preset_1";
    return `
      <section class="screen">
        <div class="screen-heading">
          <p class="eyebrow">Content picker</p>
          <h2>Choose the next content source</h2>
          ${
            tvFirst
              ? '<button type="button" class="link-button" data-action="back-browse">Back to TVs</button>'
              : '<button type="button" class="link-button" data-action="open-sport">Back to sports</button>'
          }
        </div>
        ${tvFirst ? `<div class="locked-summary">Sending to TVs: ${escapeHtml(this._selectedTvsLabel())}</div>` : ""}
        ${noFreeEncoders ? `<div class="plan-error-banner">No free encoders</div>` : ""}
        <div class="mode-toggle" role="group" aria-label="Content mode">
          <button type="button" class="${this._state.contentMode === "sports" ? "is-active" : ""}" data-action="set-content-mode" data-value="sports">
            Sports
          </button>
          <button type="button" class="${this._state.contentMode === "guide" ? "is-active" : ""}" data-action="set-content-mode" data-value="guide">
            Guide
          </button>
        </div>
        ${this._state.contentMode === "guide" ? this._renderGuideContentOptions() : this._renderSportsContentOptions()}
        ${
          tvFirst
            ? usePlanSend
              ? `<button
                  type="button"
                  class="primary-action"
                  data-action="send-plan"
                  ${sendDisabled ? "disabled aria-disabled=\"true\"" : ""}
                >
                  ${this._planSendLabel()}
                </button>`
              : `<button
                  type="button"
                  class="primary-action"
                  data-action="send-tv-first"
                  ${sendDisabled ? "disabled aria-disabled=\"true\"" : ""}
                >
                  Send to ${this._state.selectedTvs.length} TV${this._state.selectedTvs.length === 1 ? "" : "s"}
                </button>`
            : ""
        }
      </section>
    `;
  }

  _renderSportsContentOptions() {
    return `
      <div class="content-stack">
        ${SPORTS.map(
          (sport) => `
            <div class="content-section">
              <h3>${escapeHtml(sport.title)}</h3>
              <div class="card-grid">
                ${sport.games
                  .map((game) =>
                    this._renderGameCard(game, {
                      kicker: `${sport.chipTitle ?? sport.title} - ${game.channel} - ${game.tipoff}`,
                      selected: this._state.selectedContent?.id === game.id,
                      cta: this._state.entryPath === "tv" ? "Select content" : "Choose destination",
                    })
                  )
                  .join("")}
              </div>
            </div>
          `
        ).join("")}
      </div>
    `;
  }

  _renderGuideContentOptions() {
    const channels = filterGuideChannels(GUIDE_CHANNELS, this._state.guideQuery);
    return `
      <label class="search">
        <span>Search by channel, name, or category</span>
        <input data-action="guide-search" value="${escapeAttr(this._state.guideQuery)}" placeholder="ESPN, 206, Sports">
      </label>
      <div class="list">
        ${channels
          .map((channel) => {
            const selected = this._state.selectedContent?.id === channel.id ? "is-selected" : "";
            return `
              <button type="button" class="guide-row ${selected}" data-action="select-channel" data-value="${escapeAttr(channel.id)}">
                <b>${escapeHtml(channel.number)}</b>
                <span>${escapeHtml(channel.name)}</span>
                <em>${escapeHtml(channel.category)}</em>
                ${this._routeBadgeHtml(channel.id)}
              </button>
            `;
          })
          .join("")}
      </div>
    `;
  }

  _renderTvGrid() {
    return `
      <div class="tv-toolbar">
        <span>${this._state.selectedTvs.length} selected</span>
        <button type="button" data-action="clear-tvs">Clear TVs</button>
      </div>
      <div class="tv-grid" aria-label="TV picker">
        ${range(1, 35)
          .map((tv) => {
            const assignment = getAssignmentForTv(this._assignments, tv);
            const selected = this._state.selectedTvs.includes(tv) ? "is-selected" : "";
            const assigned = assignment ? "is-assigned" : "";
            const label = assignment ? `TV ${tv}: ${assignment.label}` : `TV ${tv}`;
            return `
              <button
                type="button"
                class="tv ${selected} ${assigned}"
                data-action="toggle-tv"
                data-value="${tv}"
                title="${escapeAttr(label)}"
              >
                <span class="tv-number">${tv}</span>
                ${assignment ? `<span class="tv-occupancy">${escapeHtml(assignment.label)}</span>` : ""}
              </button>
            `;
          })
          .join("")}
      </div>
    `;
  }

  render() {
    if (!this.isConnected) return;

    const guideSearchCaret = this._captureGuideSearchCaret();

    this.innerHTML = `
      <style>
        @import url("https://fonts.googleapis.com/css2?family=Sora:wght@600;700;800&display=swap");

        :host {
          --canvas: ${TOKENS.canvas};
          --graphite: ${TOKENS.stage};
          --surface: ${TOKENS.surfaceBrowse};
          --stage-surface: ${TOKENS.surfaceStage};
          --cyan: ${TOKENS.accent}; /* #0e7490 */
          --cyan-soft: ${TOKENS.accentMutedBrowse};
          --cyan-stage: ${TOKENS.accentMutedStage};
          --text: ${TOKENS.textPrimaryBrowse};
          --text-stage: ${TOKENS.textPrimaryStage};
          --muted: ${TOKENS.textMutedBrowse};
          --muted-stage: ${TOKENS.textMutedStage};
          --radius-sm: ${TOKENS.radiusSm};
          --radius-md: ${TOKENS.radiusMd};
          display: block;
          min-height: 100%;
          color: var(--text);
          background: var(--canvas);
          font-family: Sora, "Avenir Next", "Segoe UI", sans-serif;
        }

        .shell {
          min-height: 100%;
          padding: 20px;
          box-sizing: border-box;
          background:
            radial-gradient(circle at top left, rgba(14, 116, 144, 0.2), transparent 32rem),
            linear-gradient(135deg, var(--canvas) 0%, #e5e7eb 100%);
        }

        .stage {
          border-radius: var(--radius-md);
          background: var(--graphite);
          color: var(--text-stage);
          padding: 18px;
          box-shadow: 0 24px 80px rgba(17, 24, 39, 0.22);
        }

        .topbar {
          display: flex;
          align-items: flex-start;
          justify-content: space-between;
          gap: 16px;
          margin-bottom: 16px;
        }

        .brand span,
        .eyebrow {
          color: var(--cyan-stage);
          font-size: 0.75rem;
          font-weight: 800;
          letter-spacing: 0.14em;
          margin: 0 0 6px;
          text-transform: uppercase;
        }

        .brand h1,
        .screen-heading h2 {
          margin: 0;
          font-size: clamp(1.45rem, 2.8vw, 2.4rem);
          letter-spacing: -0.04em;
        }

        .state-pill {
          border: 1px solid rgba(165, 243, 252, 0.35);
          border-radius: var(--radius-md);
          color: var(--cyan-stage);
          padding: 8px 12px;
          white-space: nowrap;
        }

        .chips {
          display: flex;
          gap: 8px;
          margin-bottom: 18px;
          overflow-x: auto;
          padding-bottom: 2px;
        }

        .chip,
        .link-button,
        .mode-toggle button,
        .preset-chip,
        .tv-toolbar button,
        .live-commit-toggle,
        .primary-action,
        .stub-card {
          border: 0;
          cursor: pointer;
          font: inherit;
        }

        .chip {
          align-items: center;
          background: rgba(255, 255, 255, 0.09);
          border-radius: var(--radius-md);
          color: var(--text-stage);
          display: inline-flex;
          gap: 8px;
          padding: 10px 14px;
          white-space: nowrap;
        }

        .chip.is-active {
          background: var(--cyan);
          color: white;
        }

        .screen {
          background: var(--surface);
          border-radius: var(--radius-md);
          color: var(--text);
          min-height: 420px;
          padding: 18px;
        }

        .screen-heading {
          align-items: center;
          display: flex;
          justify-content: space-between;
          gap: 12px;
          margin-bottom: 16px;
        }

        .screen-heading .eyebrow {
          color: var(--cyan);
        }

        .link-button,
        .tv-toolbar button {
          background: var(--cyan-soft);
          border-radius: var(--radius-md);
          color: var(--cyan);
          font-weight: 800;
          padding: 10px 12px;
        }

        .card-grid,
        .stub-grid {
          display: grid;
          gap: 12px;
          grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
        }

        .content-card,
        .guide-row,
        .stub-card {
          background: #f9fafb;
          border: 1px solid #e5e7eb;
          border-radius: var(--radius-md);
          color: var(--text);
          cursor: pointer;
          padding: 14px;
          text-align: left;
        }

        .content-card.is-selected,
        .guide-row.is-selected {
          border-color: var(--cyan);
          box-shadow: inset 0 0 0 2px var(--cyan);
        }

        .card-kicker {
          color: var(--cyan);
          font-size: 0.78rem;
          font-weight: 900;
          letter-spacing: 0.08em;
          text-transform: uppercase;
        }

        .matchup {
          align-items: center;
          display: flex;
          flex-wrap: wrap;
          gap: 10px;
          margin: 10px 0 8px;
        }

        .team {
          align-items: center;
          display: inline-flex;
          gap: 8px;
          font-size: 1.05rem;
          font-weight: 800;
        }

        .team-logo {
          background: #fff;
          border-radius: var(--radius-sm);
          display: block;
          height: 36px;
          object-fit: contain;
          width: 36px;
        }

        .at {
          color: var(--muted);
          font-weight: 800;
        }

        .card-meta {
          align-items: center;
          color: var(--muted);
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
          justify-content: space-between;
        }

        .route-badge {
          background: var(--cyan-soft);
          border-radius: var(--radius-sm);
          color: var(--cyan);
          font-size: 0.72rem;
          font-weight: 800;
          padding: 4px 8px;
          white-space: nowrap;
        }

        .search {
          display: grid;
          gap: 8px;
          margin-bottom: 12px;
        }

        .search span,
        .tv-toolbar span {
          color: var(--muted);
          font-weight: 700;
        }

        .search input {
          border: 1px solid #d1d5db;
          border-radius: var(--radius-md);
          font: inherit;
          padding: 12px;
        }

        .list {
          display: grid;
          gap: 8px;
        }

        .content-stack {
          display: grid;
          gap: 16px;
        }

        .content-section h3 {
          margin: 0 0 8px;
        }

        .guide-row {
          align-items: center;
          display: grid;
          gap: 10px;
          grid-template-columns: 64px 1fr auto auto;
        }

        .guide-row b {
          color: var(--cyan);
          font-size: 1.1rem;
        }

        .guide-row em {
          color: var(--muted);
          font-style: normal;
        }

        .mode-toggle,
        .preset-row,
        .tv-toolbar {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
          margin-bottom: 12px;
        }

        .mode-toggle button,
        .preset-chip {
          background: #eef2f7;
          border-radius: var(--radius-md);
          padding: 11px 13px;
        }

        .mode-toggle button.is-active {
          background: var(--cyan);
          color: white;
        }

        .locked-summary {
          background: #eef2f7;
          border: 1px solid #d1d5db;
          border-radius: var(--radius-md);
          color: var(--graphite);
          font-weight: 900;
          margin-bottom: 12px;
          padding: 12px;
        }

        .preset-chip b,
        .preset-chip span,
        .slot-chip b,
        .slot-chip span {
          display: block;
        }

        .preset-chip span,
        .slot-chip span {
          color: var(--muted);
          font-size: 0.8rem;
        }

        .preset-chip.is-active {
          background: var(--cyan);
          color: white;
        }

        .preset-chip.is-active span {
          color: rgba(255, 255, 255, 0.82);
        }

        .slot-strip {
          display: grid;
          gap: 8px;
          grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
          margin-bottom: 12px;
        }

        .slot-chip {
          background: #eef2f7;
          border-radius: var(--radius-md);
          padding: 11px 13px;
        }

        .slot-chip.is-filled {
          box-shadow: inset 0 0 0 2px var(--cyan);
        }

        .live-commit-row {
          align-items: center;
          display: flex;
          gap: 10px;
          margin-bottom: 12px;
        }

        .live-commit-toggle {
          background: rgba(165, 243, 252, 0.08);
          border: 1px solid rgba(165, 243, 252, 0.35);
          border-radius: var(--radius-md);
          color: var(--cyan-stage);
          font-weight: 800;
          padding: 10px 14px;
        }

        .live-commit-toggle.is-active {
          background: var(--cyan);
          border-color: var(--cyan);
          color: white;
        }

        .live-commit-toggle[disabled] {
          cursor: not-allowed;
          opacity: 0.55;
        }

        .live-commit-hint {
          color: var(--muted-stage);
          font-size: 0.8rem;
          font-weight: 700;
        }

        .dry-run-summary {
          background: var(--surface);
          border: 1px solid rgba(14, 116, 144, 0.35);
          border-radius: var(--radius-md);
          color: var(--text);
          margin-bottom: 14px;
          padding: 14px;
        }

        .dry-run-heading {
          align-items: center;
          display: flex;
          justify-content: space-between;
          gap: 12px;
          margin-bottom: 8px;
        }

        .dry-run-heading .eyebrow {
          color: var(--cyan);
        }

        .plan-slots {
          margin: 0;
          padding-left: 18px;
        }

        .plan-error,
        .plan-error-banner {
          color: var(--graphite);
          font-weight: 800;
          margin: 0 0 8px;
        }

        .plan-error-banner {
          background: var(--cyan-soft);
          border-radius: var(--radius-md);
          color: var(--cyan);
          margin-bottom: 12px;
          padding: 12px;
        }

        .plan-warning {
          color: var(--muted);
          margin: 0 0 6px;
        }

        .tv-grid {
          display: grid;
          gap: 7px;
          grid-template-columns: repeat(7, minmax(0, 1fr));
          margin-bottom: 14px;
        }

        .tv {
          align-items: center;
          aspect-ratio: 1;
          background: #eef2f7;
          border: 0;
          border-radius: var(--radius-sm);
          color: var(--text);
          cursor: pointer;
          display: flex;
          flex-direction: column;
          font-weight: 900;
          justify-content: center;
          min-width: 0;
          overflow: hidden;
          padding: 4px;
        }

        .tv.is-assigned:not(.is-selected) {
          background: #d1d5db;
        }

        .tv.is-selected {
          background: var(--cyan);
          color: white;
        }

        .tv-occupancy {
          color: #374151;
          font-size: 0.58rem;
          font-weight: 800;
          max-width: 100%;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }

        .tv.is-selected .tv-occupancy {
          color: rgba(255, 255, 255, 0.82);
        }

        .primary-action {
          background: var(--cyan);
          border-radius: var(--radius-md);
          color: white;
          font-weight: 900;
          padding: 14px 18px;
          width: 100%;
        }

        .primary-action[disabled] {
          background: #9ca3af;
          cursor: not-allowed;
        }

        @media (max-width: 760px) {
          .topbar,
          .screen-heading {
            align-items: stretch;
            flex-direction: column;
          }

          .tv-grid {
            grid-template-columns: repeat(5, minmax(0, 1fr));
          }
        }
      </style>

      <div class="shell">
        <div class="stage">
          <header class="topbar">
            <div class="brand">
              <span>AVAccess · iPad</span>
              <h1>Sports Routing</h1>
            </div>
            <div class="state-pill">Screen: ${escapeHtml(SCREEN_TITLES[this._state.screen])}</div>
          </header>
          ${this._renderChipRow()}
          ${this._renderLiveCommitToggle()}
          ${this._renderDryRunSummary()}
          ${this._renderScreen()}
        </div>
      </div>
    `;

    this._restoreGuideSearchCaret(guideSearchCaret);
  }
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function escapeAttr(value) {
  return escapeHtml(value);
}

function deviceById(devices, id) {
  if (!Array.isArray(devices)) return null;
  return devices.find((item) => item?.id === id) ?? null;
}

function hostnameIssue(deviceId, device) {
  const hostname = device?.hostname;
  if (!hostname || typeof hostname !== "string" || !hostname.trim()) {
    return `${deviceId}: missing hostname`;
  }
  if (hostname.includes("REPLACE_ME")) {
    return `${deviceId}: hostname contains REPLACE_ME`;
  }
  return null;
}

function networkIssues(inventory) {
  const net = inventory?.network;
  if (!net || typeof net !== "object") {
    return ["Missing network.broadcast", "Missing network.udp_switch_port"];
  }
  const issues = [];
  if (
    net.broadcast == null ||
    typeof net.broadcast !== "string" ||
    !net.broadcast.trim()
  ) {
    issues.push("Missing or empty network.broadcast");
  }
  if (
    net.udp_switch_port == null ||
    net.udp_switch_port === "" ||
    (typeof net.udp_switch_port === "string" && !net.udp_switch_port.trim())
  ) {
    issues.push("Missing or empty network.udp_switch_port");
  }
  return issues;
}

function isInventoryLiveReady(inventory) {
  if (!inventory || typeof inventory !== "object") return false;
  if (networkIssues(inventory).length > 0) return false;
  const encoders = inventory.encoders;
  const receivers = inventory.receivers;
  for (let i = 1; i <= 10; i += 1) {
    const encId = `ENC-${String(i).padStart(2, "0")}`;
    if (hostnameIssue(encId, deviceById(encoders, encId))) return false;
  }
  for (let i = 1; i <= 35; i += 1) {
    const rxId = `RX-${String(i).padStart(2, "0")}`;
    if (hostnameIssue(rxId, deviceById(receivers, rxId))) return false;
  }
  return true;
}

function extractShellCommandStdout(response) {
  if (response == null) return null;
  if (typeof response === "string") return response;
  if (typeof response !== "object") return null;
  if (typeof response.stdout === "string") return response.stdout;
  if (typeof response.output === "string") return response.output;
  const nested = response.response;
  if (nested && typeof nested === "object") {
    if (typeof nested.stdout === "string") return nested.stdout;
    if (typeof nested.output === "string") return nested.output;
  }
  return null;
}

function parseLiveExecuteReport(response) {
  const stdout = extractShellCommandStdout(response);
  if (!stdout || typeof stdout !== "string") return null;
  const lines = stdout
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);
  for (let i = lines.length - 1; i >= 0; i -= 1) {
    try {
      const parsed = JSON.parse(lines[i]);
      if (parsed && typeof parsed === "object" && Array.isArray(parsed.slots)) {
        return parsed;
      }
    } catch {
      // keep scanning for a JSON report line
    }
  }
  return null;
}

function mergeLiveReportIntoPlan(plan, report) {
  const reportSlots = Array.isArray(report?.slots) ? report.slots : [];
  const slots = (plan.slots ?? []).map((slot, index) => {
    const match =
      reportSlots.find((item) => item?.encoderId && item.encoderId === slot.encoderId) ??
      reportSlots[index];
    if (!match || typeof match !== "object") return slot;
    const next = { ...slot };
    if (match.status) next.status = match.status;
    const err = match.error ?? match.message;
    if (err) {
      next.error = err;
      next.message = err;
    } else if (match.status === "ok") {
      delete next.error;
      delete next.message;
    }
    return next;
  });
  const warnings = [...(plan.warnings ?? [])];
  for (const err of report?.errors ?? []) {
    if (err && !warnings.includes(err)) warnings.push(String(err));
  }
  return { ...plan, slots, warnings };
}

if (!customElements.get("panel-health")) {
  customElements.define("panel-health", PanelHealth);
}
