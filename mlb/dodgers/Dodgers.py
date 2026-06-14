# Dodgers game log scraper
import json
import os
from datetime import datetime

import requests


YEARS = [2026, 2025, 2024,2023, 2022, 2021, 2020, 2019, 2018, 2017, 2016, 2015]
PLAYERS = [
    {"name": "Shohei Ohtani", "id": None, "mlb_id": 660271, "slug": "shohei-ohtani", "output": "shohei_ohtani.json"},
    {"name": "Andy Pages", "id": None, "mlb_id": 681624, "slug": "andy-pages", "output": "andy_pages.json"},
    {"name": "Freddie Freeman", "id": None, "mlb_id": 518692, "slug": "freddie-freeman", "output": "freddie_freeman.json"},
    {"name": "Mookie Betts", "id": None, "mlb_id": 605141, "slug": "mookie-betts", "output": "mookie_betts.json"},
    {"name": "Max Muncy", "id": None, "mlb_id": 571970, "slug": "max-muncy", "output": "max_muncy.json"},
    {"name": "Alex Call", "id": None, "mlb_id": 669743, "slug": "alex-call", "output": "alex_call.json"},
    {"name": "Ryan Ward", "id": None, "mlb_id": 669899, "slug": "ryan-ward", "output": "ryan_ward.json"}
]
BASE_URL = "https://statsapi.mlb.com/api/v1/people/{}/stats?stats=gameLog&group=hitting&season={}"
TEAMS_URL = "https://statsapi.mlb.com/api/v1/teams?sportId=1"
BASE_DIR = '/var/data'
OUTPUT_DIR = os.path.join(BASE_DIR, 'mlb', 'dodgers')

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
    if not player.get("mlb_id"):
        return []
    url = BASE_URL.format(player["mlb_id"], year)
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    stats = response.json().get("stats", [])
    if not stats:
        return []
    team_abbreviations = get_team_abbreviations()
    splits = stats[0].get("splits", [])
    return [build_game_entry(split, team_abbreviations) for split in reversed(splits)]


# --- Dodgers current/next game logic ---
import pytz
from datetime import datetime

SCHEDULE_URL = "https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/teams/lad/schedule"
LOCAL_TZ = pytz.timezone("America/Los_Angeles")

def get_dodgers_games_info():
    resp = requests.get(SCHEDULE_URL)
    resp.raise_for_status()
    data = resp.json()
    now_local = datetime.now(LOCAL_TZ)
    current_game = None
    next_game_after_now = None
    for event in data.get('events', []):
        game_time_str = event['date']  # ISO UTC string
        game_time_utc = datetime.fromisoformat(game_time_str.replace("Z", "+00:00"))
        game_time_local = game_time_utc.astimezone(LOCAL_TZ)
        competitors = event['competitions'][0]['competitors']
        dodgers = None
        opponent = None
        for team in competitors:
            if team['team']['abbreviation'] == 'LAD':
                dodgers = team
            else:
                opponent = team
        if dodgers and opponent:
            home_away = 'Home' if dodgers['homeAway'] == 'home' else 'Away'
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
        # Get Dodgers current and next game info
        current_game, next_game = get_dodgers_games_info()
        output_file = os.path.join(OUTPUT_DIR, player["output"])
        output_json = {
            "player_logs": all_data,
            "current_game": current_game,
            "next_game": next_game
        }
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(output_json, f, indent=2)
        print(f"Saved {sum(len(y['games']) for y in all_data)} games for {player['name']} to {output_file}")

if __name__ == "__main__":
    main()
