import json
import os
from datetime import datetime

import pytz
import requests

YEARS = [2026, 2025, 2024, 2023, 2022, 2021, 2020, 2019, 2018, 2017, 2016, 2015]
PLAYERS = [
    {
        "name": "Michael Busch",
        "id": 683737,
        "mlb_id": 683737,
        "slug": "michael-busch",
        "output": "michael_busch.json"
    },
    {
        "name": "Pete Crow-Armstrong",
        "id": 691718,
        "mlb_id": 691718,
        "slug": "pete-crow-armstrong",
        "output": "pete_crow_armstrong.json"
    },
    {
        "name": "Alex Bregman",
        "id": 608324,
        "mlb_id": 608324,
        "slug": "alex-bregman",
        "output": "alex_bregman.json"
    },
    {
        "name": "Ian Happ",
        "id": 664023,
        "mlb_id": 664023,
        "slug": "ian-happ",
        "output": "ian_happ.json"
    },
    {
        "name": "Carson Kelly",
        "id": 608348,
        "mlb_id": 608348,
        "slug": "carson-kelly",
        "output": "carson_kelly.json"
    }
]
BASE_URL = "https://statsapi.mlb.com/api/v1/people/{}/stats?stats=gameLog&group=hitting&season={}"
TEAMS_URL = "https://statsapi.mlb.com/api/v1/teams?sportId=1"
BASE_DIR = '/var/data'
OUTPUT_DIR = os.path.join(BASE_DIR, 'mlb', 'cubs')

TEAM_ABBREVIATIONS = None
SCHEDULE_URL = "https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/teams/chc/schedule"
LOCAL_TZ = pytz.timezone("America/Chicago")


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
    response = requests.get(BASE_URL.format(player["mlb_id"], year), timeout=30)
    response.raise_for_status()
    stats = response.json().get("stats", [])
    if not stats:
        return []
    team_abbreviations = get_team_abbreviations()
    splits = stats[0].get("splits", [])
    return [build_game_entry(split, team_abbreviations) for split in reversed(splits)]


def get_cubs_games_info():
    response = requests.get(SCHEDULE_URL, timeout=30)
    response.raise_for_status()
    data = response.json()
    now_local = datetime.now(LOCAL_TZ)
    current_game = None
    next_game_after_now = None

    for event in data.get('events', []):
        game_time_utc = datetime.fromisoformat(event['date'].replace("Z", "+00:00"))
        game_time_local = game_time_utc.astimezone(LOCAL_TZ)
        competitors = event['competitions'][0]['competitors']
        cubs = None
        opponent = None

        for team in competitors:
            if team['team']['abbreviation'] == 'CHC':
                cubs = team
            else:
                opponent = team

        if cubs and opponent:
            home_away = 'Home' if cubs['homeAway'] == 'home' else 'Away'
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
    current_game, next_game = get_cubs_games_info()
    for player in PLAYERS:
        all_data = []
        for year in YEARS:
            all_data.append({
                "year": year,
                "games": fetch_game_log(player, year)
            })
        output_file = os.path.join(OUTPUT_DIR, player["output"])
        with open(output_file, "w", encoding="utf-8") as file_handle:
            json.dump({
                "player_logs": all_data,
                "current_game": current_game,
                "next_game": next_game
            }, file_handle, indent=2)
        print(f"Saved {sum(len(year['games']) for year in all_data)} games for {player['name']} to {output_file}")


if __name__ == "__main__":
    main()