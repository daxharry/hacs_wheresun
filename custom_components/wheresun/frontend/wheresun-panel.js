const VERSION = "0.2.4";

class WhereSunHousePanel extends HTMLElement {
  constructor() {
    super();
    this._hass = null;
    this._flowId = null;
  }

  set hass(hass) {
    this._hass = hass;
    this._render().catch((err) => {
      this.innerHTML = `<div style="padding:16px;color:#f44336;">${err.message || err}</div>`;
    });
  }

  async _render() {
    if (!this._hass) return;
    this.innerHTML =
      '<div style="padding:16px;color:var(--secondary-text-color,#aaa);">Loading editor…</div>';

    const result = await this._hass.callWS({ type: "wheresun/editor_active" });
    const flowId = result.flow_id;
    if (!flowId) {
      this.innerHTML =
        '<div style="padding:16px;max-width:640px;line-height:1.5;">' +
        "<strong>No active house layout step.</strong><br>" +
        "Open WhereSun configuration, start the house layout step, then open this page again." +
        "</div>";
      return;
    }

    this._flowId = flowId;
    const iframe = document.createElement("iframe");
    iframe.src = `/wheresun/editor.html?flow_id=${encodeURIComponent(flowId)}&v=${VERSION}`;
    iframe.title = "WhereSun house editor";
    iframe.style.cssText =
      "width:100%;height:calc(100vh - 64px);border:none;display:block;background:#111;";
    iframe.dataset.wheresunEditor = "1";
    this.innerHTML = "";
    this.appendChild(iframe);
  }
}

customElements.define("wheresun-house-panel", WhereSunHousePanel);
