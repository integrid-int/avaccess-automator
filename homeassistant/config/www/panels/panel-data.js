import { GUIDE_CHANNELS as LINEUP_CHANNELS } from "./spectrum-lineup-data.js?v=18";

export const SPECTRUM_ZIP = "27403";
export const STORAGE_KEY = "avaccess-bartender-panel-v2";

export const TOKENS = {
  canvas: "#f4f6f8",
  stage: "#111827",
  surfaceBrowse: "#ffffff",
  surfaceStage: "#1f2937",
  accent: "#0e7490",
  accentMutedBrowse: "#ecfeff",
  accentMutedStage: "#a5f3fc",
  textPrimaryBrowse: "#111827",
  textPrimaryStage: "#ffffff",
  textMutedBrowse: "#6b7280",
  textMutedStage: "#9ca3af",
  radiusSm: "8px",
  radiusMd: "10px",
};

export function range(start, end) {
  return Array.from({ length: end - start + 1 }, (_, index) => start + index);
}

export const PRESETS = [
  {
    id: "1_all",
    mode: "preset_1",
    label: "Preset 1 — ALL",
    shortLabel: "ALL",
    description: "One program on ENC-01 → all 35 TVs",
    programCapacity: 1,
    stripeCount: null,
    tvs: range(1, 35),
  },
  {
    id: "2_four_programs",
    mode: "preset_2",
    label: "Preset 2 — 4 Programs",
    shortLabel: "4 Prog",
    description: "Pick up to 4 programs; striped across ENC-01..04",
    programCapacity: 4,
    stripeCount: 4,
    tvs: range(1, 35),
  },
  {
    id: "3_nine_programs",
    mode: "preset_3",
    label: "Preset 3 — 9 Programs",
    shortLabel: "9 Prog",
    description: "Pick up to 9 programs; striped across ENC-01..09",
    programCapacity: 9,
    stripeCount: 9,
    tvs: range(1, 35),
  },
];

/** Sports chips filter schedule/EPG games (no hard-coded seed matchups). */
export const SPORTS = [
  { id: "all", title: "All sports", chipTitle: "All", icon: "" },
  { id: "nfl", title: "NFL", chipTitle: "NFL", icon: "" },
  { id: "cfb", title: "College Football", chipTitle: "CFB", icon: "" },
  { id: "nba", title: "NBA", chipTitle: "NBA", icon: "" },
  { id: "nhl", title: "NHL", chipTitle: "NHL", icon: "" },
  { id: "mlb", title: "MLB", chipTitle: "MLB", icon: "" },
  { id: "wnba", title: "WNBA", chipTitle: "WNBA", icon: "" },
  { id: "other", title: "Other", chipTitle: "Other", icon: "" },
];

export const GUIDE_CHANNELS = LINEUP_CHANNELS;

export const GUIDE_EPG_STALE_MS = 6 * 60 * 60 * 1000;

export function isGuideEpgFresh(feed, nowMs = Date.now()) {
  if (!feed || !feed.generatedAt) return false;
  const generatedMs = Date.parse(feed.generatedAt);
  if (Number.isNaN(generatedMs)) return false;
  return nowMs - generatedMs <= GUIDE_EPG_STALE_MS;
}

export function mergeGuideWithEpg(channels, feed, nowMs = Date.now()) {
  if (!isGuideEpgFresh(feed, nowMs)) {
    return { channels, epgAvailable: false };
  }
  const epgChannels = feed.channels || {};
  return {
    epgAvailable: true,
    channels: channels.map((channel) => {
      const epg = epgChannels[channel.number];
      if (!epg) return channel;
      const merged = { ...channel };
      if (epg.now?.title != null) merged.nowTitle = epg.now.title;
      if (epg.next?.title != null) merged.nextTitle = epg.next.title;
      return merged;
    }),
  };
}

export function filterGuideChannels(channels, query) {
  const q = String(query || "").trim().toLowerCase();
  if (!q) return channels;
  return channels.filter((c) => {
    const nowTitle = String(c.nowTitle || "").toLowerCase();
    const nextTitle = String(c.nextTitle || "").toLowerCase();
    return (
      c.number.includes(q) ||
      c.name.toLowerCase().includes(q) ||
      c.category.toLowerCase().includes(q) ||
      nowTitle.includes(q) ||
      nextTitle.includes(q)
    );
  });
}

export function guideCategories(channels) {
  const seen = new Set();
  const cats = [];
  for (const channel of channels) {
    const cat = String(channel.category || "").trim();
    if (!cat || seen.has(cat)) continue;
    seen.add(cat);
    cats.push(cat);
  }
  return cats.sort((a, b) => a.localeCompare(b));
}

export function filterGuideByCategory(channels, category) {
  const cat = String(category || "").trim();
  if (!cat || cat.toLowerCase() === "all") return channels;
  return channels.filter((c) => c.category === cat);
}

function formatSportTime(iso) {
  if (!iso) return "";
  const ms = Date.parse(iso);
  if (Number.isNaN(ms)) return String(iso);
  try {
    return new Intl.DateTimeFormat("en-US", {
      timeZone: "America/New_York",
      hour: "numeric",
      minute: "2-digit",
    }).format(new Date(ms));
  } catch {
    return String(iso);
  }
}

function normalizeSportItem(item, bucket) {
  return {
    id: item.id,
    kind: "game",
    source: "epg",
    title: item.title,
    channel: item.channelName || item.channelNumber,
    channelNumber: String(item.channelNumber),
    channelName: item.channelName || "",
    tipoff: formatSportTime(bucket === "now" ? item.start : item.start),
    start: item.start,
    end: item.end,
    sportKey: item.sportKey || "other",
    bucket,
    away: item.title,
    home: "",
    awayLogo: "",
    homeLogo: "",
  };
}

function normalizeScheduleItem(item) {
  const channelNumber = item.channelNumber != null ? String(item.channelNumber) : "";
  const broadcasts = Array.isArray(item.broadcasts)
    ? item.broadcasts.map((b) => String(b)).filter(Boolean)
    : [];
  return {
    id: item.id,
    kind: "game",
    source: "schedule",
    title: item.title || `${item.away || ""} at ${item.home || ""}`.trim(),
    channel: item.channelName || channelNumber || "No channel match",
    channelNumber,
    channelName: item.channelName || "",
    tipoff: formatSportTime(item.start),
    start: item.start,
    end: item.end,
    sportKey: item.sportKey || "other",
    bucket: "schedule",
    matched: Boolean(item.matched && channelNumber),
    broadcasts,
    away: item.away || item.title || "",
    home: item.home || "",
    awayLogo: "",
    homeLogo: "",
  };
}

export function sportsFromEpg(feed, nowMs = Date.now()) {
  if (!isGuideEpgFresh(feed, nowMs) || !feed?.sports) {
    return { available: false, now: [], upcoming: [], schedule: [] };
  }
  const now = (feed.sports.now || []).map((item) => normalizeSportItem(item, "now"));
  const upcoming = (feed.sports.upcoming || []).map((item) =>
    normalizeSportItem(item, "upcoming")
  );
  const schedule = (feed.sports.schedule || []).map((item) => normalizeScheduleItem(item));
  return { available: true, now, upcoming, schedule };
}

export function filterSportsByTab(items, sportKey) {
  const key = String(sportKey || "all");
  if (!key || key === "all") return items;
  return items.filter((item) => item.sportKey === key);
}

/**
 * League chips (NFL/MLB/…) list ESPN schedule games matched to channels.
 * Generic Sports-category EPG dump is only used for Other, or as fallback
 * when the schedule feed is empty for that league.
 */
export function sportsItemsForTab(feed, sportKey, nowMs = Date.now()) {
  const { available, now, upcoming, schedule } = sportsFromEpg(feed, nowMs);
  const key = String(sportKey || "all");
  const sched = filterSportsByTab(schedule || [], key);

  if (key === "other") {
    const nowF = filterSportsByTab(now, "other");
    const upF = filterSportsByTab(upcoming, "other");
    return {
      available,
      schedule: [],
      now: nowF,
      upcoming: upF,
      items: [...nowF, ...upF],
    };
  }

  if (key !== "all") {
    if (sched.length) {
      return { available, schedule: sched, now: [], upcoming: [], items: sched };
    }
    // Fallback: classified EPG rows when ESPN schedule missing.
    const nowF = filterSportsByTab(now, key);
    const upF = filterSportsByTab(upcoming, key);
    return {
      available,
      schedule: [],
      now: nowF,
      upcoming: upF,
      items: [...nowF, ...upF],
    };
  }

  // All sports: schedule games first; fall back to EPG only if no schedule.
  if (sched.length) {
    return { available, schedule: sched, now: [], upcoming: [], items: sched };
  }
  return {
    available,
    schedule: [],
    now,
    upcoming,
    items: [...now, ...upcoming],
  };
}

export function allSportsItems(feed, nowMs = Date.now()) {
  const { available, items } = sportsItemsForTab(feed, "all", nowMs);
  return { available, items };
}
