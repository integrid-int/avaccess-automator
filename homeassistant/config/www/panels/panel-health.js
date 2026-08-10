const SPORTS = [
  "Football",
  "Basketball",
  "Baseball",
  "Soccer",
  "Hockey",
  "Tennis",
];

const GROUPS = ["Ops Team", "VIP Clients", "Family Group", "Weekend Watch Party"];
const INDIVIDUALS = ["Alex", "Jordan", "Taylor", "Morgan", "Riley", "Casey"];
const STORAGE_KEY = "panel-health-sport-assignments-v1";

class PanelHealth extends HTMLElement {
  constructor() {
    super();
    this._hass = null;
    this._panel = null;
    this._selectedSport = SPORTS[0];
    this._assignments = this._loadAssignments();
    this._boundChangeHandler = this._handleChange.bind(this);
    this._boundClickHandler = this._handleClick.bind(this);
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
      this.addEventListener("change", this._boundChangeHandler);
      this.addEventListener("click", this._boundClickHandler);
      this._eventsBound = true;
    }
    this.render();
  }

  disconnectedCallback() {
    if (this._eventsBound) {
      this.removeEventListener("change", this._boundChangeHandler);
      this.removeEventListener("click", this._boundClickHandler);
      this._eventsBound = false;
    }
  }

  _emptyAssignment() {
    return { groups: [], individuals: [] };
  }

  _loadAssignments() {
    const defaults = {};
    for (const sport of SPORTS) {
      defaults[sport] = this._emptyAssignment();
    }

    try {
      const raw = window.localStorage.getItem(STORAGE_KEY);
      if (!raw) {
        return defaults;
      }

      const parsed = JSON.parse(raw);
      for (const sport of SPORTS) {
        const current = parsed[sport];
        if (!current) {
          continue;
        }
        defaults[sport] = {
          groups: Array.isArray(current.groups) ? current.groups : [],
          individuals: Array.isArray(current.individuals) ? current.individuals : [],
        };
      }
      return defaults;
    } catch (error) {
      console.warn("Unable to read panel assignments from storage", error);
      return defaults;
    }
  }

  _saveAssignments() {
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(this._assignments));
    } catch (error) {
      console.warn("Unable to save panel assignments", error);
    }
  }

  _assignmentForSport(sport) {
    if (!this._assignments[sport]) {
      this._assignments[sport] = this._emptyAssignment();
    }
    return this._assignments[sport];
  }

  _toggleValue(list, value, enabled) {
    const next = new Set(list);
    if (enabled) {
      next.add(value);
    } else {
      next.delete(value);
    }
    return Array.from(next);
  }

  _setAllAssignments(kind, values) {
    const assignment = this._assignmentForSport(this._selectedSport);
    assignment[kind] = [...values];
    this._saveAssignments();
    this.render();
  }

  _clearAssignments(kind) {
    const assignment = this._assignmentForSport(this._selectedSport);
    assignment[kind] = [];
    this._saveAssignments();
    this.render();
  }

  _handleChange(event) {
    const target = event.target;

    if (target.id === "sport-selector") {
      this._selectedSport = target.value;
      this.render();
      return;
    }

    const itemKind = target.dataset.kind;
    const itemValue = target.dataset.value;
    if (!itemKind || !itemValue) {
      return;
    }

    const assignment = this._assignmentForSport(this._selectedSport);
    assignment[itemKind] = this._toggleValue(assignment[itemKind], itemValue, target.checked);
    this._saveAssignments();
    this.render();
  }

  _handleClick(event) {
    const action = event.target.dataset.action;
    if (!action) {
      return;
    }

    if (action === "assign-all-groups") {
      this._setAllAssignments("groups", GROUPS);
      return;
    }
    if (action === "clear-groups") {
      this._clearAssignments("groups");
      return;
    }
    if (action === "assign-all-individuals") {
      this._setAllAssignments("individuals", INDIVIDUALS);
      return;
    }
    if (action === "clear-individuals") {
      this._clearAssignments("individuals");
    }
  }

  _summaryRows() {
    return SPORTS.map((sport) => {
      const assignment = this._assignmentForSport(sport);
      const groups = assignment.groups.length ? assignment.groups.join(", ") : "None";
      const individuals = assignment.individuals.length
        ? assignment.individuals.join(", ")
        : "None";
      return `
        <tr>
          <td>${sport}</td>
          <td>${groups}</td>
          <td>${individuals}</td>
        </tr>
      `;
    }).join("");
  }

  render() {
    if (!this.isConnected) {
      return;
    }

    const assignment = this._assignmentForSport(this._selectedSport);
    const stateCount = this._hass ? Object.keys(this._hass.states).length : 0;
    const env = this._panel?.config?.environment ?? "unknown";

    const groupOptions = GROUPS.map((group) => {
      const checked = assignment.groups.includes(group) ? "checked" : "";
      return `
        <label class="option">
          <input type="checkbox" data-kind="groups" data-value="${group}" ${checked}>
          <span>${group}</span>
        </label>
      `;
    }).join("");

    const individualOptions = INDIVIDUALS.map((individual) => {
      const checked = assignment.individuals.includes(individual) ? "checked" : "";
      return `
        <label class="option">
          <input type="checkbox" data-kind="individuals" data-value="${individual}" ${checked}>
          <span>${individual}</span>
        </label>
      `;
    }).join("");

    this.innerHTML = `
      <style>
        .panel-wrapper {
          padding: 16px;
          display: grid;
          gap: 16px;
          color: var(--primary-text-color);
        }
        .meta {
          display: flex;
          gap: 16px;
          flex-wrap: wrap;
          font-size: 14px;
        }
        .editor-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
          gap: 16px;
        }
        .card {
          border: 1px solid var(--divider-color);
          border-radius: 12px;
          padding: 16px;
          background: var(--card-background-color);
        }
        h2, h3 {
          margin: 0 0 12px 0;
        }
        .row {
          margin-bottom: 12px;
        }
        .option {
          display: flex;
          align-items: center;
          gap: 8px;
          margin-bottom: 6px;
        }
        .button-row {
          display: flex;
          gap: 8px;
          margin-top: 10px;
          flex-wrap: wrap;
        }
        button {
          border: 1px solid var(--divider-color);
          border-radius: 8px;
          padding: 6px 10px;
          background: var(--secondary-background-color);
          color: var(--primary-text-color);
          cursor: pointer;
        }
        table {
          width: 100%;
          border-collapse: collapse;
          font-size: 14px;
        }
        th, td {
          border: 1px solid var(--divider-color);
          padding: 8px;
          text-align: left;
          vertical-align: top;
        }
        th {
          background: var(--secondary-background-color);
        }
      </style>
      <ha-card header="Sports Assignment Panel">
        <div class="panel-wrapper">
          <div class="meta">
            <span><strong>Environment:</strong> ${env}</span>
            <span><strong>Loaded entities:</strong> ${stateCount}</span>
            <span><strong>Route:</strong> /panel-health</span>
          </div>
          <div class="editor-grid">
            <section class="card">
              <h2>Assignment Editor</h2>
              <div class="row">
                <label for="sport-selector"><strong>Sport</strong></label><br>
                <select id="sport-selector">
                  ${SPORTS.map((sport) => {
                    const selected = sport === this._selectedSport ? "selected" : "";
                    return `<option value="${sport}" ${selected}>${sport}</option>`;
                  }).join("")}
                </select>
              </div>

              <div class="row">
                <h3>Assign to Groups</h3>
                ${groupOptions}
                <div class="button-row">
                  <button data-action="assign-all-groups" type="button">Assign all groups</button>
                  <button data-action="clear-groups" type="button">Clear groups</button>
                </div>
              </div>

              <div class="row">
                <h3>Assign to Individuals</h3>
                ${individualOptions}
                <div class="button-row">
                  <button data-action="assign-all-individuals" type="button">Assign all individuals</button>
                  <button data-action="clear-individuals" type="button">Clear individuals</button>
                </div>
              </div>
            </section>

            <section class="card">
              <h2>Assignment Summary</h2>
              <table>
                <thead>
                  <tr>
                    <th>Sport</th>
                    <th>Groups</th>
                    <th>Individuals</th>
                  </tr>
                </thead>
                <tbody>
                  ${this._summaryRows()}
                </tbody>
              </table>
            </section>
          </div>
        </div>
      </ha-card>
    `;
  }
}

customElements.define("panel-health", PanelHealth);
