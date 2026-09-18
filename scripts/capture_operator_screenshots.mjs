#!/usr/bin/env node
/**
 * Capture operator screenshots from staging Home Assistant.
 *
 * Requires a running HA at http://127.0.0.1:8123 and /tmp/hassTokens.json
 * (frontend access + refresh token). Launch with system Chrome:
 *
 *   node scripts/capture_operator_screenshots.mjs
 */
import fs from "node:fs";
import path from "node:path";
import puppeteer from "puppeteer-core";

const BASE = process.env.HA_BASE_URL || "http://127.0.0.1:8123";
const OUT = process.env.SHOT_DIR || path.resolve(path.dirname(new URL(import.meta.url).pathname), "../docs/images/operations");
const ART = process.env.ART_DIR || "/opt/cursor/artifacts/screenshots";
const TOKENS_PATH = process.env.HASS_TOKENS || "/tmp/hassTokens.json";
const CHROME =
  process.env.CHROME_PATH ||
  ["/usr/bin/google-chrome-stable", "/usr/bin/google-chrome", "/usr/local/bin/google-chrome"].find((p) =>
    fs.existsSync(p)
  );

fs.mkdirSync(OUT, { recursive: true });
fs.mkdirSync(ART, { recursive: true });

const tokens = JSON.parse(fs.readFileSync(TOKENS_PATH, "utf8"));

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

async function waitForText(page, needle, timeout = 25000) {
  const start = Date.now();
  while (Date.now() - start < timeout) {
    const text = await deepText(page);
    if (text.includes(needle)) return text;
    await sleep(250);
  }
  throw new Error(`timeout waiting for text: ${needle}`);
}

async function deepText(page) {
  return page.evaluate(() => {
    const bits = [];
    const visit = (root) => {
      if (!root) return;
      try {
        if (root.innerText) bits.push(root.innerText);
        else if (root.textContent) bits.push(root.textContent);
      } catch {
        /* ignore closed shadows */
      }
      const nodes = root.querySelectorAll ? root.querySelectorAll("*") : [];
      for (const el of nodes) {
        if (el.shadowRoot) visit(el.shadowRoot);
      }
    };
    visit(document);
    return bits.join("\n");
  });
}

async function dismissOverlays(page) {
  await page.evaluate(() => {
    const hosts = [document];
    const seen = new Set();
    const visit = (root) => {
      if (!root || seen.has(root)) return;
      seen.add(root);
      for (const el of root.querySelectorAll?.("*") || []) {
        const tag = (el.tagName || "").toLowerCase();
        if (tag.includes("toast") || tag.includes("notification") || tag === "ha-dialog") {
          el.remove();
        }
        if (el.shadowRoot) visit(el.shadowRoot);
      }
    };
    visit(document);
  });
}

async function findScrollerHandle(page) {
  return page.evaluateHandle(() => {
    const seen = new Set();
    const candidates = [];
    const walk = (node, depth) => {
      if (!node || seen.has(node) || depth > 24) return;
      seen.add(node);
      if (node.nodeType !== 1) return;
      const style = node instanceof Element ? getComputedStyle(node) : null;
      if (style) {
        const oy = style.overflowY;
        if ((oy === "auto" || oy === "scroll" || oy === "overlay") && node.scrollHeight > node.clientHeight + 30) {
          candidates.push(node);
        }
      }
      if (node.shadowRoot) walk(node.shadowRoot, depth + 1);
      for (const child of node.children || []) walk(child, depth + 1);
    };
    walk(document.documentElement, 0);
    candidates.sort((a, b) => b.scrollHeight - a.scrollHeight - (a.scrollHeight - a.clientHeight));
    return candidates[0] || document.scrollingElement || document.documentElement;
  });
}

async function scrollToTop(page) {
  const handle = await findScrollerHandle(page);
  await handle.evaluate((el) => {
    el.scrollTop = 0;
    window.scrollTo(0, 0);
  });
  await sleep(250);
}

async function scrollBy(page, amount) {
  const handle = await findScrollerHandle(page);
  await handle.evaluate((el, y) => {
    el.scrollTop = Math.min(el.scrollHeight, el.scrollTop + y);
  }, amount);
  await sleep(350);
}

async function scrollUntilText(page, needle, step = 420, max = 12) {
  for (let i = 0; i < max; i += 1) {
    const found = await page.evaluate((text) => {
      const bits = [];
      const visit = (root) => {
        if (!root) return;
        try {
          if (root.innerText) bits.push(root.innerText);
        } catch {}
        const nodes = root.querySelectorAll ? root.querySelectorAll("*") : [];
        for (const el of nodes) if (el.shadowRoot) visit(el.shadowRoot);
      };
      visit(document);
      return bits.join("\n").includes(text);
    }, needle);
    if (found) {
      await page.evaluate((text) => {
        const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
        while (walker.nextNode()) {
          if (walker.currentNode.textContent.includes(text)) {
            walker.currentNode.parentElement?.scrollIntoView({ block: "center" });
            return;
          }
        }
      }, needle);
      await sleep(250);
      return true;
    }
    await scrollBy(page, step);
  }
  return false;
}

async function saveShot(page, name) {
  await dismissOverlays(page);
  await sleep(200);
  const dest = path.join(OUT, name);
  const art = path.join(ART, name);
  await page.screenshot({ path: dest, type: "png" });
  fs.copyFileSync(dest, art);
  const stat = fs.statSync(dest);
  console.log("wrote", dest, stat.size);
}

async function gotoReady(page, url, hint) {
  await page.goto(url, { waitUntil: "networkidle2", timeout: 60000 });
  await sleep(1500);
  await dismissOverlays(page);
  if (hint) await waitForText(page, hint, 30000);
  await sleep(400);
}

async function clickText(page, text) {
  const clicked = await page.evaluate((needle) => {
    const matches = [];
    const visit = (root) => {
      for (const el of root.querySelectorAll("*")) {
        const t = `${el.innerText || ""} ${el.textContent || ""}`.replace(/\s+/g, " ").trim();
        const tag = (el.tagName || "").toLowerCase();
        const clickable =
          tag === "button" ||
          tag === "a" ||
          el.getAttribute("role") === "button" ||
          tag.includes("button") ||
          tag.includes("list-item") ||
          el.hasAttribute("data-action");
        if (clickable && t.includes(needle)) matches.push(el);
        if (el.shadowRoot) visit(el.shadowRoot);
      }
    };
    visit(document);
    if (!matches.length) return false;
    matches[0].click();
    return true;
  }, text);
  if (!clicked) throw new Error(`clickText failed: ${text}`);
  await sleep(800);
}

async function clickSelectorDeep(page, selector) {
  const clicked = await page.evaluate((sel) => {
    const visit = (root) => {
      const hit = root.querySelector(sel);
      if (hit) {
        hit.click();
        return true;
      }
      for (const el of root.querySelectorAll("*")) {
        if (el.shadowRoot && visit(el.shadowRoot)) return true;
      }
      return false;
    };
    return visit(document);
  }, selector);
  if (!clicked) throw new Error(`clickSelectorDeep failed: ${selector}`);
  await sleep(700);
}

const browser = await puppeteer.launch({
  executablePath: CHROME,
  headless: "new",
  args: [
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--disable-gpu",
    "--window-size=1440,900",
  ],
});

try {
  const page = await browser.newPage();
  page.setDefaultTimeout(40000);
  await page.setViewport({ width: 1440, height: 900, deviceScaleFactor: 2 });

  await page.evaluateOnNewDocument((t) => {
    localStorage.setItem("hassTokens", JSON.stringify(t));
  }, tokens);
  await page.goto(`${BASE}/avaccess-matrix/av-control`, { waitUntil: "networkidle2", timeout: 60000 });
  await sleep(2000);

  if (await page.$("ha-authorize")) {
    throw new Error("Still on login after token inject");
  }
  await waitForText(page, "FOX Local");
  await dismissOverlays(page);

  await saveShot(page, "01-control-overview.png");

  await scrollUntilText(page, "Route Program");
  await saveShot(page, "01b-control-route.png");

  await page.setViewport({ width: 768, height: 1024, deviceScaleFactor: 2 });
  await gotoReady(page, `${BASE}/avaccess-matrix/av-control`, "FOX Local");
  await saveShot(page, "02-control-ipad.png");
  await scrollUntilText(page, "Route Program");
  await saveShot(page, "03-control-ipad-route.png");

  await page.setViewport({ width: 1440, height: 900, deviceScaleFactor: 2 });
  await gotoReady(page, `${BASE}/avaccess-matrix/nfl`, "NFL");
  await saveShot(page, "04-nfl.png");

  await gotoReady(page, `${BASE}/avaccess-matrix/cfb`, "College Football");
  await saveShot(page, "05-college-football.png");

  await gotoReady(page, `${BASE}/avaccess-matrix/hoops`, "Basketball");
  await saveShot(page, "06-basketball.png");

  await gotoReady(page, `${BASE}/logbook`, "Activity");
  await sleep(1200);
  await saveShot(page, "07-activity-logbook.png");

  await page.setViewport({ width: 768, height: 1024, deviceScaleFactor: 2 });
  await gotoReady(page, `${BASE}/panel-health`, "Sports Routing");
  await waitForText(page, "NFL");
  await saveShot(page, "08-sports-routing-nfl.png");

  try {
    await clickSelectorDeep(page, '[data-action="open-guide"]');
  } catch {
    await clickText(page, "Guide");
  }
  await waitForText(page, "DirecTV");
  await saveShot(page, "09-sports-routing-guide.png");

  try {
    await clickSelectorDeep(page, '[data-action="open-sport"][data-value="nfl"], [data-action="open-sport"]');
  } catch {
    await clickText(page, "NFL");
  }
  await sleep(600);
  try {
    await clickSelectorDeep(page, '[data-action="select-game"]');
  } catch {
    /* destination may already be open */
  }
  await sleep(800);
  const destReady = await page.evaluate(
    () => document.body.innerText.includes("Preset") || document.body.innerText.includes("Pick TVs")
  );
  if (destReady) {
    await saveShot(page, "10-sports-routing-destination.png");
  } else {
    await saveShot(page, "10-sports-routing-destination.png");
  }

  await page.setViewport({ width: 1440, height: 900, deviceScaleFactor: 2 });
  await gotoReady(page, `${BASE}/avaccess-matrix/av-control`, "FOX Local");
  await saveShot(page, "00-sidebar-matrix.png");
} finally {
  await browser.close();
}
