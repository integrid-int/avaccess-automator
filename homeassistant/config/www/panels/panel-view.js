export const PRACTICE_BANNER = "PRACTICE – TVs will not change";
export const LIVE_BANNER = "LIVE – TVs WILL change";
const SCROLL_KEY_SELECTOR = "[data-scroll-key]";

export function commitModeBanner({ liveCommit = false, inventoryLiveReady = false } = {}) {
  // Take only goes live when both are true (see _sendPlan), so the banner follows the same rule.
  if (liveCommit && inventoryLiveReady) return { mode: "live", text: LIVE_BANNER };
  return { mode: "practice", text: PRACTICE_BANNER };
}

export function teamInitials(name) {
  const words = String(name ?? "")
    .split(/[\s-]+/)
    .map((word) => word.replace(/[^A-Za-z0-9]/g, ""))
    .filter(Boolean);
  if (!words.length) return "?";
  if (words.length === 1) {
    const [word] = words;
    if (word.length <= 4 && word === word.toUpperCase()) return word;
    return word.slice(0, 3).toUpperCase();
  }
  return words
    .slice(0, 3)
    .map((word) => word[0])
    .join("")
    .toUpperCase();
}

export function captureScrollPositions(root) {
  const positions = new Map();
  for (const element of root?.querySelectorAll?.(SCROLL_KEY_SELECTOR) ?? []) {
    const key = element.getAttribute("data-scroll-key");
    if (!key || (!element.scrollTop && !element.scrollLeft)) continue;
    positions.set(key, { top: element.scrollTop, left: element.scrollLeft });
  }
  return positions;
}

export function restoreScrollPositions(root, positions) {
  if (!root?.querySelectorAll || !positions?.size) return;
  for (const element of root.querySelectorAll(SCROLL_KEY_SELECTOR)) {
    const saved = positions.get(element.getAttribute("data-scroll-key"));
    if (!saved) continue;
    element.scrollTop = saved.top;
    element.scrollLeft = saved.left;
  }
}
