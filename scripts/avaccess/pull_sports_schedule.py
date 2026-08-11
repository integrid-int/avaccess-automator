#!/usr/bin/env python3
"""Pull live league scoreboards (ESPN public API) for Sports ↔ EPG matching."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
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
LEAGUES: dict[str, tuple[str, str]] = {
    "mlb": ("mlb", "https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard"),
    "nfl": ("nfl", "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"),
    "nba": ("nba", "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"),
    "nhl": ("nhl", "https://site.api.espn.com/apis/site/v2/sports/hockey/nhl/scoreboard"),
    "wnba": (
        "wnba",
        "https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/scoreboard",
    ),
    "cfb": (
        "cfb",
        "https://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard",
    ),
}


def fetch_json(url: str) -> dict[str, Any]:
    # ESPN's edge often 403s generic bots; the android UA is accepted.
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "espn-android",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _team_name(competitor: dict[str, Any]) -> str:
    team = competitor.get("team") or {}
    return str(
        team.get("displayName")
        or team.get("shortDisplayName")
        or team.get("name")
        or team.get("abbreviation")
        or ""
    ).strip()


def parse_scoreboard(payload: dict[str, Any], sport_key: str) -> list[dict[str, Any]]:
    games: list[dict[str, Any]] = []
    for event in payload.get("events") or []:
        event_id = str(event.get("id") or "")
        name = str(event.get("name") or event.get("shortName") or "").strip()
        start = event.get("date")
        comps = (
            ((event.get("competitions") or [{}])[0]).get("competitors") or []
        )
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
            }
        )
    return games


def pull_schedules(leagues: list[str] | None = None) -> dict[str, Any]:
    selected = leagues or list(LEAGUES.keys())
    games: list[dict[str, Any]] = []
    errors: list[str] = []
    for key in selected:
        if key not in LEAGUES:
            errors.append(f"unknown league: {key}")
            continue
        sport_key, url = LEAGUES[key]
        try:
            payload = fetch_json(url)
            games.extend(parse_scoreboard(payload, sport_key))
        except (OSError, TimeoutError, json.JSONDecodeError, ValueError) as exc:
            errors.append(f"{key}: {exc}")
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
            payload = pull_schedules(leagues)
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
