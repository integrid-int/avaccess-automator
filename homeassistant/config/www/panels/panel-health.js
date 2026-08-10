/**
 * AVAccess bartender panel for Home Assistant Companion (iPad).
 * Sport tabs → game cards (logos + names) → preset groups or adhoc TVs 1–35.
 */
const STORAGE_KEY = "avaccess-bartender-panel-v1";

const PRESETS = [
  {
    id: "1_all",
    label: "Preset 1 — ALL",
    shortLabel: "ALL",
    description: "One game on every TV",
    tvs: range(1, 35),
  },
  {
    id: "2_four_programs",
    label: "Preset 2 — 4 Programs",
    shortLabel: "4 Prog",
    description: "Split across 4 encoder groups",
    tvs: range(1, 35),
    blocks: [
      { name: "A", tvs: range(1, 9) },
      { name: "B", tvs: range(10, 18) },
      { name: "C", tvs: range(19, 27) },
      { name: "D", tvs: range(28, 35) },
    ],
  },
  {
    id: "3_nine_programs",
    label: "Preset 3 — 9 Programs",
    shortLabel: "9 Prog",
    description: "Split across 9 encoder groups",
    tvs: range(1, 35),
    blocks: [
      { name: "1", tvs: range(1, 4) },
      { name: "2", tvs: range(5, 8) },
      { name: "3", tvs: range(9, 12) },
      { name: "4", tvs: range(13, 16) },
      { name: "5", tvs: range(17, 20) },
      { name: "6", tvs: range(21, 24) },
      { name: "7", tvs: range(25, 28) },
      { name: "8", tvs: range(29, 32) },
      { name: "9", tvs: range(33, 35) },
    ],
  },
];

const SPORTS = [
  {
    id: "nfl",
    title: "NFL",
    icon: "🏈",
    games: [
      game("nfl-1", "Chiefs", "kc", "Bills", "buf", "FOX", "1:00 PM"),
      game("nfl-2", "Eagles", "phi", "Cowboys", "dal", "CBS", "1:00 PM"),
      game("nfl-3", "49ers", "sf", "Seahawks", "sea", "FOX", "4:25 PM"),
      game("nfl-4", "Ravens", "bal", "Steelers", "pit", "NBC", "8:20 PM"),
      game("nfl-5", "Lions", "det", "Packers", "gb", "NFLN", "Thursday"),
    ],
  },
  {
    id: "cfb",
    title: "College Football",
    icon: "🎓",
    games: [
      game("cfb-1", "Georgia", "uga", "Alabama", "ala", "ABC", "3:30 PM", "ncaa"),
      game("cfb-2", "Ohio State", "osu", "Michigan", "mich", "FOX", "12:00 PM", "ncaa"),
      game("cfb-3", "Texas", "tex", "Oklahoma", "okla", "ESPN", "7:30 PM", "ncaa"),
      game("cfb-4", "USC", "usc", "Oregon", "ore", "NBC", "8:00 PM", "ncaa"),
    ],
  },
  {
    id: "basketball",
    title: "Basketball",
    icon: "🏀",
    games: [
      game("nba-1", "Lakers", "lal", "Celtics", "bos", "TNT", "7:30 PM", "nba"),
      game("nba-2", "Warriors", "gs", "Nuggets", "den", "ESPN", "10:00 PM", "nba"),
      game("nba-3", "Knicks", "ny", "Heat", "mia", "ABC", "3:00 PM", "nba"),
      game("nba-4", "Suns", "phx", "Mavericks", "dal", "ESPN2", "9:00 PM", "nba"),
    ],
  },
];

function range(start, end) {
  return Array.from({ length: end - start + 1 }, (_, index) => start + index);
}

function logoUrl(abbrev, league) {
  const sport = league || "nfl";
  return `https://a.espncdn.com/i/teamlogos/${sport}/500/${abbrev}.png`;
}

function game(id, away, awayAbbr, home, homeAbbr, channel, tipoff, league = "nfl") {
  return {
    id,
    away,
    home,
    channel,
    tipoff,
    awayLogo: logoUrl(awayAbbr, league),
    homeLogo: logoUrl(homeAbbr, league),
  };
}

class PanelHealth extends HTMLElement {
  constructor() {
    super();
    this._hass = null;
    this._panel = null;
    this._sportId = SPORTS[0].id;
    this._selectedGameId = null;
    this._selectedTvs = [];
    this._activePresetId = null;
    this._assignments = this._loadAssignments();
    this._boundClick = this._onClick.bind(this);
    this._boundChange = this._onChange.bind(this);
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
    if (!this._eventsBound) {
      this.addEventListener("click", this._boundClick);
      this.addEventListener("change", this._boundChange);
      this._eventsBound = true;
    }
    this.render();
  }

  disconnectedCallback() {
    if (this._eventsBound) {
      this.removeEventListener("click", this._boundClick);
      this.removeEventListener("change", this._boundChange);
      this._eventsBound = false;
    }
  }

  _loadAssignments() {
    try {
      const raw = window.localStorage.getItem(STORAGE_KEY);
      return raw ? JSON.parse(raw) : {};
    } catch (error) {
      console.warn("Unable to load bartender assignments", error);
      return {};
    }
  }

  _saveAssignments() {
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(this._assignments));
    } catch (error) {
      console.warn("Unable to save bartender assignments", error);
    }
  }

  _sport() {
    return SPORTS.find((sport) => sport.id === this._sportId) || SPORTS[0];
  }

  _selectedGame() {
    const sport = this._sport();
    return sport.games.find((item) => item.id === this._selectedGameId) || null;
  }

  _gameLabel(gameItem) {
    return `${gameItem.away} @ ${gameItem.home}`;
  }

  _onClick(event) {
    const target = event.target.closest("[data-action]");
    if (!target) {
      return;
    }

    const action = target.dataset.action;
    const value = target.dataset.value;

    if (action === "select-sport") {
      this._sportId = value;
      this._selectedGameId = null;
      this._selectedTvs = [];
      this._activePresetId = null;
      this.render();
      return;
    }

    if (action === "select-game") {
      this._selectedGameId = value;
      const existing = this._assignments[value];
      this._selectedTvs = existing?.tvs ? [...existing.tvs] : [];
      this._activePresetId = existing?.presetId || null;
      this.render();
      return;
    }

    if (action === "toggle-tv") {
      const tv = Number(value);
      const next = new Set(this._selectedTvs);
      if (next.has(tv)) {
        next.delete(tv);
      } else {
        next.add(tv);
      }
      this._selectedTvs = Array.from(next).sort((a, b) => a - b);
      this._activePresetId = null;
      this.render();
      return;
    }

    if (action === "apply-preset") {
      const preset = PRESETS.find((item) => item.id === value);
      if (!preset) {
        return;
      }
      this._activePresetId = preset.id;
      // For bartender speed: ALL fills every TV. Multi-program presets
      // preselect the first block so the operator can expand/adjust.
      if (preset.id === "1_all") {
        this._selectedTvs = [...preset.tvs];
      } else if (preset.blocks?.length) {
        this._selectedTvs = [...preset.blocks[0].tvs];
      } else {
        this._selectedTvs = [...preset.tvs];
      }
      this.render();
      return;
    }

    if (action === "select-preset-block") {
      const [presetId, blockName] = value.split(":");
      const preset = PRESETS.find((item) => item.id === presetId);
      const block = preset?.blocks?.find((item) => item.name === blockName);
      if (!block) {
        return;
      }
      this._activePresetId = presetId;
      this._selectedTvs = [...block.tvs];
      this.render();
      return;
    }

    if (action === "select-all-tvs") {
      this._selectedTvs = range(1, 35);
      this._activePresetId = "1_all";
      this.render();
      return;
    }

    if (action === "clear-tvs") {
      this._selectedTvs = [];
      this._activePresetId = null;
      this.render();
      return;
    }

    if (action === "apply-assignment") {
      this._applyAssignment();
      return;
    }

    if (action === "clear-game-assignment") {
      if (!this._selectedGameId) {
        return;
      }
      delete this._assignments[this._selectedGameId];
      this._selectedTvs = [];
      this._activePresetId = null;
      this._saveAssignments();
      this.render();
    }
  }

  _onChange() {
    // Checkbox fallback path not required; TV toggles use click actions.
  }

  _applyAssignment() {
    const gameItem = this._selectedGame();
    if (!gameItem || this._selectedTvs.length === 0) {
      return;
    }

    // One TV can only show one game: remove overlapping TVs from other games.
    const selected = new Set(this._selectedTvs);
    for (const [gameId, assignment] of Object.entries(this._assignments)) {
      if (gameId === gameItem.id) {
        continue;
      }
      assignment.tvs = assignment.tvs.filter((tv) => !selected.has(tv));
      if (assignment.tvs.length === 0) {
        delete this._assignments[gameId];
      }
    }

    this._assignments[gameItem.id] = {
      sportId: this._sportId,
      label: this._gameLabel(gameItem),
      channel: gameItem.channel,
      presetId: this._activePresetId,
      tvs: [...this._selectedTvs],
      updatedAt: new Date().toISOString(),
    };
    this._saveAssignments();
    this.render();
  }

  _tvStatus(tv) {
    for (const assignment of Object.values(this._assignments)) {
      if (assignment.tvs.includes(tv)) {
        return assignment;
      }
    }
    return null;
  }

  _presetBlocksMarkup(preset) {
    if (!preset.blocks) {
      return "";
    }
    return `
      <div class="block-row">
        ${preset.blocks
          .map((block) => {
            const active =
              this._activePresetId === preset.id &&
              this._selectedTvs.join(",") === block.tvs.join(",")
                ? "is-active"
                : "";
            return `
              <button
                type="button"
                class="block-chip ${active}"
                data-action="select-preset-block"
                data-value="${preset.id}:${block.name}"
              >
                ${block.name}
                <span>${block.tvs[0]}–${block.tvs[block.tvs.length - 1]}</span>
              </button>
            `;
          })
          .join("")}
      </div>
    `;
  }

  render() {
    if (!this.isConnected) {
      return;
    }

    const sport = this._sport();
    const selectedGame = this._selectedGame();
    const env = this._panel?.config?.environment ?? "live";

    this.innerHTML = `
      <style>
        @import url("https://fonts.googleapis.com/css2?family=Manrope:wght@500;600;700;800&family=IBM+Plex+Sans:wght@400;500;600&display=swap");

        :host, .wrap {
          font-family: "IBM Plex Sans", "Segoe UI", sans-serif;
          color: #142033;
          display: block;
          min-height: 100%;
          background:
            radial-gradient(1200px 500px at 10% -10%, #d9ecff 0%, transparent 55%),
            radial-gradient(900px 420px at 100% 0%, #dff7ea 0%, transparent 50%),
            linear-gradient(180deg, #f3f7fb 0%, #eef3f8 100%);
        }

        .wrap {
          padding: 18px 18px 28px;
          box-sizing: border-box;
        }

        .topbar {
          display: flex;
          justify-content: space-between;
          align-items: flex-end;
          gap: 12px;
          margin-bottom: 14px;
        }

        .brand {
          font-family: Manrope, sans-serif;
          font-weight: 800;
          font-size: clamp(1.4rem, 2.4vw, 2rem);
          letter-spacing: -0.03em;
          line-height: 1.1;
        }

        .brand span {
          display: block;
          font-size: 0.78rem;
          font-weight: 600;
          letter-spacing: 0.08em;
          text-transform: uppercase;
          color: #4d627a;
          margin-bottom: 4px;
        }

        .meta {
          color: #4d627a;
          font-size: 0.9rem;
          text-align: right;
        }

        .tabs {
          display: flex;
          gap: 8px;
          overflow-x: auto;
          padding-bottom: 4px;
          margin-bottom: 14px;
        }

        .tab {
          border: 0;
          border-radius: 999px;
          padding: 12px 18px;
          font-family: Manrope, sans-serif;
          font-weight: 700;
          font-size: 1rem;
          background: rgba(255, 255, 255, 0.72);
          color: #24364d;
          cursor: pointer;
          white-space: nowrap;
          box-shadow: inset 0 0 0 1px rgba(20, 32, 51, 0.08);
        }

        .tab.is-active {
          background: #0f7a4c;
          color: #fff;
          box-shadow: none;
        }

        .layout {
          display: grid;
          grid-template-columns: minmax(0, 1.35fr) minmax(320px, 0.9fr);
          gap: 14px;
          align-items: start;
        }

        @media (max-width: 980px) {
          .layout {
            grid-template-columns: 1fr;
          }
        }

        .panel {
          background: rgba(255, 255, 255, 0.86);
          border-radius: 22px;
          box-shadow: 0 10px 30px rgba(20, 32, 51, 0.08);
          padding: 14px;
        }

        .games {
          display: grid;
          gap: 10px;
        }

        .game {
          display: grid;
          grid-template-columns: 1fr auto;
          gap: 10px;
          align-items: center;
          width: 100%;
          text-align: left;
          border: 0;
          border-radius: 18px;
          padding: 12px 14px;
          background: #f7fafc;
          box-shadow: inset 0 0 0 1px rgba(20, 32, 51, 0.06);
          cursor: pointer;
        }

        .game.is-selected {
          background: #e8f7ef;
          box-shadow: inset 0 0 0 2px #0f7a4c;
        }

        .matchup {
          display: flex;
          align-items: center;
          gap: 10px;
          min-width: 0;
        }

        .team {
          display: flex;
          align-items: center;
          gap: 8px;
          min-width: 0;
        }

        .team img {
          width: 42px;
          height: 42px;
          object-fit: contain;
          flex: 0 0 auto;
          background: #fff;
          border-radius: 50%;
          padding: 4px;
          box-shadow: inset 0 0 0 1px rgba(20, 32, 51, 0.08);
        }

        .team strong {
          font-family: Manrope, sans-serif;
          font-size: 1.02rem;
          font-weight: 700;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }

        .at {
          color: #6a7d93;
          font-weight: 700;
          padding: 0 2px;
        }

        .game-meta {
          text-align: right;
          color: #4d627a;
          font-size: 0.86rem;
          line-height: 1.35;
        }

        .game-meta b {
          display: block;
          color: #142033;
          font-size: 0.95rem;
        }

        .section-title {
          font-family: Manrope, sans-serif;
          font-weight: 800;
          font-size: 1.05rem;
          margin: 0 0 10px;
        }

        .hint {
          color: #4d627a;
          font-size: 0.9rem;
          margin: 0 0 12px;
        }

        .preset-grid {
          display: grid;
          gap: 8px;
          margin-bottom: 12px;
        }

        .preset {
          border: 0;
          border-radius: 14px;
          padding: 12px;
          text-align: left;
          background: #f4f7fb;
          cursor: pointer;
          box-shadow: inset 0 0 0 1px rgba(20, 32, 51, 0.08);
        }

        .preset.is-active {
          background: #e7f1ff;
          box-shadow: inset 0 0 0 2px #1d5fbf;
        }

        .preset strong {
          display: block;
          font-family: Manrope, sans-serif;
          font-size: 0.98rem;
        }

        .preset span {
          color: #4d627a;
          font-size: 0.84rem;
        }

        .block-row {
          display: flex;
          flex-wrap: wrap;
          gap: 6px;
          margin: 8px 0 4px;
        }

        .block-chip {
          border: 0;
          border-radius: 10px;
          padding: 8px 10px;
          background: #fff;
          cursor: pointer;
          font-weight: 600;
          box-shadow: inset 0 0 0 1px rgba(20, 32, 51, 0.1);
        }

        .block-chip span {
          display: block;
          font-size: 0.75rem;
          color: #4d627a;
          font-weight: 500;
        }

        .block-chip.is-active {
          background: #1d5fbf;
          color: #fff;
        }

        .block-chip.is-active span {
          color: rgba(255, 255, 255, 0.85);
        }

        .tv-toolbar {
          display: flex;
          gap: 8px;
          margin-bottom: 8px;
        }

        .tv-toolbar button,
        .actions button {
          border: 0;
          border-radius: 12px;
          padding: 12px 14px;
          font-family: Manrope, sans-serif;
          font-weight: 700;
          cursor: pointer;
        }

        .ghost {
          background: #e8eef5;
          color: #24364d;
        }

        .primary {
          background: #0f7a4c;
          color: #fff;
          flex: 1;
        }

        .danger {
          background: #f3e6e6;
          color: #8a2f2f;
        }

        .tv-grid {
          display: grid;
          grid-template-columns: repeat(7, minmax(0, 1fr));
          gap: 6px;
          margin-bottom: 12px;
        }

        .tv {
          aspect-ratio: 1;
          border: 0;
          border-radius: 12px;
          background: #f2f5f8;
          font-family: Manrope, sans-serif;
          font-weight: 800;
          font-size: 0.95rem;
          cursor: pointer;
          box-shadow: inset 0 0 0 1px rgba(20, 32, 51, 0.08);
        }

        .tv.is-selected {
          background: #0f7a4c;
          color: #fff;
        }

        .tv.is-assigned:not(.is-selected) {
          background: #ffe8c7;
        }

        .actions {
          display: flex;
          gap: 8px;
        }

        .summary {
          margin-top: 12px;
          border-radius: 14px;
          background: #f7fafc;
          padding: 10px 12px;
          font-size: 0.9rem;
        }

        .summary ul {
          margin: 8px 0 0;
          padding-left: 18px;
        }

        .empty {
          padding: 28px 12px;
          text-align: center;
          color: #4d627a;
        }
      </style>

      <div class="wrap">
        <div class="topbar">
          <div class="brand">
            <span>AVAccess · iPad Bar Panel</span>
            Sports Routing
          </div>
          <div class="meta">
            Env: ${env}<br>
            TVs online: 35
          </div>
        </div>

        <div class="tabs" role="tablist" aria-label="Sports">
          ${SPORTS.map(
            (item) => `
              <button
                type="button"
                class="tab ${item.id === sport.id ? "is-active" : ""}"
                data-action="select-sport"
                data-value="${item.id}"
              >
                ${item.icon} ${item.title}
              </button>
            `
          ).join("")}
        </div>

        <div class="layout">
          <section class="panel">
            <h2 class="section-title">${sport.title} games</h2>
            <p class="hint">Tap a game, then send it to a preset group or pick TVs 1–35.</p>
            <div class="games">
              ${sport.games
                .map((item) => {
                  const assigned = this._assignments[item.id];
                  return `
                    <button
                      type="button"
                      class="game ${item.id === this._selectedGameId ? "is-selected" : ""}"
                      data-action="select-game"
                      data-value="${item.id}"
                    >
                      <div class="matchup">
                        <div class="team">
                          <img src="${item.awayLogo}" alt="${item.away} logo" loading="lazy">
                          <strong>${item.away}</strong>
                        </div>
                        <div class="at">@</div>
                        <div class="team">
                          <img src="${item.homeLogo}" alt="${item.home} logo" loading="lazy">
                          <strong>${item.home}</strong>
                        </div>
                      </div>
                      <div class="game-meta">
                        <b>${item.channel}</b>
                        ${item.tipoff}
                        ${
                          assigned
                            ? `<div>TVs: ${assigned.tvs.join(", ")}</div>`
                            : "<div>Unassigned</div>"
                        }
                      </div>
                    </button>
                  `;
                })
                .join("")}
            </div>
          </section>

          <aside class="panel">
            ${
              selectedGame
                ? `
                  <h2 class="section-title">Assign ${this._gameLabel(selectedGame)}</h2>
                  <p class="hint">Groups use project presets. Adhoc lets you multi-select any TVs.</p>

                  <div class="preset-grid">
                    ${PRESETS.map((preset) => {
                      const active = this._activePresetId === preset.id ? "is-active" : "";
                      return `
                        <button
                          type="button"
                          class="preset ${active}"
                          data-action="apply-preset"
                          data-value="${preset.id}"
                        >
                          <strong>${preset.label}</strong>
                          <span>${preset.description}</span>
                          ${this._presetBlocksMarkup(preset)}
                        </button>
                      `;
                    }).join("")}
                  </div>

                  <div class="tv-toolbar">
                    <button type="button" class="ghost" data-action="select-all-tvs">Select 1–35</button>
                    <button type="button" class="ghost" data-action="clear-tvs">Clear TVs</button>
                  </div>

                  <div class="tv-grid" aria-label="TV picker">
                    ${range(1, 35)
                      .map((tv) => {
                        const selected = this._selectedTvs.includes(tv) ? "is-selected" : "";
                        const occupied = this._tvStatus(tv) ? "is-assigned" : "";
                        return `
                          <button
                            type="button"
                            class="tv ${selected} ${occupied}"
                            data-action="toggle-tv"
                            data-value="${tv}"
                          >${tv}</button>
                        `;
                      })
                      .join("")}
                  </div>

                  <div class="actions">
                    <button type="button" class="primary" data-action="apply-assignment">
                      Apply to ${this._selectedTvs.length || 0} TV${this._selectedTvs.length === 1 ? "" : "s"}
                    </button>
                    <button type="button" class="danger" data-action="clear-game-assignment">
                      Clear
                    </button>
                  </div>
                `
                : `
                  <div class="empty">
                    <h2 class="section-title">Choose a game</h2>
                    <p class="hint">Select a matchup to assign presets or individual TVs.</p>
                  </div>
                `
            }

            <div class="summary">
              <strong>Live assignments</strong>
              ${
                Object.keys(this._assignments).length
                  ? `<ul>
                      ${Object.values(this._assignments)
                        .map(
                          (item) =>
                            `<li><b>${item.label}</b> → TVs ${item.tvs.join(", ")}${
                              item.presetId ? ` (${item.presetId})` : ""
                            }</li>`
                        )
                        .join("")}
                    </ul>`
                  : "<p class=\"hint\" style=\"margin:8px 0 0\">No routes yet.</p>"
              }
            </div>
          </aside>
        </div>
      </div>
    `;
  }
}

if (!customElements.get("panel-health")) {
  customElements.define("panel-health", PanelHealth);
}
