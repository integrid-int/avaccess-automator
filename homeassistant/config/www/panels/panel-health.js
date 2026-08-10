import {
  applyAssignment,
  createEmptyAssignments,
  getAssignmentForTv,
  loadAssignments,
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

const DEFAULT_STATE = {
  screen: "browse-sport",
  sportId: SPORTS[0]?.id ?? null,
  guideQuery: "",
  selectedContent: null,
  selectedTvs: [],
  destMode: "presets",
  contentMode: "sports",
  entryPath: "content",
};

const SCREEN_TITLES = {
  "browse-sport": "Sports",
  "browse-guide": "Guide",
  "browse-tvs": "TVs",
  destination: "Destination",
  "content-picker": "Content Picker",
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
  }

  set hass(hass) {
    this._hass = hass;
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
      });
      return;
    }
    if (action === "open-guide") {
      this._setState({ screen: "browse-guide", contentMode: "guide", entryPath: "content" });
      return;
    }
    if (action === "open-tvs") {
      this._setState({ screen: "browse-tvs", entryPath: "tv", destMode: "presets", selectedContent: null });
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
    if (action === "open-content-picker") {
      this._setState({ screen: "content-picker" });
      return;
    }
    if (action === "set-dest-mode") {
      this._setState({ destMode: value === "presets" ? "presets" : "tvs" });
      return;
    }
    if (action === "set-tv-browse-mode") {
      this._setState({ destMode: value === "presets" ? "presets" : "tvs" });
      return;
    }
    if (action === "next-choose-content") {
      if (this._state.selectedTvs.length > 0) {
        this._setState({ screen: "content-picker", selectedContent: null });
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
    if (action === "apply-preset") {
      this._applyPreset(value);
      return;
    }
    if (action === "toggle-tv") {
      this._toggleTv(Number(value));
      return;
    }
    if (action === "clear-tvs") {
      this._setState({ selectedTvs: [] });
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
    return [...(this._assignments[routeId]?.tvs ?? [])].sort((a, b) => a - b);
  }

  _seedDestinationMode(routeId) {
    const assignment = this._assignments[routeId];
    if (!assignment?.tvs?.length) return "presets";
    return assignment.presetId ? "presets" : "tvs";
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
    this._setState({
      screen: "destination",
      selectedContent,
      selectedTvs: this._seedDestinationTvs(game.game.id),
      destMode: this._seedDestinationMode(game.game.id),
      contentMode: "sports",
      entryPath: "content",
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
    this._setState({
      screen: "destination",
      selectedContent,
      selectedTvs: this._seedDestinationTvs(channel.id),
      destMode: this._seedDestinationMode(channel.id),
      contentMode: "guide",
      entryPath: "content",
    });
  }

  _applyPreset(presetId) {
    const preset = PRESETS.find((item) => item.id === presetId);
    if (!preset) return;
    this._setState({ selectedTvs: [...preset.tvs], destMode: "presets" });
  }

  _toggleTv(tv) {
    if (!Number.isInteger(tv)) return;
    const selected = new Set(this._state.selectedTvs);
    if (selected.has(tv)) selected.delete(tv);
    else selected.add(tv);
    this._setState({ selectedTvs: Array.from(selected).sort((a, b) => a - b), destMode: "tvs" });
  }

  _backToBrowse() {
    this._setState({ screen: this._browseScreenForContent() });
  }

  _sendDestination() {
    const content = this._state.selectedContent;
    if (!content) return;
    const selectedTvs = [...this._state.selectedTvs].sort((a, b) => a - b);

    const assignments = applyAssignment(this._assignments, {
      routeId: content.id,
      kind: content.kind,
      sportId: content.sportId,
      label: this._selectedContentLabel(),
      channel: content.channel ?? content.number,
      presetId: this._state.destMode === "presets" ? PRESETS.find((preset) => sameTvs(preset.tvs, selectedTvs))?.id : null,
      tvs: selectedTvs,
    });
    this._saveAssignments(assignments);
    this._backToBrowse();
  }

  _sendTvFirst() {
    if (!this._state.selectedContent || this._state.selectedTvs.length === 0) return;
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
    return this._renderSportScreen();
  }

  _renderSportScreen() {
    const sport = this._activeSport();
    return `
      <section class="screen">
        <div class="screen-heading">
          <p class="eyebrow">Browse sport</p>
          <h2>${escapeHtml(sport.title)}</h2>
          <button type="button" class="link-button" data-action="open-content-picker">Open content picker</button>
        </div>
        <div class="card-grid">
          ${sport.games
            .map(
              (game) => `
                <button type="button" class="content-card" data-action="select-game" data-value="${escapeAttr(game.id)}">
                  <span class="card-kicker">${escapeHtml(game.channel)} - ${escapeHtml(game.tipoff)}</span>
                  <strong>${escapeHtml(game.away)} @ ${escapeHtml(game.home)}</strong>
                  <span>Choose destination</span>
                </button>
              `
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
        <div class="destination-body">
          ${this._state.destMode === "presets" ? this._renderPresetChoices() : this._renderTvGrid()}
        </div>
        <button type="button" class="primary-action" data-action="send-destination">
          Send to ${this._state.selectedTvs.length} TV${this._state.selectedTvs.length === 1 ? "" : "s"}
        </button>
      </section>
    `;
  }

  _renderPresetChoices() {
    return `
      <div class="preset-row">
        ${PRESETS.map(
          (preset) => `
            <button type="button" class="preset-chip" data-action="apply-preset" data-value="${escapeAttr(preset.id)}">
              <b>${escapeHtml(preset.shortLabel)}</b>
              <span>${escapeHtml(preset.description)}</span>
            </button>
          `
        ).join("")}
      </div>
    `;
  }

  _renderContentPickerScreen() {
    const tvFirst = this._state.entryPath === "tv";
    const sendDisabled = !this._state.selectedContent || this._state.selectedTvs.length === 0;
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
            ? `<button
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
                  .map((game) => {
                    const selected = this._state.selectedContent?.id === game.id ? "is-selected" : "";
                    return `
                      <button type="button" class="content-card ${selected}" data-action="select-game" data-value="${escapeAttr(game.id)}">
                        <span class="card-kicker">${escapeHtml(sport.chipTitle ?? sport.title)} - ${escapeHtml(game.channel)} - ${escapeHtml(game.tipoff)}</span>
                        <strong>${escapeHtml(game.away)} @ ${escapeHtml(game.home)}</strong>
                        <span>${this._state.entryPath === "tv" ? "Select content" : "Choose destination"}</span>
                      </button>
                    `;
                  })
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
          font-family: Inter, "Segoe UI", system-ui, sans-serif;
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

        .content-card strong {
          display: block;
          font-size: 1.05rem;
          margin: 6px 0;
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
          grid-template-columns: 64px 1fr auto;
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
        .preset-chip span {
          display: block;
        }

        .preset-chip span {
          color: var(--muted);
          font-size: 0.8rem;
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
              <span>Bartender HA panel</span>
              <h1>Graphite routing shell</h1>
            </div>
            <div class="state-pill">Screen: ${escapeHtml(SCREEN_TITLES[this._state.screen])}</div>
          </header>
          ${this._renderChipRow()}
          ${this._renderScreen()}
        </div>
      </div>
    `;
  }
}

function sameTvs(left, right) {
  return left.length === right.length && left.every((tv, index) => tv === right[index]);
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

if (!customElements.get("panel-health")) {
  customElements.define("panel-health", PanelHealth);
}
