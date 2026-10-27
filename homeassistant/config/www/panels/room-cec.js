// Room power and per-TV volume. The panel calls script.avaccess_cec.
// Step badges count presses from this iPad. The receiver does not report a level.

export const CEC_SCRIPT = "avaccess_cec";

const ACTIONS = {
  "power-on": "power-on",
  "power-off": "power-off",
  up: "volume-up",
  down: "volume-down",
  mute: "mute",
};

export function cecCallArgs(action, tv = 0) {
  const name = ACTIONS[action] || action;
  return ["script", CEC_SCRIPT, { action: name, tv: String(tv ?? 0) }, undefined, true, true];
}

export function parseCecReport(response) {
  const stdout =
    typeof response?.stdout === "string"
      ? response.stdout
      : typeof response?.response?.stdout === "string"
        ? response.response.stdout
        : "";
  const lines = stdout
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);
  for (let index = lines.length - 1; index >= 0; index -= 1) {
    try {
      const parsed = JSON.parse(lines[index]);
      if (parsed && typeof parsed === "object" && ("ok" in parsed || parsed.refused)) return parsed;
    } catch {
      // keep scanning
    }
  }
  return null;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function markText(mark) {
  if (!mark) return "";
  const parts = [];
  if (mark.steps > 0) parts.push(`+${mark.steps}`);
  else if (mark.steps < 0) parts.push(String(mark.steps));
  if (mark.mute) parts.push("M");
  return parts.join(" ");
}

function pickedMeta(mark) {
  if (!mark || (mark.steps === 0 && !mark.mute)) return "No steps yet";
  const step = mark.steps > 0 ? `+${mark.steps}` : String(mark.steps);
  const bits = [mark.steps === 0 ? "No steps yet" : `${step} this session`];
  if (mark.mute) bits.push("mute sent");
  return bits.join(" · ");
}

export function roomScreenHtml({
  live = false,
  busy = false,
  bannerText = "",
  bannerMode = "practice",
  statusText = "",
  selectedTv = 12,
  marks = {},
  note = "",
  confirm = false,
} = {}) {
  const locked = !live || busy;
  const disabled = locked ? "disabled" : "";
  const selected = marks[selectedTv] || marks[String(selectedTv)] || { steps: 0, mute: false };
  const tiles = [];
  for (let tv = 1; tv <= 35; tv += 1) {
    const mark = marks[tv] || marks[String(tv)];
    const noteText = markText(mark);
    const classes = ["room-tv"];
    if (tv === Number(selectedTv)) classes.push("is-selected");
    if (mark?.mute) classes.push("is-muted");
    tiles.push(
      `<button type="button" class="${classes.join(" ")}" data-action="room-tv" data-value="${tv}" aria-pressed="${tv === Number(selectedTv) ? "true" : "false"}"><b>${tv}</b><small>${escapeHtml(noteText)}</small></button>`,
    );
  }
  const confirmHtml = confirm
    ? `<div class="room-confirm" role="dialog" aria-label="Turn off all TVs">
        <div class="room-confirm-card">
          <h3>Turn off all 35 TVs?</h3>
          <p>They stay off until someone turns them back on from here.</p>
          <div class="room-confirm-row">
            <button type="button" class="room-cancel" data-action="room-cancel-off">Cancel</button>
            <button type="button" class="room-danger" data-action="room-confirm-off" ${disabled}>Turn off</button>
          </div>
        </div>
      </div>`
    : "";
  const hint = live
    ? note
    : "Live commit is off. Nothing will be sent.";
  return `
    <div class="room-fit">
      <header class="room-top">
        <button type="button" class="room" data-action="close-room">Bar</button>
        <div class="mode-banner is-${escapeHtml(bannerMode)}" role="status">${escapeHtml(bannerText)}</div>
        <div class="room-route">${escapeHtml(statusText)}</div>
        <button type="button" class="room-close" data-action="close-room">Close</button>
      </header>
      <div class="room-power">
        <button type="button" class="room-power-on" data-action="room-power-on" ${disabled}><b>TVs on</b><small>All 35</small></button>
        <button type="button" class="room-power-off" data-action="room-power-off" ${disabled}><b>TVs off</b><small>Asks first</small></button>
      </div>
      <section class="room-volume" aria-label="Volume for the selected TV">
        <div class="room-picked">
          <p class="room-kicker">Volume</p>
          <h2>TV ${Number(selectedTv)}</h2>
          <p>${escapeHtml(pickedMeta(selected))}</p>
        </div>
        <div class="room-vol">
          <button type="button" data-action="room-vol" data-value="down" aria-label="Volume down for the selected TV" ${disabled}>−</button>
          <button type="button" class="room-mute${selected.mute ? " is-on" : ""}" data-action="room-vol" data-value="mute" aria-label="Mute the selected TV" ${disabled}>${selected.mute ? "Muted" : "Mute"}</button>
          <button type="button" class="room-up" data-action="room-vol" data-value="up" aria-label="Volume up for the selected TV" ${disabled}>+</button>
        </div>
      </section>
      <p class="room-note" role="status">${escapeHtml(hint)}</p>
      <div class="room-grid" aria-label="Choose a TV">${tiles.join("")}</div>
      ${confirmHtml}
    </div>
  `;
}

export const ROOM_CSS = `
        .routing.room-open { position: relative; }
        .room-fit {
          display: grid;
          flex: 1 1 auto;
          gap: 8px;
          grid-template-rows: auto auto auto auto minmax(0, 1fr);
          min-height: 0;
          overflow: hidden;
          padding: 8px 12px 10px;
          position: relative;
        }
        .room-top {
          align-items: center;
          display: flex;
          gap: 10px;
          min-height: 40px;
        }
        .routing .room-top .room {
          background: transparent;
          border: 0;
          color: inherit;
          cursor: pointer;
          font: inherit;
          font-size: 20px;
          font-weight: 650;
          padding: 0;
        }
        .room-route {
          color: #c8c8c8;
          flex: 1;
          font-size: 14px;
          overflow: hidden;
          text-align: right;
          text-overflow: ellipsis;
          white-space: nowrap;
        }
        .room-close, .room-cancel, .room-danger, .room-power button, .room-vol button, .room-tv {
          font: inherit;
        }
        .room-close {
          background: #2a2a2a;
          border: 0;
          border-radius: 3px;
          color: #f3f3f3;
          cursor: pointer;
          font-weight: 700;
          min-height: 40px;
          padding: 0 14px;
        }
        .room-power { display: grid; gap: 8px; grid-template-columns: 1fr 1fr; }
        .room-power button {
          border: 0;
          border-radius: 3px;
          cursor: pointer;
          min-height: 48px;
          padding: 6px 12px;
          text-align: left;
        }
        .room-power button b { display: block; font-size: 17px; }
        .room-power button small { display: block; font-size: 12px; }
        .room-power-on { background: #0b5cab; color: #fff; }
        .room-power-on small { color: #d7e7f8; }
        .room-power-off {
          background: #2a2a2a;
          box-shadow: inset 0 0 0 1px #7f1d1d;
          color: #fecaca;
        }
        .room-power button:disabled, .room-vol button:disabled { cursor: default; opacity: 0.45; }
        .room-volume {
          align-items: stretch;
          display: grid;
          gap: 8px;
          grid-template-columns: 148px minmax(0, 1fr);
        }
        .room-picked {
          background: #1a1a1a;
          border-radius: 3px;
          display: flex;
          flex-direction: column;
          justify-content: center;
          min-height: 64px;
          padding: 6px 12px;
        }
        .room-kicker {
          color: #8d8d8d;
          font-size: 11px;
          font-weight: 700;
          letter-spacing: 0.12em;
          margin: 0;
          text-transform: uppercase;
        }
        .room-picked h2 { font-size: 26px; margin: 0; }
        .room-picked p { color: #d7e7f8; font-size: 13px; font-weight: 650; margin: 2px 0 0; }
        .room-vol { display: grid; gap: 8px; grid-template-columns: 1fr 1.2fr 1fr; }
        .room-vol button {
          background: #3a3a3a;
          border: 0;
          border-radius: 3px;
          color: #fff;
          cursor: pointer;
          font-size: 22px;
          font-weight: 700;
          min-height: 64px;
        }
        .room-vol .room-up { background: #0b5cab; }
        .room-vol .room-mute.is-on { background: #7f1d1d; }
        .room-note { color: #d7e7f8; font-size: 14px; font-weight: 650; margin: 0; min-height: 18px; }
        .room-grid {
          display: grid;
          gap: 8px;
          grid-template-columns: repeat(7, minmax(0, 1fr));
          grid-template-rows: repeat(5, minmax(44px, 1fr));
          min-height: 0;
        }
        .room-tv {
          align-items: center;
          background: #2a2a2a;
          border: 0;
          border-radius: 3px;
          color: #f3f3f3;
          cursor: pointer;
          display: flex;
          flex-direction: column;
          justify-content: center;
          min-height: 44px;
          min-width: 0;
          padding: 4px;
        }
        .room-tv b { font-size: 20px; line-height: 1; }
        .room-tv small { color: #d7e7f8; font-size: 12px; font-weight: 700; line-height: 1; min-height: 12px; }
        .room-tv.is-selected { background: #0b5cab; }
        .room-tv.is-muted:not(.is-selected) { box-shadow: inset 0 0 0 1px #fca5a5; }
        .room-confirm {
          align-items: center;
          background: rgba(0, 0, 0, 0.72);
          display: flex;
          inset: 0;
          justify-content: center;
          padding: 24px;
          position: absolute;
        }
        .room-confirm-card {
          background: #1a1a1a;
          border: 1px solid #333;
          border-radius: 8px;
          max-width: 480px;
          padding: 22px;
          width: min(480px, 100%);
        }
        .room-confirm-card h3 { font-size: 24px; margin: 0 0 8px; }
        .room-confirm-card p { color: #c8c8c8; margin: 0 0 16px; }
        .room-confirm-row { display: grid; gap: 10px; grid-template-columns: 1fr 1fr; }
        .room-cancel, .room-danger {
          border: 0;
          border-radius: 3px;
          cursor: pointer;
          font-size: 18px;
          font-weight: 700;
          min-height: 56px;
        }
        .room-cancel { background: #2a2a2a; color: #f3f3f3; }
        .room-danger { background: #b91c1c; color: #fff; }
`;
