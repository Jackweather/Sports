 # Jalen Brunson 2025 Game Log Scraper
import json
import os
from datetime import datetime

import pytz
import requests


YEARS = [2026, 2025, 2024,2023, 2022, 2021, 2020, 2019, 2018, 2017, 2016, 2015]
PLAYERS = [
    {
        "name": "Jalen Brunson",
        "espn_id": 3934672,
        "output": "jalen_brunson.json"
    },
    {
        "name": "Karl-Anthony Towns",
        "espn_id": 3136195,
        "output": "karl_anthony_towns.json"
    },
    {
        "name": "Mikal Bridges",
        "espn_id": 3147657,
        "output": "mikal_bridges.json"
    },
    {
        "name": "OG Anunoby",
        "espn_id": 3934719,
        "output": "og_anunoby.json"
    },
    {
        "name": "Josh Hart",
        "espn_id": 3062679,
        "output": "josh_hart.json"
    },
    {
        "name": "Landry Shamet",
        "espn_id": 3914044,
        "output": "landry_shamet.json"
    }
]
BASE_URL = "https://site.api.espn.com/apis/common/v3/sports/basketball/nba/athletes/{}/gamelog?season={}"
SCHEDULE_URL = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams/ny/schedule"
BASE_DIR = '/var/data'
OUTPUT_DIR = os.path.join(BASE_DIR, 'nba', 'knicks')
LOCAL_TZ = pytz.timezone("America/New_York")
STAT_KEYS = ["PTS", "REB", "AST", "STL"]


def format_game_date(date_str):
    game_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
    return game_date.astimezone(LOCAL_TZ).strftime("%m/%d/%y")


def get_stat_indices(labels):
    return {label: labels.index(label) for label in STAT_KEYS}


def build_game_entry(event, stats, stat_indices):
    opponent = event.get("opponent", {})
    return {
        "Date": format_game_date(event["gameDate"]),
        "OPP": f"{event.get('atVs', '')}{opponent.get('abbreviation', '')}",
        "PTS": stats[stat_indices["PTS"]],
        "REB": stats[stat_indices["REB"]],
        "AST": stats[stat_indices["AST"]],
        "STL": stats[stat_indices["STL"]]
    }


def fetch_game_log(player, year):
    response = requests.get(BASE_URL.format(player["espn_id"], year), timeout=30)
    response.raise_for_status()
    data = response.json()
    labels = data.get("labels", [])
    if not labels:
        return []

    stat_indices = get_stat_indices(labels)
    event_stats = {}
    for season_type in data.get("seasonTypes", []):
        for category in season_type.get("categories", []):
            for event in category.get("events", []):
                if event.get("eventId") and event.get("stats"):
                    event_stats[event["eventId"]] = event["stats"]

    events = sorted(
        data.get("events", {}).values(),
        key=lambda event: event.get("gameDate", ""),
        reverse=True
    )
    game_log = []
    for event in events:
        stats = event_stats.get(event.get("id"))
        if stats:
            game_log.append(build_game_entry(event, stats, stat_indices))
    return game_log


def get_knicks_games_info():
    response = requests.get(SCHEDULE_URL, timeout=30)
    response.raise_for_status()
    data = response.json()
    now_local = datetime.now(LOCAL_TZ)
    current_game = None
    next_game_after_now = None

    for event in data.get('events', []):
        game_time_utc = datetime.fromisoformat(event['date'].replace('Z', '+00:00'))
        game_time_local = game_time_utc.astimezone(LOCAL_TZ)
        competitors = event['competitions'][0]['competitors']
        knicks = None
        opponent = None
        for team in competitors:
            if team['team']['abbreviation'] == 'NY':
                knicks = team
            else:
                opponent = team
        if knicks and opponent:
            home_away = 'Home' if knicks['homeAway'] == 'home' else 'Away'
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

        current_game, next_game = get_knicks_games_info()
        output_file = os.path.join(OUTPUT_DIR, player["output"])
        output_json = {
            "player": player["name"],
            "sport": "nba",
            "player_logs": all_data,
            "current_game": current_game,
            "next_game": next_game
        }
        with open(output_file, "w", encoding="utf-8") as file_handle:
            json.dump(output_json, file_handle, indent=2)
        print(f"Saved {sum(len(year['games']) for year in all_data)} games for {player['name']} from {YEARS} to {output_file}")


if __name__ == "__main__":
    main()
