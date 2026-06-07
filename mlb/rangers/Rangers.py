# Texas Rangers game log scraper
import json
import os
from datetime import datetime

import pytz
import requests

YEARS = [2026, 2025, 2024, 2023, 2022, 2021, 2020, 2019, 2018, 2017, 2016, 2015]
PLAYERS = [
    {
        "name": "Corey Seager",
        "id": 608369,
        "mlb_id": 608369,
        "slug": "corey-seager",
        "output": "corey_seager.json"
    },
    {
        "name": "Josh Jung",
        "id": 673962,
        "mlb_id": 673962,
        "slug": "josh-jung",
        "output": "josh_jung.json"
    },
    {
        "name": "Brandon Nimmo",
        "id": 607043,
        "mlb_id": 607043,
        "slug": "brandon-nimmo",
        "output": "brandon_nimmo.json"
    },
    {
        "name": "Joc Pederson",
        "id": 592626,
        "mlb_id": 592626,
        "slug": "joc-pederson",
        "output": "joc_pederson.json"
    },
    {
        "name": "Kyle Higashioka",
        "id": 543309,
        "mlb_id": 543309,
        "slug": "kyle-higashioka",
        "output": "kyle_higashioka.json"
    },
    {
        "name": "Wyatt Langford",
        "id": 694671,
        "mlb_id": 694671,
        "slug": "wyatt-langford",
        "output": "wyatt_langford.json"
    }
]
BASE_URL = "https://statsapi.mlb.com/api/v1/people/{}/stats?stats=gameLog&group=hitting&season={}"
TEAMS_URL = "https://statsapi.mlb.com/api/v1/teams?sportId=1"
BASE_DIR = '/var/data'
OUTPUT_DIR = os.path.join(BASE_DIR, 'mlb', 'rangers')

TEAM_ABBREVIATIONS = None


def get_team_abbreviations():
    global TEAM_ABBREVIATIONS
    if TEAM_ABBREVIATIONS is None:
        response = requests.get(TEAMS_URL, timeout=30)
        response.raise_for_status()
        teams = response.json().get("teams", [])
        TEAM_ABBREVIATIONS = {team["id"]: team.get("abbreviation", "") for team in teams}
    return TEAM_ABBREVIATIONS


def format_game_date(date_str):
    game_date = datetime.strptime(date_str, "%Y-%m-%d")
    return game_date.strftime("%m/%d/%y")


def get_stat_value(stat_line, key, default="0"):
    value = stat_line.get(key, default)
    if value in (None, ""):
        return default
    return str(value)


def build_game_entry(split, team_abbreviations):
    stat_line = split.get("stat", {})
    opponent = split.get("opponent", {})
    opponent_abbr = team_abbreviations.get(opponent.get("id"), opponent.get("name", ""))
    opp_prefix = "vs" if split.get("isHome") else "@"
    return {
        "Date": format_game_date(split["date"]),
        "OPP": f"{opp_prefix}{opponent_abbr}",
        "H": get_stat_value(stat_line, "hits"),
        "HR": get_stat_value(stat_line, "homeRuns"),
        "RBI": get_stat_value(stat_line, "rbi"),
        "SB": get_stat_value(stat_line, "stolenBases"),
        "BB": get_stat_value(stat_line, "baseOnBalls")
    }


def fetch_game_log(player, year):
    url = BASE_URL.format(player["mlb_id"], year)
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    stats = response.json().get("stats", [])
    if not stats:
        return []
    team_abbreviations = get_team_abbreviations()
    splits = stats[0].get("splits", [])
    return [build_game_entry(split, team_abbreviations) for split in reversed(splits)]


# --- Rangers current/next game logic ---
SCHEDULE_URL = "https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/teams/tex/schedule"
LOCAL_TZ = pytz.timezone("America/New_York")


def get_rangers_games_info():
    resp = requests.get(SCHEDULE_URL, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    now_local = datetime.now(LOCAL_TZ)
    current_game = None
    next_game_after_now = None
    for event in data.get('events', []):
        game_time_str = event['date']
        game_time_utc = datetime.fromisoformat(game_time_str.replace("Z", "+00:00"))
        game_time_local = game_time_utc.astimezone(LOCAL_TZ)
        competitors = event['competitions'][0]['competitors']
        rangers = None
        opponent = None
        for team in competitors:
            if team['team']['abbreviation'] == 'TEX':
                rangers = team
            else:
                opponent = team
        if rangers and opponent:
            home_away = 'Home' if rangers['homeAway'] == 'home' else 'Away'
            game_info = {
                'date': game_time_local.strftime('%Y-%m-%d'),
                'time': game_time_local.strftime('%I:%M %p'),
                'opponent': opponent['team']['displayName'],
                'homeAway': home_away
            }
            if game_time_local.date() == now_local.date():
                current_game = game_info
            elif game_time_local > now_local and next_game_after_now is None:
                next_game_after_now = game_info
    return current_game, next_game_after_now


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    for player in PLAYERS:
        all_data = []
        for year in YEARS:
            year_data = fetch_game_log(player, year)
            all_data.append({
                "year": year,
                "games": year_data
            })
        current_game, next_game = get_rangers_games_info()
        output_file = os.path.join(OUTPUT_DIR, player["output"])
        output_json = {
            "player_logs": all_data,
            "current_game": current_game,
            "next_game": next_game
        }
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(output_json, f, indent=2)
        print(f"Saved {sum(len(y['games']) for y in all_data)} games for {player['name']} from {YEARS} to {output_file}")


if __name__ == "__main__":
    main()