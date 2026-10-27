import test from "node:test";
import assert from "node:assert/strict";
import { makePanel, scriptCalls } from "./panel-harness.js";

test("Bar opens the room screen and volume calls CEC for that TV", async () => {
  const { panel, calls } = makePanel({
    liveState: "on",
    callService: async () => ({
      response: { returncode: 0, stdout: '{"ok":true,"accepted":1,"results":[{"id":"RX-04","ok":true}]}' },
    }),
  });
  assert.equal(panel._state.liveCommit, true);
  panel._setState({ roomOpen: true, roomTv: 4 });
  assert.equal(panel.innerHTML.match(/data-action="room-tv"/g).length, 35);
  assert.match(panel.innerHTML, /class="room-fit"/);
  await panel._sendCec("up");
  const scripts = scriptCalls(calls);
  assert.equal(scripts.at(-1)[1], "avaccess_cec");
  assert.deepEqual(scripts.at(-1)[2], { action: "volume-up", tv: "4" });
  assert.match(panel.innerHTML, /\+1 this session/);
});

test("power stays off the wire while Live commit is off", async () => {
  const { panel, calls } = makePanel({ liveState: "off" });
  panel._setState({ roomOpen: true });
  await panel._sendCec("power-on");
  assert.equal(scriptCalls(calls).length, 0);
  assert.match(panel.innerHTML, /Live commit is off/);
});
