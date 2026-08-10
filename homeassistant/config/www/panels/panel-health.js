class PanelHealth extends HTMLElement {
  set hass(hass) {
    this._hass = hass;
    this.render();
  }

  set panel(panelConfig) {
    this._panel = panelConfig;
    this.render();
  }

  connectedCallback() {
    this.render();
  }

  render() {
    if (!this.isConnected) {
      return;
    }

    const stateCount = this._hass ? Object.keys(this._hass.states).length : 0;
    const env = this._panel?.config?.environment ?? "unknown";

    this.innerHTML = `
      <ha-card header="Panel Health">
        <div style="padding: 16px;">
          <p><strong>Environment:</strong> ${env}</p>
          <p><strong>Loaded entities:</strong> ${stateCount}</p>
          <p>Panel is running from <code>/local/panels/panel-health.js</code>.</p>
        </div>
      </ha-card>
    `;
  }
}

customElements.define("panel-health", PanelHealth);
