#!/usr/bin/env python3
"""Pull live league scoreboards (ESPN public API) for Sports ↔ channel matching."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_OUT = ROOT / "config" / "sports_schedule.json"
WWW_OUT = (
    ROOT / "homeassistant" / "config" / "www" / "avaccess" / "sports_schedule.json"
)

# ESPN site API scoreboards (public, no key). Used as the schedule scraper source.
LEAGUES: dict[str, tuple[str, list[str]]] = {
    "mlb": (
        "mlb",
        [
            "https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard",
            "https://site.web.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard",
            "https://cdn.espn.com/core/mlb/scoreboard?xhr=1",
        ],
    ),
    "nfl": (
        "nfl",
        [
            "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard",
            "https://site.web.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard",
            "https://cdn.espn.com/core/nfl/scoreboard?xhr=1",
        ],
    ),
    "nba": (
        "nba",
        [
            "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard",
            "https://site.web.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard",
            "https://cdn.espn.com/core/nba/scoreboard?xhr=1",
        ],
    ),
    "nhl": (
        "nhl",
        [
            "https://site.api.espn.com/apis/site/v2/sports/hockey/nhl/scoreboard",
            "https://site.web.api.espn.com/apis/site/v2/sports/hockey/nhl/scoreboard",
            "https://cdn.espn.com/core/nhl/scoreboard?xhr=1",
        ],
    ),
    "wnba": (
        "wnba",
        [
            "https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/scoreboard",
            "https://site.web.api.espn.com/apis/site/v2/sports/basketball/wnba/scoreboard",
            "https://cdn.espn.com/core/wnba/scoreboard?xhr=1",
        ],
    ),
    "cfb": (
        "cfb",
        [
            "https://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard",
            "https://site.web.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard",
            "https://cdn.espn.com/core/college-football/scoreboard?xhr=1",
        ],
    ),
}

_UA_ROTATION = (
    "espn-android",
    "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (compatible; AVAccess/1.0; +https://github.com/integrid-int/avaccess-automator)",
)


def fetch_json(url: str, *, retries: int = 3) -> dict[str, Any]:
    """Fetch ESPN JSON with UA rotation and light retries."""
    last_exc: Exception | None = None
    for attempt in range(retries):
        ua = _UA_ROTATION[attempt % len(_UA_ROTATION)]
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": ua,
                "Accept": "application/json,text/plain,*/*",
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": "https://www.espn.com/",
                "Origin": "https://www.espn.com",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read().decode("utf-8")
            payload = json.loads(raw)
            # cdn.espn.com wraps content under page.content
            if isinstance(payload, dict) and "page" in payload and "events" not in payload:
                content = (payload.get("page") or {}).get("content") or {}
                scoreboard = content.get("scoreboard") or content
                if isinstance(scoreboard, dict) and scoreboard.get("events"):
                    return scoreboard
            return payload
        except (OSError, TimeoutError, urllib.error.URLError, json.JSONDecodeError) as exc:
            last_exc = exc
            time.sleep(0.4 * (attempt + 1))
    assert last_exc is not None
    raise last_exc


def _team_name(competitor: dict[str, Any]) -> str:
    team = competitor.get("team") or {}
    return str(
        team.get("displayName")
        or team.get("shortDisplayName")
        or team.get("name")
        or team.get("abbreviation")
        or ""
    ).strip()


def _broadcast_names(competition: dict[str, Any]) -> list[str]:
    """Collect TV / network labels from ESPN competition broadcast fields."""
    names: list[str] = []
    seen: set[str] = set()

    def add(label: str) -> None:
        text = str(label or "").strip()
        if not text:
            return
        key = text.lower()
        if key in seen:
            return
        seen.add(key)
        names.append(text)

    for broadcast in competition.get("broadcasts") or []:
        for name in broadcast.get("names") or []:
            add(str(name))
    for geo in competition.get("geoBroadcasts") or []:
        media = geo.get("media") or {}
        add(str(media.get("shortName") or ""))
        add(str(media.get("name") or ""))
        # Prefer TV over streaming for cable matching.
        btype = str(((geo.get("type") or {}).get("shortName") or "")).upper()
        if btype and btype not in {"TV", "STREAM"}:
            pass
    # Some payloads only expose competitions[].broadcast
    legacy = competition.get("broadcast")
    if isinstance(legacy, str):
        for part in legacy.split("/"):
            add(part.strip())
    elif isinstance(legacy, list):
        for part in legacy:
            add(str(part))
    return names


def parse_scoreboard(payload: dict[str, Any], sport_key: str) -> list[dict[str, Any]]:
    games: list[dict[str, Any]] = []
    for event in payload.get("events") or []:
        event_id = str(event.get("id") or "")
        name = str(event.get("name") or event.get("shortName") or "").strip()
        start = event.get("date")
        competition = (event.get("competitions") or [{}])[0]
        comps = competition.get("competitors") or []
        home = ""
        away = ""
        for comp in comps:
            if comp.get("homeAway") == "home":
                home = _team_name(comp)
            elif comp.get("homeAway") == "away":
                away = _team_name(comp)
        if not home and len(comps) >= 1:
            home = _team_name(comps[0])
        if not away and len(comps) >= 2:
            away = _team_name(comps[1])
        title = name or (f"{away} at {home}".strip() if away or home else "Game")
        broadcasts = _broadcast_names(competition)
        games.append(
            {
                "id": f"sched-{sport_key}-{event_id or title}",
                "sportKey": sport_key,
                "away": away,
                "home": home,
                "title": title,
                "start": start,
                "end": None,
                "status": str(
                    ((event.get("status") or {}).get("type") or {}).get("name") or ""
                ),
                "broadcasts": broadcasts,
            }
        )
    return games


def _with_dates(url: str, dates: list[str]) -> list[str]:
    """Return URL variants with ?dates=YYYYMMDD when dates provided."""
    if not dates:
        return [url]
    out: list[str] = []
    for day in dates:
        sep = "&" if "?" in url else "?"
        out.append(f"{url}{sep}dates={day}")
    return out


def pull_schedules(
    leagues: list[str] | None = None,
    *,
    dates: list[str] | None = None,
) -> dict[str, Any]:
    selected = leagues or list(LEAGUES.keys())
    games: list[dict[str, Any]] = []
    errors: list[str] = []
    seen_ids: set[str] = set()
    for key in selected:
        if key not in LEAGUES:
            errors.append(f"unknown league: {key}")
            continue
        sport_key, urls = LEAGUES[key]
        fetched = False
        last_err = ""
        for base in urls:
            for url in _with_dates(base, dates or []):
                try:
                    payload = fetch_json(url)
                    for game in parse_scoreboard(payload, sport_key):
                        gid = str(game["id"])
                        if gid in seen_ids:
                            continue
                        seen_ids.add(gid)
                        games.append(game)
                    fetched = True
                    break
                except (OSError, TimeoutError, json.JSONDecodeError, ValueError) as exc:
                    last_err = str(exc)
                    continue
            if fetched:
                break
        if not fetched:
            errors.append(f"{key}: {last_err or 'fetch failed'}")
    return {
        "generatedAt": dt.datetime.now(tz=dt.timezone.utc).isoformat(),
        "source": "espn-site-api",
        "games": games,
        "errors": errors,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--leagues",
        default="mlb,nfl,nba,nhl,wnba,cfb",
        help="Comma-separated league keys",
    )
    parser.add_argument(
        "--dates",
        default="",
        help="Optional comma-separated YYYYMMDD dates (ESPN dates= param)",
    )
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--www-out", type=Path, default=WWW_OUT)
    parser.add_argument(
        "--from-json",
        type=Path,
        help="Offline fixture JSON (skip network) for tests/demos",
    )
    args = parser.parse_args(argv)
    try:
        if args.from_json:
            payload = json.loads(args.from_json.read_text(encoding="utf-8"))
            if "generatedAt" not in payload:
                payload["generatedAt"] = dt.datetime.now(
                    tz=dt.timezone.utc
                ).isoformat()
        else:
            leagues = [p.strip() for p in args.leagues.split(",") if p.strip()]
            dates = [p.strip() for p in args.dates.split(",") if p.strip()]
            payload = pull_schedules(leagues, dates=dates or None)
        for path in (args.out, args.www_out):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
            print(path)
        print(f"{len(payload.get('games') or [])} games")
        if payload.get("errors"):
            print("errors:", "; ".join(payload["errors"]), file=sys.stderr)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"pull_sports_schedule failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
