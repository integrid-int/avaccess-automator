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
} from "./assignment-store.js?v=18";
import {
  GUIDE_CHANNELS,
  PRESETS,
  SPECTRUM_ZIP,
  SPORTS,
  STORAGE_KEY,
  TOKENS,
  filterGuideChannels,
  mergeGuideWithEpg,
  range,
} from "./panel-data.js?v=19";
import { buildRoutePlan, listReplaceChoices, stripedTvs } from "./route-planner.js?v=19";

const DEFAULT_STATE = {
  screen: "browse-sport",
  sportId: SPORTS[0]?.id ?? null,
  leagueId: "all",
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
  selectedTvSetId: null,
  replaceEncoderId: null,
  replaceDismissed: false,
  draftSetId: null,
  draftName: "",
  draftTvs: [],
  setError: "",
};

const LIVE_BLOCKED_WARNING = "Live blocked: inventory not ready";
const LIVE_BLOCKED_REASON = "Live commit is off until the room inventory is set up.";
const INVENTORY_JSON_URL = "/local/avaccess/inventory.json";
const GUIDE_EPG_JSON_URL = "/local/avaccess/guide_epg.json";
const GUIDE_CHANNELS_JSON_URL = "/local/avaccess/guide_channels.json";
// Sports pages use the DirecTV sports-info slate only. Guide listings are TV Passport.
const SPORTS_JSON_URL = "/local/avaccess/sports_schedule.json";
const SPORTS_SOURCE = "directv-sports-info";
const TV_SETS_JSON_URL = "/local/avaccess/custom_tv_sets.json";
const TV_SETS_KEY = "avaccess-tv-sets-v1";
const TV_SETS_SOURCE = "tv-sets";
const MAX_TV_SETS = 8;
const GUIDE_EPG_REFRESH_MS = 15 * 60 * 1000;
const GUIDE_SEARCH_DELAY_MS = 300;
const GUIDE_UNAVAILABLE_BANNER =
  "Guide listings unavailable — channel list only";

const SCREEN_TITLES = {
  "browse-sport": "Sports",
  "browse-guide": "Guide",
  "now-playing": "Now playing",
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
    this.guideEpg = null;
    this.guideEpgAvailable = false;
    this.guideChannels = null;
    this.sportsSchedule = null;
    this._guideEpgTimer = null;
    this._guideSearchTimer = null;
    this._guideQueryDraft = null;
  }

  get hass() {
    return this._hass;
  }

  set hass(hass) {
    this._hass = hass;
    const liveBefore = this._state.liveCommit;
    this._syncLiveCommitFromHass();
    // HA pushes state often. Rebuilding the guide while a letter is in the
    // box drops focus, so wait until the search pause finishes.
    if (this._guideSearchTimer || this._searchInputIsFocused()) {
      if (this._state.liveCommit !== liveBefore) this.render();
      return;
    }
    this.render();
  }

  set panel(panelConfig) {
    this._panel = panelConfig;
    this.render();
  }

  connectedCallback() {
    this._assignments = this._loadAssignments();
    this._tvSets = this._loadTvSetsFromStorage() ?? [];
    if (!this._eventsBound) {
      this.addEventListener("click", this._boundClick);
      this.addEventListener("input", this._boundInput);
      this._eventsBound = true;
    }
    this._loadInventoryLiveReady();
    this._loadTvSets();
    this._loadGuideChannels();
    this._loadGuideEpg();
    this._loadSportsSchedule();
    if (!this._guideEpgTimer) {
      this._guideEpgTimer = setInterval(() => {
        this._loadGuideEpg();
        this._loadSportsSchedule();
      }, GUIDE_EPG_REFRESH_MS);
    }
    this.render();
  }

  disconnectedCallback() {
    if (this._eventsBound) {
      this.removeEventListener("click", this._boundClick);
      this.removeEventListener("input", this._boundInput);
      this._eventsBound = false;
    }
    if (this._guideEpgTimer) {
      clearInterval(this._guideEpgTimer);
      this._guideEpgTimer = null;
    }
    if (this._guideSearchTimer) {
      clearTimeout(this._guideSearchTimer);
      this._guideSearchTimer = null;
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

  _loadTvSetsFromStorage() {
    const storage = this._storage();
    if (!storage) return null;
    try {
      const raw = storage.getItem(TV_SETS_KEY);
      if (!raw) return null;
      return normalizeTvSets(JSON.parse(raw));
    } catch {
      return null;
    }
  }

  async _loadTvSets() {
    if (this._storage()?.getItem(TV_SETS_KEY)) return;
    try {
      const response = await fetch(TV_SETS_JSON_URL, { cache: "no-store" });
      if (!response.ok) return;
      const payload = await response.json();
      if (payload?.source !== TV_SETS_SOURCE) return;
      const sets = normalizeTvSets(payload);
      if (!sets.length) return;
      this._tvSets = sets;
      if (this.isConnected) this.render();
    } catch {
      // The iPad copy is the working set until Home Assistant has the file.
    }
  }

  async _persistTvSets() {
    const payload = { source: TV_SETS_SOURCE, sets: this._tvSets };
    const storage = this._storage();
    if (storage) storage.setItem(TV_SETS_KEY, JSON.stringify(payload));
    if (!this.hass?.callService) return;
    try {
      const sets_b64 = btoa(unescape(encodeURIComponent(JSON.stringify(payload))));
      await this.hass.callService("shell_command", "avaccess_save_tv_sets", { sets_b64 });
    } catch {
      // The iPad still has the sets. A new iPad picks them up after the file save works.
    }
  }

  _clearReplaceChoice() {
    return { replaceEncoderId: null, replaceDismissed: false };
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

  async _loadGuideEpg() {
    try {
      const response = await fetch(GUIDE_EPG_JSON_URL, { cache: "no-store" });
      if (!response.ok) {
        this.guideEpg = null;
        this.guideEpgAvailable = false;
      } else {
        const feed = await response.json();
        this.guideEpg = feed;
        const { epgAvailable } = mergeGuideWithEpg(this._lineup(), feed);
        this.guideEpgAvailable = epgAvailable;
      }
    } catch {
      this.guideEpg = null;
      this.guideEpgAvailable = false;
    }
    if (this.isConnected) this.render();
  }

  async _loadGuideChannels() {
    try {
      const response = await fetch(GUIDE_CHANNELS_JSON_URL, { cache: "no-store" });
      if (response.ok) {
        const payload = await response.json();
        if (payload.source === "tvpassport:5960D" && Array.isArray(payload.channels) && payload.channels.length) {
          this.guideChannels = payload.channels;
        }
      }
    } catch {
      this.guideChannels = this.guideChannels || null;
    }
    if (this.isConnected) this.render();
  }

  _lineup() {
    return this.guideChannels?.length ? this.guideChannels : GUIDE_CHANNELS;
  }

  async _loadSportsSchedule() {
    try {
      const response = await fetch(SPORTS_JSON_URL, { cache: "no-store" });
      if (response.ok) {
        const payload = await response.json();
        if (
          payload.source === SPORTS_SOURCE &&
          Array.isArray(payload.sports) &&
          payload.sports.length
        ) {
          this.sportsSchedule = payload.sports;
        }
      }
    } catch {
      this.sportsSchedule = this.sportsSchedule || null;
    }
    if (this.isConnected) this.render();
  }

  _sports() {
    return this.sportsSchedule?.length ? this.sportsSchedule : SPORTS;
  }

  _guideFeedState() {
    const { channels, epgAvailable } = mergeGuideWithEpg(this._lineup(), this.guideEpg);
    const sorted = [...channels].sort(
      (a, b) => channelNumberValue(a.number) - channelNumberValue(b.number)
    );
    return {
      channels: filterGuideChannels(sorted, this._state.guideQuery),
      guideEpgAvailable: epgAvailable,
    };
  }

  _guideUnavailableBannerHtml(guideEpgAvailable) {
    if (guideEpgAvailable) return "";
    return `<div class="guide-epg-banner" role="status">${GUIDE_UNAVAILABLE_BANNER}</div>`;
  }

  _guideRowClass(guideEpgAvailable) {
    // Without EPG data the now/next columns would only show dashes; collapse them.
    return guideEpgAvailable ? "guide-row" : "guide-row no-epg";
  }

  _renderGuideRowCells(channel, guideEpgAvailable = true) {
    const nowTitle = channel.nowTitle ? String(channel.nowTitle) : "";
    const nextTitle = channel.nextTitle ? String(channel.nextTitle) : "";
    const listings = guideEpgAvailable
      ? `
      <span class="guide-now" title="${escapeAttr(nowTitle)}">${nowTitle ? escapeHtml(nowTitle) : "—"}</span>
      <span class="guide-next" title="${escapeAttr(nextTitle)}">${nextTitle ? escapeHtml(nextTitle) : "—"}</span>`
      : "";
    return `
      <b>${escapeHtml(channel.number)}</b>
      <span class="guide-name">${escapeHtml(channel.name)}</span>${listings}
      ${this._routeBadgeHtml(channel.id)}
    `;
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
      ? "When on, Send tunes DirecTV (SHEF) and switches video (UDP) via Home Assistant"
      : LIVE_BLOCKED_REASON;
    // iPads never show title tooltips, so the hint carries the full reason inline.
    const hint = ready
      ? active
        ? "Live — Send changes the TVs"
        : "Dry run — Send only previews the plan"
      : LIVE_BLOCKED_REASON;
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
        <span class="live-commit-hint ${ready ? "" : "is-blocked"}" role="status">${escapeHtml(hint)}</span>
      </div>
    `;
  }

  _deepActiveElement() {
    let node = document.activeElement;
    while (node && node.shadowRoot && node.shadowRoot.activeElement) {
      node = node.shadowRoot.activeElement;
    }
    return node;
  }

  _searchInputIsFocused() {
    const active = this._deepActiveElement();
    return active?.dataset?.action === "guide-search";
  }

  _captureNamedCaret(action) {
    const active = this.querySelector?.(`[data-action="${action}"]`);
    if (!active || this._deepActiveElement() !== active) return null;
    return { start: active.selectionStart, end: active.selectionEnd };
  }

  _restoreNamedCaret(action, snapshot) {
    if (!snapshot) return;
    const input = this.querySelector?.(`[data-action="${action}"]`);
    if (!input) return;
    input.focus({ preventScroll: true });
    try {
      input.setSelectionRange(snapshot.start, snapshot.end);
    } catch {
      // Focus alone keeps the field usable.
    }
  }

  _captureGuideSearchCaret() {
    const active = this.querySelector?.('[data-action="guide-search"]');
    if (!active || this._deepActiveElement() !== active) return null;
    return {
      value: active.value,
      start: active.selectionStart,
      end: active.selectionEnd,
    };
  }

  _restoreGuideSearchCaret(snapshot) {
    const input = this.querySelector?.('[data-action="guide-search"]');
    if (!input) return;
    const typing = this._guideSearchTimer != null && this._guideQueryDraft != null;
    if (!snapshot && !typing) return;
    if (typing && this._guideQueryDraft !== input.value) {
      input.value = this._guideQueryDraft;
    }
    input.focus({ preventScroll: true });
    try {
      const start = snapshot?.start ?? input.value.length;
      const end = snapshot?.end ?? start;
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
          ${game.home
            ? `<span class="team">
            <img class="team-logo" src="${escapeAttr(game.awayLogo)}" alt="" width="36" height="36" loading="lazy">
            <span>${escapeHtml(game.away)}</span>
          </span>
          <span class="at" aria-hidden="true">@</span>
          <span class="team">
            <img class="team-logo" src="${escapeAttr(game.homeLogo)}" alt="" width="36" height="36" loading="lazy">
            <span>${escapeHtml(game.home)}</span>
          </span>`
            : `<span class="team"><span>${escapeHtml(game.away)}</span></span>`}
        </span>
        <span class="card-meta">
          <span class="card-cta ${action === "toggle-program" ? "" : "has-chevron"}">${escapeHtml(cta)}</span>
          ${this._routeBadgeHtml(game.id)}
        </span>
      </button>
    `;
  }

  _activeSport() {
    const sports = this._sports();
    return sports.find((sport) => sport.id === this._state.sportId) ?? sports[0];
  }

  _gamesFor(sport) {
    const games = sport?.games ?? [];
    const leagueId = this._state.leagueId || "all";
    if (leagueId === "all") return games;
    const matched = games.filter((game) => game.leagueId === leagueId);
    return matched.length ? matched : games;
  }

  _gameLabel(game) {
    if (!game?.home) return game?.away || "";
    return `${game.away} @ ${game.home}`;
  }

  _renderLeagueChips(sport) {
    const leagues = Array.isArray(sport?.leagues) ? sport.leagues : [];
    if (leagues.length < 2) return "";
    const active = this._state.leagueId || "all";
    const buttons = [
      `<button type="button" class="chip ${active === "all" ? "is-active" : ""}" data-action="select-league" data-value="all">All</button>`,
      ...leagues.map(
        (league) => `
          <button
            type="button"
            class="chip ${active === league.id ? "is-active" : ""}"
            data-action="select-league"
            data-value="${escapeAttr(league.id)}"
          >${escapeHtml(league.chipTitle ?? league.title)}</button>
        `
      ),
    ];
    return `<nav class="chips league-chips" aria-label="Leagues">${buttons.join("")}</nav>`;
  }

  _selectedContentLabel() {
    const content = this._state.selectedContent;
    if (!content) return "No content selected";
    if (content.kind === "channel") return `${content.number} ${content.name}`;
    return this._gameLabel(content);
  }

  _onClick(event) {
    const target = event.target.closest?.("[data-action]");
    if (!target) return;

    const { action, value } = target.dataset;
    if (action === "open-sport" || action === "select-sport") {
      // A guide row must not stay selected after the rail moves to a sport,
      // unless staff are already building a 4- or 9-program list.
      const dropChannel = !this._isMultiPreset() && this._state.selectedContent?.kind === "channel";
      this._setState({
        screen: "browse-sport",
        sportId: value || this._state.sportId,
        leagueId: "all",
        contentMode: "sports",
        entryPath: "content",
        ...(dropChannel ? { selectedContent: null, selectedPrograms: [] } : {}),
      });
      return;
    }
    if (action === "select-league") {
      this._setState({
        screen: "browse-sport",
        leagueId: value || "all",
        contentMode: "sports",
      });
      return;
    }
    if (action === "open-guide") {
      this._setState({
        screen: "browse-guide",
        contentMode: "guide",
        entryPath: "content",
      });
      return;
    }
    if (action === "open-now") {
      this._setState({ screen: "now-playing" });
      return;
    }
    if (action === "open-tvs") {
      this._setDestMode("tvs");
      this._setState({
        selectedTvSetId: null,
        selectedPrograms: [],
        ...this._clearReplaceChoice(),
      });
      return;
    }
    if (action === "open-sets") {
      const first = this._tvSets[0];
      this._setState({
        screen: "edit-sets",
        draftSetId: first?.id ?? null,
        draftName: first?.name ?? "",
        draftTvs: first ? [...first.tvs] : [],
        setError: "",
      });
      return;
    }
    if (action === "new-tv-set") {
      if (this._tvSets.length >= MAX_TV_SETS) {
        this._setState({ setError: "8 sets is the limit. Delete one first." });
        return;
      }
      this._setState({ draftSetId: null, draftName: "", draftTvs: [], setError: "" });
      return;
    }
    if (action === "edit-tv-set") {
      const set = this._tvSets.find((item) => item.id === value);
      if (!set) return;
      this._setState({
        screen: "edit-sets",
        draftSetId: set.id,
        draftName: set.name,
        draftTvs: [...set.tvs],
        setError: "",
      });
      return;
    }
    if (action === "save-tv-set") {
      this._saveTvSet();
      return;
    }
    if (action === "delete-tv-set") {
      this._deleteTvSet();
      return;
    }
    if (action === "select-tv-set") {
      this._selectTvSet(value);
      return;
    }
    if (action === "choose-replace") {
      this._setState({ replaceEncoderId: value, replaceDismissed: false });
      return;
    }
    if (action === "dismiss-replace") {
      this._setState({ replaceDismissed: true, replaceEncoderId: null });
      return;
    }
    if (action === "reopen-replace") {
      this._setState({ replaceDismissed: false });
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
      if (this._state.screen === "edit-sets") {
        this._setState({ draftTvs: [], setError: "" });
        return;
      }
      this._setState({
        selectedTvs: [],
        selectedPresetId: null,
        selectedTvSetId: null,
        groupMode: null,
        ...this._clearReplaceChoice(),
      });
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
    if (target?.dataset?.action === "set-name") {
      this._setNameDraft = target.value;
      this._setState({ draftName: target.value, setError: "" });
      return;
    }
    if (target?.dataset?.action !== "guide-search") return;
    this._guideQueryDraft = target.value;
    if (this._guideSearchTimer) clearTimeout(this._guideSearchTimer);
    this._guideSearchTimer = setTimeout(() => {
      this._guideSearchTimer = null;
      const next = this._guideQueryDraft ?? "";
      if (next === this._state.guideQuery) return;
      this._setState({ guideQuery: next });
    }, GUIDE_SEARCH_DELAY_MS);
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
    const game = this._sports().flatMap((item) => item.games.map((sportGame) => ({ sport: item, game: sportGame }))).find(
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
    this._setState({
      screen: "browse-sport",
      selectedContent,
      sportId: game.sport.id,
      contentMode: "sports",
      entryPath: "content",
      selectedPrograms: this._isMultiPreset() ? this._state.selectedPrograms : [],
    });
  }

  _selectChannel(channelId) {
    const channel = this._lineup().find((item) => item.id === channelId);
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
    this._setState({
      screen: "browse-guide",
      selectedContent,
      contentMode: "guide",
      entryPath: "content",
      selectedPrograms: this._isMultiPreset() ? this._state.selectedPrograms : [],
    });
  }

  _activePreset() {
    return PRESETS.find((item) => item.id === this._state.selectedPresetId) ?? null;
  }

  _programsForMultiPreset() {
    if (this._state.selectedPrograms.length) return this._state.selectedPrograms;
    const content = this._state.selectedContent;
    if (!content) return [];
    const onGuide = this._state.screen === "browse-guide";
    const matches = onGuide ? content.kind === "channel" : content.kind === "game";
    return matches ? [this._toProgram(content)] : [];
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
      channelNumber: content.channelNumber ? String(content.channelNumber) : null,
    };
  }

  _findContentById(contentId) {
    for (const sport of this._sports()) {
      const game = sport.games.find((item) => item.id === contentId);
      if (game) return { ...game, kind: "game", sportId: sport.id };
    }
    const channel = this._lineup().find((item) => item.id === contentId);
    if (channel) return { ...channel, kind: "channel" };
    return null;
  }

  _selectGroup(presetId) {
    const preset = PRESETS.find((item) => item.id === presetId);
    if (!preset) return;
    if (preset.programCapacity > 1) {
      const selectedPrograms = this._programsForMultiPreset();
      this._setState({
        groupMode: preset.mode,
        selectedPresetId: presetId,
        selectedTvs: [],
        selectedTvSetId: null,
        selectedPrograms,
        destMode: "presets",
        screen: this._state.screen === "browse-guide" ? "browse-guide" : "browse-sport",
        ...this._clearReplaceChoice(),
      });
      return;
    }
    this._setState({
      groupMode: preset.mode,
      selectedTvs: [...preset.tvs],
      selectedPresetId: presetId,
      selectedTvSetId: null,
      destMode: "presets",
      ...this._clearReplaceChoice(),
    });
  }

  _selectTvSet(setId) {
    const set = this._tvSets.find((item) => item.id === setId);
    if (!set) return;
    const screen = this._state.screen === "browse-guide" ? "browse-guide" : this._state.screen === "edit-sets" ? "browse-sport" : this._state.screen;
    this._setState({
      selectedTvSetId: set.id,
      selectedTvs: [...set.tvs],
      selectedPresetId: null,
      selectedPrograms: [],
      destMode: "tvs",
      groupMode: "adhoc",
      screen: screen === "now-playing" ? "now-playing" : screen,
      ...this._clearReplaceChoice(),
    });
  }

  _saveTvSet() {
    const name = String(this._state.draftName || "").trim().slice(0, 24);
    const tvs = [...new Set(this._state.draftTvs.map((tv) => Number(tv)))]
      .filter((tv) => Number.isInteger(tv) && tv >= 1 && tv <= 35)
      .sort((a, b) => a - b);
    if (!name) {
      this._setState({ setError: "Name the set." });
      return;
    }
    if (!tvs.length) {
      this._setState({ setError: "Pick at least one TV." });
      return;
    }
    const duplicate = this._tvSets.some(
      (set) => set.id !== this._state.draftSetId && set.name.toLowerCase() === name.toLowerCase()
    );
    if (duplicate) {
      this._setState({ setError: "That name is already used." });
      return;
    }
    const id = this._state.draftSetId || `set-${Date.now()}`;
    const next = this._tvSets.filter((set) => set.id !== id);
    if (!this._state.draftSetId && next.length >= MAX_TV_SETS) {
      this._setState({ setError: "8 sets is the limit. Delete one first." });
      return;
    }
    next.push({ id, name, tvs });
    next.sort((a, b) => a.name.localeCompare(b.name));
    this._tvSets = next;
    this._persistTvSets();
    this._setState({ draftSetId: id, draftName: name, draftTvs: tvs, setError: "" });
  }

  _deleteTvSet() {
    const id = this._state.draftSetId;
    if (!id) {
      this._setState({ draftName: "", draftTvs: [], setError: "" });
      return;
    }
    this._tvSets = this._tvSets.filter((set) => set.id !== id);
    this._persistTvSets();
    const first = this._tvSets[0];
    this._setState({
      draftSetId: first?.id ?? null,
      draftName: first?.name ?? "",
      draftTvs: first ? [...first.tvs] : [],
      selectedTvSetId: this._state.selectedTvSetId === id ? null : this._state.selectedTvSetId,
      setError: "",
    });
  }

  _toggleProgram(contentId) {
    const content = this._findContentById(contentId);
    if (!content) return;
    const program = this._toProgram(content);
    const existing = this._state.selectedPrograms;
    const index = existing.findIndex((item) => item.id === program.id);
    if (index >= 0) {
      const selectedPrograms = existing.filter((item) => item.id !== program.id);
      const last = selectedPrograms[selectedPrograms.length - 1];
      this._setState({
        selectedPrograms,
        selectedContent: last ? this._findContentById(last.id) : null,
      });
      return;
    }
    const capacity = this._programCapacity();
    if (existing.length >= capacity) return;
    const selectedPrograms = [...existing, program];
    const last = selectedPrograms[selectedPrograms.length - 1];
    this._setState({
      selectedPrograms,
      selectedContent: this._findContentById(last.id),
      contentMode: content.kind === "channel" ? "guide" : "sports",
      sportId: content.sportId ?? this._state.sportId,
    });
  }

  _toggleTv(tv) {
    if (!Number.isInteger(tv)) return;
    if (this._state.screen === "edit-sets") {
      const selected = new Set(this._state.draftTvs);
      if (selected.has(tv)) selected.delete(tv);
      else selected.add(tv);
      this._setState({
        draftTvs: Array.from(selected).sort((a, b) => a - b),
        setError: "",
      });
      return;
    }
    const selected = new Set(this._state.selectedTvs);
    if (selected.has(tv)) selected.delete(tv);
    else selected.add(tv);
    this._setState({
      selectedTvs: Array.from(selected).sort((a, b) => a - b),
      selectedPresetId: null,
      selectedTvSetId: null,
      destMode: "tvs",
      groupMode: "adhoc",
      ...this._clearReplaceChoice(),
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
      assignments: this._assignments,
      replaceEncoderId: groupMode === "adhoc" ? this._state.replaceEncoderId : null,
      commit,
    });
    if (plan.error) {
      this._setState({
        lastPlan: plan.error === "No free encoders" ? this._state.lastPlan : plan,
        groupMode,
        replaceDismissed: plan.error === "No free encoders" ? false : this._state.replaceDismissed,
      });
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
      destMode: "presets",
      selectedPresetId: null,
      selectedTvSetId: null,
      selectedTvs: [],
      replaceEncoderId: null,
      replaceDismissed: false,
      screen: this._browseScreenForContent(),
    });
  }

  _sendDestination() {
    const content = this._state.selectedContent;
    if (!content) return;

    // Planner modes (including leftover preset_2/3) never fall through to applyAssignment.
    if (this._shouldSendViaPlan()) {
      const groupMode = this._state.destMode === "tvs" ? "adhoc" : this._state.groupMode;
      const multi = groupMode === "preset_2" || groupMode === "preset_3";
      if (multi && this._state.selectedPrograms.length === 0) return;
      const programs = multi ? this._state.selectedPrograms : [this._toProgram(content)];
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
        ${this._sports().map(
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
    const games = this._gamesFor(sport);
    return `
      <section class="screen">
        <div class="screen-heading">
          <p class="eyebrow">Browse sport</p>
          <h2>${escapeHtml(sport.title)}</h2>
        </div>
        ${this._renderLeagueChips(sport)}
        <div class="card-grid">
          ${games.length
            ? games
                .map((game) =>
                  this._renderGameCard(game, {
                    kicker: `${game.leagueTitle ? `${game.leagueTitle} - ` : ""}${game.channel} - ${game.tipoff}`,
                    cta: "Choose destination",
                  })
                )
                .join("")
            : `<p class="eyebrow">No games in this slate</p>`}
        </div>
      </section>
    `;
  }

  _renderGuideScreen() {
    const { channels, guideEpgAvailable } = this._guideFeedState();
    return `
      <section class="screen">
        <div class="screen-heading">
          <p class="eyebrow">Browse guide</p>
          <h2 aria-label="DirecTV · ZIP 27403">DirecTV · ZIP ${escapeHtml(SPECTRUM_ZIP)}</h2>
        </div>
        ${this._guideUnavailableBannerHtml(guideEpgAvailable)}
        <label class="search">
          <span>Search by channel, name, or title</span>
          <input data-action="guide-search" value="${escapeAttr(this._state.guideQuery)}" placeholder="ESPN, 206, SportsCenter" autocomplete="off" spellcheck="false">
        </label>
        <div class="list">
          ${channels
            .map(
              (channel) => `
                <button type="button" class="${this._guideRowClass(guideEpgAvailable)}" data-action="select-channel" data-value="${escapeAttr(channel.id)}">
                  ${this._renderGuideRowCells(channel, guideEpgAvailable)}
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
    const sendLabel = this._destinationSendLabel(viaPlan);
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
          ${escapeHtml(sendLabel)}
        </button>
      </section>
    `;
  }

  _destinationSendLabel(viaPlan) {
    const count = this._state.selectedTvs.length;
    if (!this._state.selectedContent) return "Choose content first";
    if (count === 0) return "Pick a preset or TVs";
    const suffix = viaPlan ? (this._state.liveCommit ? " (LIVE)" : " (dry run)") : "";
    return `Send ${this._selectedContentLabel()} → ${count} TV${count === 1 ? "" : "s"}${suffix}`;
  }

  _renderPresetChoices() {
    return `
      <div class="preset-row preset-grid">
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
        ? `TVs ${tvs.slice(0, 4).join(", ")}${tvs.length > 4 ? "…" : ""}`
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
        const tuneNumber = slot.tune && slot.tune.channelNumber;
        const tune = tuneNumber ? ` · Tune ${escapeHtml(String(tuneNumber))}` : "";
        return `
          <li>
            <b>${escapeHtml(slot.encoderId)}</b>
            · ${escapeHtml(slot.program?.label ?? "Program")}
            · ${escapeHtml(this._formatTvList(slot.tvs))}${tune}
            ${status}
          </li>
        `;
      })
      .join("");
    const replaced = plan.replaced?.offTvs?.length
      ? `<li><b>${escapeHtml(plan.replaced.label)}</b> off · ${escapeHtml(this._formatTvList(plan.replaced.offTvs))}</li>`
      : "";
    return `
      <aside class="dry-run-summary" aria-live="polite">
        <div class="dry-run-heading">
          <p class="eyebrow">${summaryLabel}</p>
          <button type="button" class="link-button" data-action="dismiss-plan">Dismiss</button>
        </div>
        ${error}
        ${warnings}
        ${slots || replaced ? `<ul class="plan-slots">${slots}${replaced}</ul>` : ""}
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
        ${this._sports().map(
          (sport) => `
            <div class="content-section">
              <h3>${escapeHtml(sport.title)}</h3>
              <div class="card-grid">
                ${sport.games
                  .map((game) =>
                    this._renderGameCard(game, {
                      kicker: `${game.leagueTitle || sport.chipTitle || sport.title} - ${game.channel} - ${game.tipoff}`,
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
    const { channels, guideEpgAvailable } = this._guideFeedState();
    const selectedIds = new Set(this._state.selectedPrograms.map((item) => item.id));
    return `
      ${this._guideUnavailableBannerHtml(guideEpgAvailable)}
      <label class="search">
        <span>Search by channel, name, or title</span>
        <input data-action="guide-search" value="${escapeAttr(this._state.guideQuery)}" placeholder="ESPN, 206, SportsCenter">
      </label>
      <div class="list">
        ${channels
          .map((channel) => {
            const selected = selectedIds.has(channel.id) ? "is-selected" : "";
            return `
              <button type="button" class="${this._guideRowClass(guideEpgAvailable)} ${selected}" data-action="toggle-program" data-value="${escapeAttr(channel.id)}">
                ${this._renderGuideRowCells(channel, guideEpgAvailable)}
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
        ${this._sports().map(
          (sport) => `
            <div class="content-section">
              <h3>${escapeHtml(sport.title)}</h3>
              <div class="card-grid">
                ${sport.games
                  .map((game) =>
                    this._renderGameCard(game, {
                      kicker: `${game.leagueTitle || sport.chipTitle || sport.title} - ${game.channel} - ${game.tipoff}`,
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
    const { channels, guideEpgAvailable } = this._guideFeedState();
    return `
      ${this._guideUnavailableBannerHtml(guideEpgAvailable)}
      <label class="search">
        <span>Search by channel, name, or title</span>
        <input data-action="guide-search" value="${escapeAttr(this._state.guideQuery)}" placeholder="ESPN, 206, SportsCenter">
      </label>
      <div class="list">
        ${channels
          .map((channel) => {
            const selected = this._state.selectedContent?.id === channel.id ? "is-selected" : "";
            return `
              <button type="button" class="${this._guideRowClass(guideEpgAvailable)} ${selected}" data-action="select-channel" data-value="${escapeAttr(channel.id)}">
                ${this._renderGuideRowCells(channel, guideEpgAvailable)}
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
        <span>${this._state.selectedTvs.length} picked</span>
        <button type="button" data-action="clear-tvs">Clear TVs</button>
      </div>
      <div class="tv-grid" aria-label="TV picker">
        ${range(1, 35)
          .map((tv) => {
            const assignment = getAssignmentForTv(this._assignments, tv);
            const selected = this._state.selectedTvs.includes(tv) ? "is-selected" : "";
            const assigned = assignment ? "is-assigned" : "";
            const occupancy = this._tvOccupancy(assignment);
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
                ${occupancy ? `<span class="tv-occupancy">${escapeHtml(occupancy)}</span>` : ""}
              </button>
            `;
          })
          .join("")}
      </div>
    `;
  }

  _isMultiPreset() {
    const preset = this._activePreset();
    return Boolean(preset && preset.programCapacity > 1 && this._state.destMode === "presets");
  }

  _sourceIsOn(id) {
    if (this._isMultiPreset() || this._state.selectedPrograms.length > 1) {
      return (
        this._state.selectedPrograms.some((item) => item.id === id) ||
        this._state.selectedContent?.id === id
      );
    }
    return this._state.selectedContent?.id === id;
  }

  _hasSource() {
    if (this._isMultiPreset()) return this._state.selectedPrograms.length > 0;
    return Boolean(this._state.selectedContent);
  }

  _hasDisplay() {
    if (this._state.destMode === "tvs") return this._state.selectedTvs.length > 0;
    const preset = this._activePreset();
    if (!preset) return false;
    if (preset.programCapacity > 1) return true;
    return this._state.selectedTvs.length > 0;
  }

  _formatTvList(tvs) {
    const nums = [...(tvs || [])].map((value) => Number(value)).filter((value) => Number.isInteger(value));
    if (!nums.length) return "no TVs";
    const sorted = [...nums].sort((a, b) => a - b);
    const contiguous = sorted.every((value, index) => index === 0 || value === sorted[index - 1] + 1);
    if (sorted.length > 4 && contiguous) return `TVs ${sorted[0]}–${sorted[sorted.length - 1]}`;
    if (sorted.length > 6) return `${sorted.length} TVs`;
    return `TVs ${sorted.join(", ")}`;
  }

  _tvOccupancy(assignment) {
    if (!assignment) return "";
    const channel = String(assignment.channel || "").trim();
    if (!channel) return "On";
    return channel.length > 8 ? channel.slice(0, 8) : channel;
  }

  _adhocPreview() {
    if (this._state.destMode !== "tvs" || !this._hasSource() || this._state.selectedTvs.length === 0) {
      return null;
    }
    const content = this._state.selectedContent;
    return buildRoutePlan({
      mode: "adhoc",
      programs: content ? [this._toProgram(content)] : [],
      selectedTvs: this._state.selectedTvs,
      busyEncoderIds: listBusyEncoderIds(this._assignments),
      assignments: this._assignments,
      replaceEncoderId: this._state.replaceEncoderId,
      commit: "dry_run",
    });
  }

  _needsReplace() {
    if (this._state.screen === "edit-sets" || this._state.replaceEncoderId) return false;
    if (this._state.destMode !== "tvs" || !this._hasSource() || this._state.selectedTvs.length === 0) return false;
    const plan = buildRoutePlan({
      mode: "adhoc",
      programs: [this._toProgram(this._state.selectedContent)],
      selectedTvs: this._state.selectedTvs,
      busyEncoderIds: listBusyEncoderIds(this._assignments),
      assignments: this._assignments,
      commit: "dry_run",
    });
    return plan.error === "No free encoders";
  }

  _takeError() {
    const preset = this._activePreset();
    if (
      preset &&
      preset.programCapacity === 1 &&
      this._state.destMode === "presets" &&
      this._state.selectedPrograms.length > 1
    ) {
      const name = preset.id === "1_all" ? "All 35 TVs" : preset.shortLabel;
      return `${name} takes one program. Tap the one to keep.`;
    }
    const plan = this._adhocPreview();
    if (!plan?.error || plan.error === "No free encoders") return "";
    return plan.error;
  }

  _routeStatusLabel() {
    if (this._state.screen === "edit-sets") return "Editing TV sets";
    if (this._needsReplace()) return "All DirecTV boxes are in use";
    const error = this._takeError();
    if (error) return error;
    const pending = this._pendingRouteLabel();
    if (pending) return `Ready · ${pending}`;
    const routes = Object.values(this._assignments || {}).filter((route) => route?.tvs?.length);
    if (!routes.length) return "No route";
    routes.sort((a, b) => String(b.updatedAt || "").localeCompare(String(a.updatedAt || "")));
    const route = routes[0];
    return `${route.label} · ${this._formatTvList(route.tvs)}`;
  }

  _destinationName() {
    if (this._state.selectedTvSetId) {
      const set = this._tvSets.find((item) => item.id === this._state.selectedTvSetId);
      if (set) return set.name;
    }
    if (this._state.destMode === "tvs") return this._formatTvList(this._state.selectedTvs);
    const preset = this._activePreset();
    return preset?.id === "1_all" ? "All 35 TVs" : preset?.shortLabel ?? "";
  }

  _pendingRouteLabel() {
    if (this._state.screen === "edit-sets") return "";
    if (this._needsReplace()) return "All DirecTV boxes are in use. Choose one to replace.";
    if (!this._hasSource() || !this._hasDisplay()) return "";
    if (this._state.replaceEncoderId) {
      const choice = listReplaceChoices(this._assignments).find(
        (item) => item.encoderId === this._state.replaceEncoderId
      );
      const source = this._selectedContentLabel();
      const oldLabel = choice?.label || "that program";
      return `Replace ${oldLabel} with ${source} on ${this._destinationName()}`;
    }
    if (this._isMultiPreset() && this._state.selectedPrograms.length === 0) return "";
    let source = this._selectedContentLabel();
    const listed = this._isMultiPreset() ? this._state.selectedPrograms : null;
    if (listed && listed.length > 1) {
      source = `${listed.length} programs`;
    } else if (listed && listed.length === 1) {
      const program = listed[0];
      const tune = program?.channelNumber ? `Tune ${program.channelNumber}` : "";
      source = program?.label || source;
      if (tune) source = `${source} · ${tune}`;
    } else if (this._state.selectedPrograms.length > 1) {
      source = `${this._state.selectedPrograms.length} programs`;
    } else {
      const program =
        this._state.selectedPrograms[0] || this._toProgram(this._state.selectedContent);
      const tune = program?.channelNumber ? `Tune ${program.channelNumber}` : "";
      if (tune) source = `${source} · ${tune}`;
    }
    return `${source}  →  ${this._destinationName()}`;
  }

  _renderGameKey(game) {
    const on = this._sourceIsOn(game.id) ? " on" : "";
    const action = this._isMultiPreset() ? "toggle-program" : "select-game";
    const logos = game.home
      ? `<img class="team-logo" src="${escapeAttr(game.awayLogo)}" alt="" width="28" height="28">
          <img class="team-logo" src="${escapeAttr(game.homeLogo)}" alt="" width="28" height="28">`
      : "";
    const league = game.leagueTitle ? `${game.leagueTitle} · ` : "";
    return `
      <button type="button" class="key${on}" data-action="${action}" data-value="${escapeAttr(game.id)}">
        <span class="mark">
          ${logos}
        </span>
        <span class="key-copy">
          <b>${escapeHtml(this._gameLabel(game))}</b>
          <small>${escapeHtml(league)}${escapeHtml(game.channel)} · ${escapeHtml(game.tipoff)}</small>
        </span>
        ${this._routeBadgeHtml(game.id)}
      </button>
    `;
  }

  _renderChannelKey(channel) {
    const on = this._sourceIsOn(channel.id) ? " on" : "";
    const action = this._isMultiPreset() ? "toggle-program" : "select-channel";
    const detail = channel.nowTitle ? `Now: ${channel.nowTitle}` : channel.category || "";
    return `
      <button type="button" class="key${on}" data-action="${action}" data-value="${escapeAttr(channel.id)}">
        <span class="mark">${escapeHtml(channel.number)}</span>
        <span class="key-copy">
          <b>${escapeHtml(channel.name)}</b>
          <small>${escapeHtml(detail)}</small>
        </span>
        ${this._routeBadgeHtml(channel.id)}
      </button>
    `;
  }

  _renderNowPlaying() {
    const rows = range(1, 35).map((tv) => {
      const assignment = getAssignmentForTv(this._assignments, tv);
      const program = assignment?.label ? String(assignment.label) : "Off";
      const channel = assignment ? String(assignment.channel || "").trim() : "";
      const detail = channel && channel !== program ? channel : assignment ? "On" : "No program";
      return `
        <div class="key now-row${assignment ? "" : " off"}">
          <span class="mark">${tv}</span>
          <span class="key-copy">
            <b>${escapeHtml(program)}</b>
            <small>${escapeHtml(detail)}</small>
          </span>
        </div>
      `;
    });
    const onCount = range(1, 35).filter((tv) => getAssignmentForTv(this._assignments, tv)).length;
    return `
      <h2>Now playing</h2>
      <p class="now-count">${onCount} of 35 TVs on</p>
      <div class="keys" aria-label="Now playing">
        ${rows.join("")}
      </div>
    `;
  }

  _renderRail() {
    const onGuide = this._state.screen === "browse-guide";
    const onNow = this._state.screen === "now-playing";
    const onSets = this._state.screen === "edit-sets";
    return `
      <nav class="rail" aria-label="Source types">
        ${this._sports().map(
          (item) => `
            <button
              type="button"
              class="${!onGuide && !onNow && !onSets && item.id === this._state.sportId ? "on" : ""}"
              data-action="select-sport"
              data-value="${escapeAttr(item.id)}"
            >${escapeHtml(item.chipTitle ?? item.title)}</button>
          `
        ).join("")}
        <button type="button" class="${onGuide ? "on" : ""}" data-action="open-guide">Guide</button>
        <button type="button" class="${onNow ? "on" : ""}" data-action="open-now">Now</button>
        <button type="button" class="${this._state.screen === "edit-sets" ? "on" : ""}" data-action="open-sets">Sets</button>
      </nav>
    `;
  }

  _renderReplaceChoices() {
    const choices = listReplaceChoices(this._assignments);
    const rows = choices
      .map((choice) => {
        const on = choice.encoderId === this._state.replaceEncoderId ? " on" : "";
        const channel = choice.channel ? `${choice.channel} · ` : "";
        return `
          <button type="button" class="key${on}" data-action="choose-replace" data-value="${escapeAttr(choice.encoderId)}">
            <span class="key-copy"><b>${escapeHtml(choice.label)}</b><small>${escapeHtml(channel)}${escapeHtml(this._formatTvList(choice.tvs))}</small></span>
          </button>
        `;
      })
      .join("");
    return `
      <h2>Choose a program</h2>
      <p class="now-count">The one you tap goes off. TVs that were on it and are not in ${escapeHtml(this._destinationName())} turn off.</p>
      <div class="keys">${rows}</div>
    `;
  }

  _renderSources() {
    if (this._state.screen === "edit-sets") return this._renderSetEditor();
    if (this._showReplaceSheet()) return this._renderReplaceChoices();
    if (this._state.screen === "now-playing") return this._renderNowPlaying();
    if (this._state.screen === "browse-guide") {
      const { channels, guideEpgAvailable } = this._guideFeedState();
      return `
        <h2 aria-label="DirecTV · ZIP 27403">DirecTV · ZIP ${escapeHtml(SPECTRUM_ZIP)}</h2>
        ${this._guideUnavailableBannerHtml(guideEpgAvailable)}
        <label class="search">
          <span>Search by channel, name, or title</span>
          <input data-action="guide-search" value="${escapeAttr(this._state.guideQuery)}" placeholder="ESPN, 206, SportsCenter" autocomplete="off" spellcheck="false">
        </label>
        <div class="keys">
          ${channels.map((channel) => this._renderChannelKey(channel)).join("")}
        </div>
      `;
    }
    const sport = this._activeSport();
    const games = this._gamesFor(sport);
    return `
      <h2>Sources</h2>
      ${this._renderLeagueChips(sport)}
      <div class="keys">
        ${games.length
          ? games.map((game) => this._renderGameKey(game)).join("")
          : `<p class="eyebrow">No games in this slate</p>`}
      </div>
    `;
  }

  _renderSetEditor() {
    const rows = this._tvSets
      .map((set) => {
        const on = set.id === this._state.draftSetId ? " on" : "";
        return `
          <button type="button" class="key${on}" data-action="edit-tv-set" data-value="${escapeAttr(set.id)}">
            <span class="key-copy"><b>${escapeHtml(set.name)}</b><small>${escapeHtml(this._formatTvList(set.tvs))}</small></span>
          </button>
        `;
      })
      .join("");
    return `
      <h2>TV sets</h2>
      <p class="now-count">Saved lists of TVs. They show under Displays on Sports and Guide.</p>
      <label class="search">
        <span>Name</span>
        <input data-action="set-name" value="${escapeAttr(this._state.draftName)}" placeholder="Patio" maxlength="24" autocomplete="off">
      </label>
      ${this._state.setError ? `<p class="plan-error">${escapeHtml(this._state.setError)}</p>` : ""}
      <div class="keys">
        ${rows || `<p class="eyebrow">No sets yet</p>`}
      </div>
      <div class="tv-toolbar">
        <button type="button" data-action="new-tv-set">New set</button>
      </div>
    `;
  }

  _renderDraftTvGrid() {
    return `
      <div class="tv-toolbar">
        <span>${this._state.draftTvs.length} picked</span>
        <button type="button" data-action="clear-tvs">Clear TVs</button>
        <button type="button" data-action="save-tv-set">Save</button>
        <button type="button" data-action="delete-tv-set">Delete</button>
      </div>
      <div class="tv-grid" aria-label="TVs in this set">
        ${range(1, 35)
          .map((tv) => {
            const selected = this._state.draftTvs.includes(tv) ? "is-selected" : "";
            return `
              <button type="button" class="tv ${selected}" data-action="toggle-tv" data-value="${tv}">
                <span class="tv-number">${tv}</span>
              </button>
            `;
          })
          .join("")}
      </div>
    `;
  }

  _renderDisplays() {
    if (this._state.screen === "edit-sets") {
      return `
        <h2>TVs in this set</h2>
        ${this._renderDraftTvGrid()}
      `;
    }
    const presetKeys = PRESETS.map((preset) => {
      const on = this._state.destMode === "presets" && this._state.selectedPresetId === preset.id ? " on" : "";
      const name = preset.id === "1_all" ? "All 35 TVs" : preset.shortLabel;
      const sub = preset.id === "1_all" ? "Preset 1" : preset.description;
      return `
        <button type="button" class="key${on}" data-action="select-group" data-value="${escapeAttr(preset.id)}">
          <span class="key-copy"><b>${escapeHtml(name)}</b><small>${escapeHtml(sub)}</small></span>
        </button>
      `;
    }).join("");
    const tvsOn = this._state.destMode === "tvs" && !this._state.selectedTvSetId ? " on" : "";
    const grid = this._state.destMode === "tvs" && !this._state.selectedTvSetId ? this._renderTvGrid() : "";
    const setKeys = this._tvSets
      .map((set) => {
        const on = this._state.selectedTvSetId === set.id ? " on" : "";
        return `
          <button type="button" class="key${on}" data-action="select-tv-set" data-value="${escapeAttr(set.id)}">
            <span class="key-copy"><b>${escapeHtml(set.name)}</b><small>${escapeHtml(this._formatTvList(set.tvs))}</small></span>
          </button>
        `;
      })
      .join("");
    return `
      <div class="preset-keys" aria-label="Presets">
        ${presetKeys}
        <button type="button" class="key${tvsOn}" data-action="open-tvs">
          <span class="key-copy"><b>Pick TVs</b><small>Choose TVs</small></span>
        </button>
        ${setKeys}
      </div>
      ${grid}
    `;
  }

  _renderTake() {
    if (this._state.screen === "edit-sets") {
      return `
        <footer class="take-bar">
          <div class="pending">Save the set. Take is for routing.</div>
          <button type="button" class="take" disabled aria-disabled="true">Take</button>
        </footer>
      `;
    }
    const error = this._takeError();
    const needsReplace = this._needsReplace();
    const ready = this._hasSource() && this._hasDisplay() && !error && !needsReplace;
    const label = this._state.replaceEncoderId ? "Replace" : "Take";
    const reopen = needsReplace && this._state.replaceDismissed
      ? `<button type="button" class="link-button reopen-replace" data-action="reopen-replace">Choose a program to replace</button>`
      : "";
    return `
      <footer class="take-bar">
        ${error ? `<div class="plan-error-banner">${escapeHtml(error)}</div>` : ""}
        <div class="pending">${escapeHtml(this._pendingRouteLabel())}</div>
        ${reopen}
        <button
          type="button"
          class="take${ready ? " ready" : ""}"
          data-action="send-destination"
          ${ready ? "" : "disabled aria-disabled=\"true\""}
        >${label}</button>
      </footer>
    `;
  }

  _showReplaceSheet() {
    if (this._state.screen === "edit-sets") return false;
    if (this._state.replaceEncoderId) return true;
    if (this._state.replaceDismissed) return false;
    return this._needsReplace();
  }

  _renderReplaceSheet() {
    if (!this._showReplaceSheet()) return "";
    const program = this._toProgram(this._state.selectedContent);
    const tune = program?.channelNumber ? ` · Tune ${program.channelNumber}` : "";
    const dest = this._destinationName();
    return `
      <aside class="dry-run-summary replace-sheet" aria-live="polite">
        <div class="dry-run-heading">
          <p class="eyebrow">Replace a program</p>
          <button type="button" class="link-button" data-action="dismiss-replace">Dismiss</button>
        </div>
        <p>${escapeHtml(dest)}${program ? ` · ${escapeHtml(program.label)}` : ""}${escapeHtml(tune)}</p>
      </aside>
    `;
  }

  _renderRoutingBoard() {
    return `
      <div class="board">
        ${this._renderRail()}
        <section class="bank">${this._renderSources()}</section>
        <section class="bank displays">
          ${this._state.screen === "edit-sets" ? "" : "<h2>Displays</h2>"}
          ${this._renderDisplays()}
        </section>
      </div>
      ${this._renderTake()}
    `;
  }

  render() {
    if (!this.isConnected) return;

    const guideSearchCaret = this._captureGuideSearchCaret();
    const setNameCaret = this._captureNamedCaret("set-name");

    this.innerHTML = `
      <style>
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
          font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif;
        }

        .shell {
          display: flex;
          flex-direction: column;
          min-height: 100vh;
          min-height: 100dvh;
          padding: 0;
          box-sizing: border-box;
          background: var(--graphite);
        }

        .stage {
          display: flex;
          flex: 1;
          flex-direction: column;
          background: var(--graphite);
          color: var(--text-stage);
          padding: 18px;
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
          grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
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

        .card-cta {
          background: var(--cyan-soft);
          border-radius: var(--radius-sm);
          color: var(--cyan);
          font-weight: 800;
          padding: 6px 10px;
        }

        .card-cta.has-chevron::after {
          content: " ›";
          font-weight: 900;
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

        .guide-epg-banner {
          color: var(--muted);
          font-weight: 700;
          margin: 0 0 12px;
        }

        .guide-row {
          align-items: center;
          display: grid;
          gap: 10px;
          grid-template-columns: 56px minmax(90px, 1.1fr) minmax(70px, 1fr) minmax(70px, 1fr) auto;
        }

        .guide-row.no-epg {
          grid-template-columns: 56px minmax(90px, 1fr) auto;
        }

        .guide-row b {
          color: var(--cyan);
          font-size: 1.1rem;
        }

        .guide-name {
          font-weight: 700;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }

        .guide-now,
        .guide-next {
          color: var(--muted);
          font-size: 0.9rem;
          overflow: hidden;
        }

        .guide-now {
          text-overflow: ellipsis;
          white-space: nowrap;
        }

        .guide-next {
          display: -webkit-box;
          -webkit-box-orient: vertical;
          -webkit-line-clamp: 2;
          white-space: normal;
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

        .preset-grid {
          align-items: stretch;
          display: grid;
          grid-template-columns: repeat(3, minmax(0, 1fr));
        }

        .preset-chip {
          height: 100%;
          text-align: left;
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
          background: rgba(255, 255, 255, 0.06);
          border-radius: var(--radius-md);
          display: grid;
          gap: 10px;
          grid-template-columns: auto minmax(0, 1fr);
          margin-bottom: 12px;
          padding: 8px;
        }

        .live-commit-toggle {
          background: rgba(165, 243, 252, 0.08);
          border: 1px solid rgba(165, 243, 252, 0.35);
          border-radius: var(--radius-md);
          color: var(--cyan-stage);
          flex-shrink: 0;
          font-weight: 800;
          padding: 10px 14px;
          white-space: nowrap;
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
          line-height: 1.35;
        }

        .live-commit-hint.is-blocked {
          color: #fcd34d;
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

          .preset-grid {
            grid-template-columns: 1fr;
          }
        }

        .routing {
          background: #101010;
          box-sizing: border-box;
          color: #f3f3f3;
          display: flex;
          flex-direction: column;
          font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif;
          height: calc(100dvh - 64px);
          max-height: calc(100dvh - 64px);
          min-height: 0;
          overflow: hidden;
        }

        .routing-top {
          align-items: baseline;
          display: flex;
          gap: 16px;
          justify-content: space-between;
          padding: 22px 28px 8px;
        }

        .routing .room {
          font-size: 22px;
          font-weight: 650;
        }

        .routing .status {
          color: #c8c8c8;
          font-size: 16px;
        }

        .routing .live-commit-row,
        .routing .dry-run-summary {
          margin: 0 28px 8px;
        }

        .routing .dry-run-summary {
          background: #1a1a1a;
          border-color: #2a2a2a;
          color: #f3f3f3;
          flex: 0 0 auto;
          max-height: 120px;
          overflow: auto;
        }

        .routing .replace-sheet {
          max-height: 110px;
        }

        .routing .reopen-replace {
          margin: 0 0 8px;
        }

        .routing .live-commit-row {
          flex: 0 0 auto;
        }

        .board {
          display: grid;
          flex: 1 1 auto;
          grid-template-columns: 148px minmax(0, 1fr) minmax(0, 1fr);
          min-height: 0;
          overflow: hidden;
        }

        .rail {
          border-right: 1px solid #242424;
          display: flex;
          flex-direction: column;
          min-height: 0;
          overflow: auto;
          padding: 8px 0;
        }

        .rail button {
          background: transparent;
          border: 0;
          border-left: 3px solid transparent;
          border-radius: 0;
          color: #8d8d8d;
          cursor: pointer;
          font: inherit;
          font-size: 16px;
          padding: 12px 16px;
          text-align: left;
        }

        .rail button.on {
          border-left-color: #0b5cab;
          color: #ffffff;
          font-weight: 650;
        }

        .bank {
          border-left: 1px solid #242424;
          min-height: 0;
          min-width: 0;
          overflow: auto;
          padding: 16px 18px 12px;
        }

        .bank h2 {
          color: #8d8d8d;
          font-size: 14px;
          font-weight: 500;
          margin: 0 0 10px;
        }

        .keys {
          display: flex;
          flex-direction: column;
          gap: 8px;
        }

        .preset-keys {
          display: grid;
          gap: 8px;
          grid-template-columns: 1fr 1fr;
        }

        .routing .key {
          align-items: center;
          background: linear-gradient(#323232, #2a2a2a);
          border: 0;
          border-radius: 3px;
          box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.07);
          color: #f3f3f3;
          cursor: pointer;
          display: flex;
          font: inherit;
          gap: 12px;
          min-height: 68px;
          padding: 10px 14px;
          text-align: left;
          width: 100%;
        }

        .routing .key.on {
          background: linear-gradient(#1470d4, #0b5cab);
        }

        .routing .now-row {
          cursor: default;
        }

        .routing .now-row.off {
          color: #8d8d8d;
        }

        .routing .now-count {
          color: #8d8d8d;
          font-size: 13px;
          margin: -4px 0 10px;
        }

        .routing .mark {
          align-items: center;
          display: flex;
          flex: 0 0 auto;
          gap: 4px;
          justify-content: center;
          width: 64px;
        }

        .routing .team-logo {
          height: 28px;
          object-fit: contain;
          width: 28px;
        }

        .routing .key-copy {
          min-width: 0;
        }

        .routing .key-copy b {
          display: block;
          font-size: 17px;
          font-weight: 650;
        }

        .routing .key-copy small {
          color: #bdbdbd;
          display: block;
          font-size: 13px;
          margin-top: 2px;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }

        .routing .key.on small {
          color: #d7e7f8;
        }

        .routing .route-badge {
          background: transparent;
          color: #d7e7f8;
          font-size: 12px;
          font-weight: 650;
          margin-left: auto;
          padding: 0;
        }

        .routing .link-button {
          background: #2a2a2a;
          border-radius: 3px;
          color: #f3f3f3;
        }

        .routing .dry-run-heading .eyebrow {
          color: #c8c8c8;
          letter-spacing: 0;
        }

        .routing .tv-toolbar {
          align-items: center;
          color: #c8c8c8;
          display: flex;
          gap: 8px;
          margin: 0 0 10px;
        }

        .routing .tv-toolbar button {
          background: #2a2a2a;
          border-radius: 3px;
          color: #f3f3f3;
        }

        .routing .tv-grid {
          gap: 8px;
          grid-template-columns: repeat(7, minmax(0, 1fr));
          margin-top: 8px;
        }

        .routing .tv {
          aspect-ratio: auto;
          background: #2a2a2a;
          border-radius: 3px;
          color: #f3f3f3;
          font-weight: 650;
          height: 52px;
        }

        .routing .tv.is-assigned:not(.is-selected) {
          background: #3a3a3a;
        }

        .routing .tv.is-selected {
          background: #0b5cab;
          color: #ffffff;
        }

        .routing .tv-number {
          font-size: 16px;
          line-height: 1;
        }

        .routing .tv-occupancy,
        .routing .tv.is-selected .tv-occupancy {
          color: #d7e7f8;
          font-size: 11px;
          line-height: 1.1;
          max-width: 100%;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }

        .routing .search span,
        .routing .guide-epg-banner {
          color: #c8c8c8;
        }

        .routing .search input {
          background: #1a1a1a;
          border: 1px solid #333333;
          border-radius: 3px;
          color: #f3f3f3;
        }

        .take-bar {
          border-top: 1px solid #242424;
          flex: 0 0 auto;
          padding: 12px 28px 18px;
        }

        .pending {
          font-size: 18px;
          margin-bottom: 8px;
          min-height: 24px;
          text-align: center;
        }

        .routing .plan-error {
          color: #fecaca;
        }

        .routing .plan-error-banner {
          background: #3a1d1d;
          border-radius: 3px;
          color: #fecaca;
          margin-bottom: 8px;
          padding: 10px 12px;
          text-align: center;
        }

        .take {
          background: #2a2a2a;
          border: 0;
          border-radius: 3px;
          color: #6a6a6a;
          font: inherit;
          font-size: 20px;
          font-weight: 700;
          height: 64px;
          width: 100%;
        }

        .take.ready {
          background: #0b5cab;
          color: #ffffff;
          cursor: pointer;
        }

        @media (max-width: 900px) {
          .board {
            grid-template-columns: 1fr;
          }

          .rail {
            border-bottom: 1px solid #242424;
            border-right: 0;
            flex-direction: row;
            overflow-x: auto;
          }

          .rail button {
            border-bottom: 3px solid transparent;
            border-left: 0;
            white-space: nowrap;
          }

          .rail button.on {
            border-bottom-color: #0b5cab;
            border-left-color: transparent;
          }

          .bank {
            border-left: 0;
          }

          .routing .tv-grid {
            grid-template-columns: repeat(5, minmax(0, 1fr));
          }
        }
      </style>

      <div class="routing">
        <header class="routing-top">
          <div class="room">Bar</div>
          <div class="status">${escapeHtml(this._routeStatusLabel())}</div>
          ${
            this._panel?.config?.debug
              ? `<div class="state-pill">Screen: ${escapeHtml(SCREEN_TITLES[this._state.screen])}</div>`
              : ""
          }
        </header>
        ${this._renderLiveCommitToggle()}
        ${this._showReplaceSheet() ? this._renderReplaceSheet() : this._renderDryRunSummary()}
        ${this._renderRoutingBoard()}
      </div>
    `;

    this._restoreGuideSearchCaret(guideSearchCaret);
    this._restoreNamedCaret("set-name", setNameCaret);
  }
}

function normalizeTvSets(payload) {
  const raw = Array.isArray(payload?.sets) ? payload.sets : Array.isArray(payload) ? payload : [];
  const sets = [];
  const names = new Set();
  for (const item of raw) {
    const name = String(item?.name || "").trim().slice(0, 24);
    const tvs = [...new Set((item?.tvs || []).map((tv) => Number(tv)))]
      .filter((tv) => Number.isInteger(tv) && tv >= 1 && tv <= 35)
      .sort((a, b) => a - b);
    if (!name || !tvs.length || names.has(name.toLowerCase())) continue;
    names.add(name.toLowerCase());
    sets.push({ id: String(item.id || `set-${sets.length + 1}`), name, tvs });
    if (sets.length >= MAX_TV_SETS) break;
  }
  return sets;
}

function channelNumberValue(number) {
  // "212" -> 212, "212-1" -> 212.001 so subchannels sort after their major.
  const [major, minor] = String(number ?? "").split(/[-.]/);
  const value = Number.parseInt(major, 10);
  if (!Number.isFinite(value)) return Number.POSITIVE_INFINITY;
  const sub = Number.parseInt(minor ?? "0", 10);
  return value + (Number.isFinite(sub) ? sub / 1000 : 0);
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
