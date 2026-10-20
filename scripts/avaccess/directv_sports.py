#!/usr/bin/env python3
"""Turn DirecTV sports-info JSON into sports-rail games with satellite majors.

The sports page loads one calendar day per request:

  GET https://www.directv.com/sports-info/games?zip=27403&days=2026-10-25

A week of games is that request repeated, then merged on game id. The URL has
no plan argument: zip 27403 returns every package. This is a commercial
account, so a channel is kept only when one of its packages is marked
commercial. Greensboro locals 2, 8, 12, and 45 stay even though DirecTV tags
them with the residential MySports package. Scripted HTTP is refused (HTTP
403) from many networks. Do not send Cookie or XSRF headers from a saved
browser session, and do not curl DirecTV from the HA container.

On Home Assistant OS, the Selenium Standalone add-on is the browser. A
morning shell command talks to it on port 4444:

  python3 avaccess/scripts/directv_sports.py --pull \\
    --selenium http://127.0.0.1:4444 --ahead 8 \\
    --out www/avaccess/sports_schedule.json

On a PC that can open the sports page, Chrome or Edge can do the same:

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

# ESPN logo folders. Other leagues have no matching CDN path.
ESPN_LOGO_FOLDER = {
    "nfl": "nfl",
    "nba": "nba",
    "mlb": "mlb",
    "nhl": "nhl",
    "wnba": "wnba",
}

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


def fetch_window_via_selenium(
    endpoint: str,
    zip_code: str,
    days: list[str],
    *,
    page_timeout_s: float = 20,
    script_timeout_s: float = 30,
) -> list[dict[str, Any]]:
    """Ask the Selenium Standalone add-on to open the sports page and pull each day.

    The add-on already runs Chromium on a virtual screen. This client only
    speaks WebDriver. It does not send DirecTV cookies.
    """
    days = require_days(list(days))
    base = endpoint.strip().rstrip("/")
    if not base:
        raise DirectvSportsError("Pass the Selenium add-on URL, for example http://127.0.0.1:4444.")
    session = _wd_new_session(base, timeout_s=page_timeout_s)
    try:
        _wd_call(
            base,
            "POST",
            f"/session/{session}/timeouts",
            {"script": int(script_timeout_s * 1000), "pageLoad": int(page_timeout_s * 1000), "implicit": 0},
            timeout_s=page_timeout_s,
        )
        _wd_call(
            base,
            "POST",
            f"/session/{session}/url",
            {"url": SPORTS_PAGE},
            timeout_s=page_timeout_s,
        )
        wrapper = (
            "const done = arguments[arguments.length - 1];"
            f"const run = {_PAGE_FETCH_JS};"
            "Promise.resolve(run(arguments[0])).then(done).catch((error) => done({error: String(error)}));"
        )
        result = _wd_call(
            base,
            "POST",
            f"/session/{session}/execute/async",
            {"script": wrapper, "args": [{"zip": zip_code, "days": days}]},
            timeout_s=script_timeout_s + 5,
        )
    finally:
        try:
            _wd_call(base, "DELETE", f"/session/{session}", timeout_s=10)
        except DirectvSportsError:
            pass
    if isinstance(result, dict) and result.get("error"):
        raise DirectvSportsError(f"DirecTV browser pull failed: {result['error']}")
    return payloads_from_page_results(result)


def _wd_new_session(base: str, *, timeout_s: float) -> str:
    try:
        value = _wd_call(
            base,
            "POST",
            "/session",
            {
                "capabilities": {
                    "alwaysMatch": {
                        "browserName": "chrome",
                        "pageLoadStrategy": "eager",
                    }
                }
            },
            timeout_s=timeout_s,
        )
    except DirectvSportsError as exc:
        if "Selenium" in str(exc):
            raise
        raise DirectvSportsError(
            "Cannot open a browser on the Selenium add-on. "
            "Start Selenium Standalone and confirm port 4444."
        ) from exc
    session = ""
    if isinstance(value, dict):
        session = str(value.get("sessionId") or "")
    if not session:
        raise DirectvSportsError("Selenium did not return a session.")
    return session


def _wd_call(
    base: str,
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
    *,
    timeout_s: float,
) -> Any:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(base + path, data=data, method=method)
    request.add_header("Accept", "application/json")
    if data is not None:
        request.add_header("Content-Type", "application/json; charset=utf-8")
    try:
        with urllib.request.urlopen(request, timeout=timeout_s) as response:
            raw = response.read()
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        message = _wd_error(raw) or f"Selenium request failed (HTTP {exc.code})."
        raise DirectvSportsError(message) from exc
    except urllib.error.URLError as exc:
        raise DirectvSportsError(
            "Cannot reach the Selenium add-on. Start Selenium Standalone and confirm port 4444."
        ) from exc
    if not raw:
        return None
    try:
        body = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise DirectvSportsError("Selenium returned a response that was not JSON.") from exc
    if not isinstance(body, dict):
        return body
    if "value" not in body:
        return body
    value = body["value"]
    if isinstance(value, dict) and value.get("error") and "sessionId" not in value:
        raise DirectvSportsError(str(value.get("message") or value["error"]))
    return value


def _wd_error(raw: bytes) -> str:
    try:
        body = json.loads(raw)
    except json.JSONDecodeError:
        return ""
    value = body.get("value") if isinstance(body, dict) else None
    if isinstance(value, dict):
        return str(value.get("message") or value.get("error") or "")
    return ""


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
    if not _on_commercial_plan(channel, major):
        return False
    return True


def _on_commercial_plan(channel: dict[str, Any], major: int) -> bool:
    """True when this commercial account can be sold the channel.

    The games response mixes residential and commercial packages. Residential
    tiers (Choice, Ultimate, Sports Pack, MySports) are not on this account.
    A package with commercial set is. Locals are the exception: the commercial
    headend carries them even when the only listed package is MySports.
    """
    if major in LOCAL_MAJORS:
        return True
    packages = channel.get("packages")
    if not isinstance(packages, list) or not packages:
        return True
    return any(
        isinstance(package, dict) and package.get("commercial") is True for package in packages
    )


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


def _slug(value: Any) -> str:
    return "".join(ch for ch in str(value or "").strip().lower() if ch.isalnum() or ch == "_")


def _shown(node: Any) -> bool:
    return isinstance(node, dict) and node.get("show") is not False


def _rank_value(node: dict[str, Any]) -> int:
    raw = node.get("rank")
    if isinstance(raw, bool) or raw is None:
        return 9999
    if isinstance(raw, int):
        return raw
    text = str(raw).strip()
    return int(text) if text.isdigit() else 9999


def _event_sides(game: dict[str, Any]) -> tuple[str, str]:
    """Team matchup, or the event title when DirecTV has no teams."""
    away = _team_name(game.get("away_team"))
    home = _team_name(game.get("home_team"))
    if away != "TBD" or home != "TBD":
        return away, home
    description = " ".join(str(game.get("description") or "").split())
    if description:
        return description, ""
    return away, home


def _category(game: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]] | None:
    """DirecTV sport category and league. Hidden rows are not picker choices."""
    sport = game.get("sport")
    league = game.get("league")
    if not _shown(sport) or not _shown(league):
        return None
    sport_id = _slug(sport.get("text_id"))
    league_id = _slug(league.get("text_id"))
    if not sport_id or not league_id:
        return None
    sport_title = str(sport.get("title") or sport_id).strip()
    league_title = str(league.get("title_short") or league.get("title") or league_id).strip()
    emoji = str(sport.get("emoji") or "").strip()
    return (
        {
            "id": sport_id,
            "title": sport_title,
            "chipTitle": sport_title,
            "icon": emoji,
            "_rank": _rank_value(sport),
        },
        {
            "id": league_id,
            "title": league_title,
            "chipTitle": league_title,
            "_rank": _rank_value(league),
        },
    )


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
        category = _category(game)
        if category is None:
            continue
        sport, league = category
        showings = tunable_showings(game)
        primary = showings[0] if showings else None
        away, home = _event_sides(game)
        logo_folder = ESPN_LOGO_FOLDER.get(league["id"], "")
        away_abbr = _team_abbr(game.get("away_team")) if home and logo_folder else ""
        home_abbr = _team_abbr(game.get("home_team")) if home and logo_folder else ""
        gid = game.get("id")
        bucket = buckets.setdefault(sport["id"], {**sport, "games": [], "_leagues": {}})
        bucket["_leagues"].setdefault(league["id"], league)
        bucket["games"].append(
            {
                "id": f"{league['id']}-{gid}",
                "leagueId": league["id"],
                "leagueTitle": league["title"],
                "away": away,
                "home": home,
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
    for sport in sorted(buckets.values(), key=lambda item: (item["_rank"], item["title"])):
        sport["games"].sort(key=lambda item: (item.get("startsAt") or "", item["id"]))
        leagues = sorted(sport.pop("_leagues").values(), key=lambda item: (item["_rank"], item["title"]))
        for league in leagues:
            league.pop("_rank", None)
        sport.pop("_rank", None)
        sport["leagues"] = leagues
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
    parser.add_argument(
        "--selenium",
        default="",
        help="Selenium Standalone URL, used with --pull. Example: http://127.0.0.1:4444.",
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
            if args.selenium:
                payloads.extend(fetch_window_via_selenium(args.selenium, args.zip, pulled_days))
            else:
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
    temporary = out.with_suffix(out.suffix + ".tmp")
    temporary.write_text(json.dumps(schedule, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, out)
    games = sum(len(sport["games"]) for sport in schedule["sports"])
    print(f"wrote {out} ({games} games)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
