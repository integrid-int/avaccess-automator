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

function logoUrl(abbrev, league = "nfl") {
  return `https://a.espncdn.com/i/teamlogos/${league}/500/${abbrev}.png`;
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

export const SPORTS = [
  {
    id: "nfl",
    title: "NFL",
    chipTitle: "NFL",
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
    chipTitle: "CFB",
    icon: "🎓",
    games: [
      game("cfb-1", "Georgia", "uga", "Alabama", "ala", "ABC", "3:30 PM", "ncaa"),
      game("cfb-2", "Ohio State", "osu", "Michigan", "mich", "FOX", "12:00 PM", "ncaa"),
      game("cfb-3", "Texas", "tex", "Oklahoma", "okla", "ESPN", "7:30 PM", "ncaa"),
      game("cfb-4", "USC", "usc", "Oregon", "ore", "NBC", "8:00 PM", "ncaa"),
    ],
  },
  {
    id: "nba",
    title: "NBA",
    chipTitle: "NBA",
    icon: "🏀",
    games: [
      game("nba-1", "Lakers", "lal", "Celtics", "bos", "TNT", "7:30 PM", "nba"),
      game("nba-2", "Warriors", "gs", "Nuggets", "den", "ESPN", "10:00 PM", "nba"),
      game("nba-3", "Knicks", "ny", "Heat", "mia", "ABC", "3:00 PM", "nba"),
      game("nba-4", "Suns", "phx", "Mavericks", "dal", "ESPN2", "9:00 PM", "nba"),
    ],
  },
  {
    id: "nhl",
    title: "NHL",
    chipTitle: "NHL",
    icon: "🏒",
    games: [
      game("nhl-1", "Bruins", "bos", "Maple Leafs", "tor", "TNT", "7:00 PM", "nhl"),
      game("nhl-2", "Rangers", "nyr", "Islanders", "nyi", "MSG", "7:30 PM", "nhl"),
      game("nhl-3", "Avalanche", "col", "Stars", "dal", "ESPN", "8:00 PM", "nhl"),
      game("nhl-4", "Oilers", "edm", "Canucks", "van", "ESPN+", "10:00 PM", "nhl"),
    ],
  },
  {
    id: "mlb",
    title: "MLB",
    chipTitle: "MLB",
    icon: "⚾",
    games: [
      game("mlb-1", "Yankees", "nyy", "Red Sox", "bos", "YES", "7:05 PM", "mlb"),
      game("mlb-2", "Dodgers", "lad", "Giants", "sf", "ESPN", "10:10 PM", "mlb"),
      game("mlb-3", "Braves", "atl", "Mets", "nym", "SNY", "7:20 PM", "mlb"),
      game("mlb-4", "Cubs", "chc", "Cardinals", "stl", "FS1", "2:15 PM", "mlb"),
    ],
  },
  {
    id: "wnba",
    title: "WNBA",
    chipTitle: "WNBA",
    icon: "🏀",
    games: [
      game("wnba-1", "Aces", "lv", "Liberty", "ny", "ESPN2", "8:00 PM", "wnba"),
      game("wnba-2", "Storm", "sea", "Lynx", "min", "NBA TV", "7:00 PM", "wnba"),
      game("wnba-3", "Sun", "conn", "Fever", "ind", "ESPN", "1:00 PM", "wnba"),
      game("wnba-4", "Wings", "dal", "Mercury", "phx", "Amazon", "9:00 PM", "wnba"),
    ],
  },
];

export const GUIDE_CHANNELS = [
  { id: "ch-fox", number: "4", name: "WGHP FOX", category: "Local" },
  { id: "ch-cbs", number: "2", name: "WFMY CBS", category: "Local" },
  { id: "ch-nbc", number: "12", name: "WXII NBC", category: "Local" },
  { id: "ch-abc", number: "45", name: "WXLV ABC", category: "Local" },
  { id: "ch-espn", number: "206", name: "ESPN", category: "Sports" },
  { id: "ch-espn2", number: "207", name: "ESPN2", category: "Sports" },
  { id: "ch-fs1", number: "400", name: "FS1", category: "Sports" },
  { id: "ch-tnt", number: "245", name: "TNT", category: "Sports" },
  { id: "ch-nfl-a1", number: "705", name: "NFL Sunday Ticket 1", category: "Sports" },
];

export function filterGuideChannels(channels, query) {
  const q = String(query || "").trim().toLowerCase();
  if (!q) return channels;
  return channels.filter(
    (c) => c.number.includes(q) || c.name.toLowerCase().includes(q) || c.category.toLowerCase().includes(q)
  );
}
