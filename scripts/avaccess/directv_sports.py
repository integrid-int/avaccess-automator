#!/usr/bin/env python3
"""Turn DirecTV sports-info JSON into sports-rail games with satellite majors.

The sports page loads one calendar day per request:

  GET https://www.directv.com/sports-info/games?zip=27403&days=2026-10-25

A week of games is that request repeated, then merged on game id. Scripted
HTTP is refused (HTTP 403) from many networks, including the Home Assistant
host. Do not send Cookie or XSRF headers from a saved browser session, and do
not schedule a fetch inside the HA container.

Run the pull on a PC that can open the sports page. It starts Chrome or Edge,
lets that browser hold the session, and asks the page for each day:

  python3 scripts/avaccess/directv_sports.py --pull --ahead 8 \\
    --out homeassistant/config/www/avaccess/sports_schedule.json

Point --out at the file Home Assistant serves as
/local/avaccess/sports_schedule.json. If a hidden window is refused, add
--headed. A saved DevTools body still works:

  python3 scripts/avaccess/directv_sports.py --file games.json \\
    --out homeassistant/config/www/avaccess/sports_schedule.json
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

GAMES_URL = "https://www.directv.com/sports-info/games"
MARKET_ZIP = "27403"
MARKET_TZ = ZoneInfo("America/New_York")
APP_MAJOR_MIN = 30000
# Greensboro in-market affiliates. Prefer these over the national simulcast.
LOCAL_MAJORS = (2, 8, 12, 45)
# National sports nets the commercial lineup actually tunes.
NATIONAL_MAJORS = (206, 209, 212, 215, 216, 218, 219, 245)

# league text_id -> rail id, title, chip, icon, ESPN logo folder
LEAGUES: dict[str, tuple[str, str, str, str, str]] = {
    "NFL": ("nfl", "NFL", "NFL", "🏈", "nfl"),
    "NBA": ("nba", "NBA", "NBA", "🏀", "nba"),
    "MLB": ("mlb", "MLB", "MLB", "⚾", "mlb"),
    "NHL": ("nhl", "NHL", "NHL", "🏒", "nhl"),
    "WNBA": ("wnba", "WNBA", "WNBA", "🏀", "wnba"),
}
LEAGUE_ORDER = ("nfl", "nba", "mlb", "nhl", "wnba")

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/155.0.0.0 Safari/537.36 Edg/155.0.0.0"
)
SPORTS_PAGE = "https://www.directv.com/sports-info/all/all"
_DAY = re.compile(r"^\d{4}-\d{2}-\d{2}$")
# DirecTV text_id_short values that do not match the ESPN logo filename.
ESPN_ABBR = {
    "sfo": "sf",
    "gnb": "gb",
    "oak": "lv",
    "tam": "tb",
    "nor": "no",
    "kan": "kc",
}

# Runs inside the sports page. The open page already has the session; this
# does not read a token from disk.
_PAGE_FETCH_JS = """
async ({ zip, days }) => {
  const meta = document.querySelector('meta[name="csrf-token"]');
  let token = meta && meta.content ? meta.content : "";
  if (!token) {
    const match = document.cookie.match(/(?:^|;\\s*)XSRF-TOKEN=([^;]+)/);
    token = match ? decodeURIComponent(match[1]) : "";
  }
  const headers = {
    Accept: "application/json",
    "X-Requested-With": "XMLHttpRequest",
  };
  if (token) {
    headers["X-CSRF-Token"] = token;
    headers["X-XSRF-Token"] = token;
  }
  const results = [];
  for (const day of days) {
    const url = "/sports-info/games?zip=" + encodeURIComponent(zip)
      + "&days=" + encodeURIComponent(day);
    const response = await fetch(url, { credentials: "include", headers });
    results.push({ day, status: response.status, body: await response.text() });
  }
  return results;
}
"""


class DirectvSportsError(RuntimeError):
    pass


def games_url(zip_code: str, day: str) -> str:
    """One calendar day, matching the request the sports page fires."""
    query = urllib.parse.urlencode({"zip": zip_code, "days": day})
    return f"{GAMES_URL}?{query}"


def window_days(count: int = 8, *, today: dt.date | None = None) -> list[str]:
    """Eastern calendar dates starting today. One games request per date."""
    if count < 1:
        raise DirectvSportsError("--ahead must be at least 1.")
    start = today or dt.datetime.now(MARKET_TZ).date()
    return [(start + dt.timedelta(days=offset)).isoformat() for offset in range(count)]


def require_days(days: list[str]) -> list[str]:
    cleaned: list[str] = []
    for day in days:
        text = str(day).strip()
        if not _DAY.match(text):
            raise DirectvSportsError(f"Not a calendar day: {day}")
        try:
            dt.date.fromisoformat(text)
        except ValueError as exc:
            raise DirectvSportsError(f"Not a calendar day: {day}") from exc
        cleaned.append(text)
    return cleaned


def browser_profile_dir() -> Path:
    """Persistent Chrome/Edge profile on this PC. Never a path in the repo."""
    override = os.environ.get("AVACCESS_DIRECTV_BROWSER_PROFILE", "").strip()
    if override:
        return Path(override)
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home())
        return Path(base) / "avaccess" / "directv-sports-browser"
    return Path.home() / ".cache" / "avaccess" / "directv-sports-browser"


def browser_channel_order(preferred: str | None = None) -> list[str | None]:
    choice = (preferred or "").strip().lower()
    if choice:
        return [choice]
    if sys.platform == "win32":
        return ["msedge", "chrome", None]
    return ["chrome", "msedge", None]


def fetch_games(zip_code: str, day: str, timeout: float = 25) -> dict[str, Any]:
    """GET one day. Raises DirectvSportsError on Akamai 403 or a non-JSON body."""
    request = urllib.request.Request(
        games_url(zip_code, day),
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json, */*",
            "Referer": "https://www.directv.com/sports-info/all/all",
            "X-Requested-With": "XMLHttpRequest",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read()
    except urllib.error.HTTPError as exc:
        if exc.code == 403:
            raise DirectvSportsError(
                "DirecTV refused this client (HTTP 403). "
                "Save the games response from the browser and pass --file."
            ) from exc
        raise DirectvSportsError(f"DirecTV games request failed (HTTP {exc.code}).") from exc
    except urllib.error.URLError as exc:
        raise DirectvSportsError(f"DirecTV games request failed: {exc.reason}") from exc
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise DirectvSportsError("DirecTV games response was not JSON.") from exc
    if not isinstance(payload, dict):
        raise DirectvSportsError("DirecTV games response was not a JSON object.")
    return payload


def payloads_from_page_results(results: Any) -> list[dict[str, Any]]:
    """Games payloads from the in-page fetch. One failure aborts the pull."""
    if not isinstance(results, list) or not results:
        raise DirectvSportsError("DirecTV browser pull returned no days.")
    payloads: list[dict[str, Any]] = []
    for item in results:
        if not isinstance(item, dict):
            raise DirectvSportsError("DirecTV browser pull returned an unexpected row.")
        day = item.get("day") or "?"
        status = item.get("status")
        body = item.get("body") if isinstance(item.get("body"), str) else ""
        lowered = body.lstrip().lower()
        if status == 403 or lowered.startswith("<!doctype html") or lowered.startswith("<html"):
            raise DirectvSportsError(
                f"DirecTV refused the browser pull (HTTP {status}) for {day}. "
                "Run --pull on the PC that can open the sports page, and add "
                "--headed if a hidden window is refused."
            )
        if status != 200:
            raise DirectvSportsError(f"DirecTV games request for {day} failed (HTTP {status}).")
        try:
            payload = json.loads(body)
        except json.JSONDecodeError as exc:
            raise DirectvSportsError(f"DirecTV games response for {day} was not JSON.") from exc
        if not isinstance(payload, dict) or not isinstance(payload.get("games"), list):
            raise DirectvSportsError(f"DirecTV games response for {day} had no games list.")
        payloads.append(payload)
    return payloads


def fetch_window_in_browser(
    zip_code: str,
    days: list[str],
    *,
    headless: bool = True,
    channel: str | None = None,
    timeout_s: float = 45,
) -> list[dict[str, Any]]:
    """Open the sports page and request each day from that page."""
    days = require_days(days)
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise DirectvSportsError(
            "Install Playwright on the PC that opens DirecTV: pip install playwright"
        ) from exc

    profile = browser_profile_dir()
    profile.mkdir(parents=True, exist_ok=True)
    timeout_ms = int(timeout_s * 1000)
    last_error: Exception | None = None
    with sync_playwright() as playwright:
        context = None
        for candidate in browser_channel_order(channel):
            try:
                options: dict[str, Any] = {
                    "user_data_dir": str(profile),
                    "headless": headless,
                    "viewport": {"width": 1280, "height": 800},
                }
                if candidate:
                    options["channel"] = candidate
                context = playwright.chromium.launch_persistent_context(**options)
                break
            except Exception as exc:  # noqa: BLE001 — try the next installed browser
                last_error = exc
        if context is None:
            raise DirectvSportsError(
                "Could not open Chrome or Edge for the DirecTV pull. "
                "Install one of them on this PC."
            ) from last_error
        try:
            page = context.pages[0] if context.pages else context.new_page()
            page.goto(SPORTS_PAGE, wait_until="domcontentloaded", timeout=timeout_ms)
            page.wait_for_timeout(1500)
            results = page.evaluate(_PAGE_FETCH_JS, {"zip": zip_code, "days": days})
        except DirectvSportsError:
            raise
        except Exception as exc:
            raise DirectvSportsError(f"DirecTV browser pull failed: {exc}") from exc
        finally:
            context.close()
    return payloads_from_page_results(results)


def load_payload(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("games"), list):
        raise DirectvSportsError(f"{path} is not a DirecTV games response.")
    return payload


def merge_payloads(payloads: list[dict[str, Any]]) -> dict[str, Any]:
    """Keep one row per game id, preferring the copy with more showings."""
    by_id: dict[Any, dict[str, Any]] = {}
    order: list[Any] = []
    for payload in payloads:
        for game in payload.get("games") or []:
            if not isinstance(game, dict):
                continue
            gid = game.get("id")
            key = gid if gid is not None else id(game)
            previous = by_id.get(key)
            if previous is None:
                order.append(key)
                by_id[key] = game
                continue
            if len(game.get("showings") or []) > len(previous.get("showings") or []):
                by_id[key] = game
    return {"games": [by_id[key] for key in order]}


def _major(channel: dict[str, Any]) -> int | None:
    raw = channel.get("number_major")
    if isinstance(raw, bool) or raw is None:
        return None
    if isinstance(raw, int):
        return raw
    text = str(raw).strip()
    if text.isdigit():
        return int(text)
    return None


def _virtual(channel: dict[str, Any]) -> bool:
    blob = " ".join(
        str(channel.get(key) or "")
        for key in ("title_pgws", "title_display", "title", "title_clu")
    ).casefold()
    return "virtual" in blob or "(virt" in blob


def is_tunable_showing(showing: dict[str, Any]) -> bool:
    """Satellite major the Greensboro commercial lineup can tune."""
    if not isinstance(showing, dict) or showing.get("is_sat") is False:
        return False
    channel = showing.get("channel")
    if not isinstance(channel, dict):
        return False
    if channel.get("is_sat") is False:
        return False
    if channel.get("nondtv") in (1, True, "1"):
        return False
    if channel.get("residential_only") is True:
        return False
    if channel.get("ppv") is True:
        return False
    major = _major(channel)
    if major is None or major <= 0 or major >= APP_MAJOR_MIN:
        return False
    display = str(channel.get("number_display") or "").strip()
    if display and not display.isdigit():
        return False
    if _virtual(channel):
        return False
    return True


def _rank(major: int) -> tuple[int, int]:
    if major in LOCAL_MAJORS:
        return (0, major)
    if major in NATIONAL_MAJORS:
        return (1, major)
    if 9500 <= major < 9700:
        return (2, major)
    if 760 <= major <= 799:
        return (3, major)
    return (4, major)


def _callsign(channel: dict[str, Any]) -> str:
    callsign = str(channel.get("callsign_display") or channel.get("callsign") or "").strip()
    title = str(channel.get("title_display") or "").strip()
    legal = "television" in title.casefold() or "(" in title
    if title and not legal and len(title) > len(callsign):
        return title
    return callsign or title


def tunable_showings(game: dict[str, Any]) -> list[dict[str, Any]]:
    chosen: list[dict[str, Any]] = []
    for showing in game.get("showings") or []:
        if not is_tunable_showing(showing):
            continue
        channel = showing["channel"]
        major = _major(channel)
        assert major is not None
        label = _callsign(channel)
        chosen.append(
            {
                "channelNumber": str(major),
                "channel": f"{major} {label}".strip(),
                "_rank": _rank(major),
            }
        )
    chosen.sort(key=lambda item: item["_rank"])
    for item in chosen:
        item.pop("_rank", None)
    # One row per major. Keep the first (best rank) label.
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for item in chosen:
        if item["channelNumber"] in seen:
            continue
        seen.add(item["channelNumber"])
        unique.append(item)
    return unique


def _team_name(team: Any) -> str:
    if not isinstance(team, dict):
        return "TBD"
    for key in ("display_name_short", "name", "display_name_full"):
        text = str(team.get(key) or "").strip()
        if text and text.casefold() != "tbd":
            return text
    return "TBD"


def _team_abbr(team: Any) -> str:
    if not isinstance(team, dict):
        return ""
    raw = str(team.get("text_id_short") or team.get("text_id") or "").strip().lower()
    abbr = "".join(ch for ch in raw if ch.isalnum())
    return ESPN_ABBR.get(abbr, abbr)


def _logo(abbr: str, folder: str) -> str:
    if not abbr:
        return ""
    return f"https://a.espncdn.com/i/teamlogos/{folder}/500/{abbr}.png"


def _tipoff(starts_at: Any) -> str:
    if not isinstance(starts_at, str) or not starts_at.strip():
        return ""
    text = starts_at.strip().replace("Z", "+00:00")
    try:
        moment = dt.datetime.fromisoformat(text)
    except ValueError:
        return ""
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=dt.timezone.utc)
    local = moment.astimezone(MARKET_TZ)
    hour = local.strftime("%I").lstrip("0") or "12"
    return f"{local.strftime('%a')} {hour}:{local.strftime('%M %p')}"


def _league_meta(game: dict[str, Any]) -> tuple[str, str, str, str, str] | None:
    league = game.get("league")
    text_id = ""
    if isinstance(league, dict):
        text_id = str(league.get("text_id") or "").strip()
    return LEAGUES.get(text_id)


def parse_schedule(
    payload: dict[str, Any],
    *,
    zip_code: str = MARKET_ZIP,
    generated_at: dt.datetime | None = None,
    days: list[str] | None = None,
) -> dict[str, Any]:
    """Sports-rail document. Drops betting fields and non-satellite showings."""
    buckets: dict[str, dict[str, Any]] = {}
    for game in payload.get("games") or []:
        if not isinstance(game, dict):
            continue
        meta = _league_meta(game)
        if meta is None:
            continue
        rail_id, title, chip, icon, logo_folder = meta
        showings = tunable_showings(game)
        primary = showings[0] if showings else None
        away_team = game.get("away_team")
        home_team = game.get("home_team")
        away_abbr = _team_abbr(away_team)
        home_abbr = _team_abbr(home_team)
        gid = game.get("id")
        buckets.setdefault(
            rail_id,
            {"id": rail_id, "title": title, "chipTitle": chip, "icon": icon, "games": []},
        )
        buckets[rail_id]["games"].append(
            {
                "id": f"{rail_id}-{gid}",
                "away": _team_name(away_team),
                "home": _team_name(home_team),
                "channel": primary["channel"] if primary else "No channel",
                "channelNumber": primary["channelNumber"] if primary else None,
                "alternates": showings[1:],
                "tipoff": _tipoff(game.get("starts_at")),
                "startsAt": game.get("starts_at") or "",
                "awayLogo": _logo(away_abbr, logo_folder),
                "homeLogo": _logo(home_abbr, logo_folder),
            }
        )
    sports = []
    for rail_id in LEAGUE_ORDER:
        sport = buckets.get(rail_id)
        if not sport:
            continue
        sport["games"].sort(key=lambda item: (item.get("startsAt") or "", item["id"]))
        sports.append(sport)
    moment = generated_at or dt.datetime.now(dt.timezone.utc)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=dt.timezone.utc)
    document: dict[str, Any] = {
        "generatedAt": moment.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "zip": zip_code,
        "source": "directv-sports-info",
        "sports": sports,
    }
    if days:
        document["days"] = list(days)
    return document


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the sports rail from DirecTV games JSON.")
    parser.add_argument("--zip", default=MARKET_ZIP, help="Lineup ZIP. Default 27403.")
    parser.add_argument("--days", nargs="*", default=[], help="YYYY-MM-DD values to fetch.")
    parser.add_argument(
        "--pull",
        action="store_true",
        help="Fetch a rolling window in Chrome or Edge on this PC.",
    )
    parser.add_argument(
        "--ahead",
        type=int,
        default=8,
        help="Days to pull starting today Eastern. Used with --pull. Default 8.",
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Show the browser window. Use when a hidden window is refused.",
    )
    parser.add_argument(
        "--browser",
        default="",
        help="chrome or msedge. Default tries the installed browser.",
    )
    parser.add_argument("--file", action="append", default=[], help="Saved games JSON. Repeatable.")
    parser.add_argument("--out", required=True, help="sports_schedule.json path.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])
    payloads: list[dict[str, Any]] = []
    pulled_days: list[str] = []
    try:
        if args.pull:
            pulled_days = require_days(args.days) if args.days else window_days(args.ahead)
            payloads.extend(
                fetch_window_in_browser(
                    args.zip,
                    pulled_days,
                    headless=not args.headed,
                    channel=args.browser or None,
                )
            )
        else:
            for day in require_days(args.days):
                payloads.append(fetch_games(args.zip, day))
    except DirectvSportsError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    for raw in args.file:
        try:
            payloads.append(load_payload(Path(raw)))
        except (OSError, json.JSONDecodeError, DirectvSportsError) as exc:
            print(str(exc), file=sys.stderr)
            return 1
    if not payloads:
        print("Pass --pull, --days YYYY-MM-DD, or --file games.json.", file=sys.stderr)
        return 1
    schedule = parse_schedule(
        merge_payloads(payloads),
        zip_code=args.zip,
        days=pulled_days or None,
    )
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(schedule, indent=2) + "\n", encoding="utf-8")
    games = sum(len(sport["games"]) for sport in schedule["sports"])
    print(f"wrote {out} ({games} games)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
