from flask import Flask, jsonify, render_template
import getpass
import json
import os
import requests
import subprocess
import threading
import time
import traceback

app = Flask(__name__)
BASE_DIR = '/var/data'
APP_DIR = os.path.dirname(os.path.abspath(__file__))
MLB_DATA_DIR = os.path.join(BASE_DIR, 'mlb', 'yankees')
NBA_DATA_DIR = os.path.join(BASE_DIR, 'nba', 'knicks')
SPURS_DATA_DIR = os.path.join(BASE_DIR, 'nba', 'spurs')
MLB_TEAMS_PATH = os.path.join(APP_DIR, 'mlb_teams.json')
NBA_TEAMS_PATH = os.path.join(APP_DIR, 'nba_teams.json')
YANKEES_SCRIPT = os.path.join(APP_DIR, 'mlb', 'yankees', 'Yankees.py')
BRUNSON_SCRIPT = os.path.join(APP_DIR, 'nba', 'knicks', 'JalenBrunson.py')
SPURS_SCRIPT = os.path.join(APP_DIR, 'nba', 'spurs', 'Spurs.py')
RUN_TASK_LOCK = threading.Lock()
ODDS_CACHE_LOCK = threading.Lock()
ODDS_API_BASE_URL = 'https://api.the-odds-api.com/v4'
ODDS_API_KEY = os.getenv('THE_ODDS_API_KEY', '364de355ee9806aa403b7c954d539459')
ODDS_EVENTS_CACHE_TTL_SECONDS = int(os.getenv('ODDS_EVENTS_CACHE_TTL_SECONDS', '900'))
ODDS_MARKET_CACHE_TTL_SECONDS = int(os.getenv('ODDS_MARKET_CACHE_TTL_SECONDS', '300'))
ODDS_EVENTS_CACHE = {}
ODDS_MARKET_CACHE = {}
SPORT_ODDS_KEYS = {
    'mlb': 'baseball_mlb',
    'nba': 'basketball_nba'
}
PLAYER_PROP_MARKETS = {
    'mlb': {
        'H': 'batter_hits',
        'HR': 'batter_home_runs',
        'RBI': 'batter_rbis',
        'SB': 'batter_stolen_bases',
        'BB': 'batter_walks'
    },
    'nba': {
        'PTS': 'player_points',
        'REB': 'player_rebounds',
        'AST': 'player_assists',
        'STL': 'player_steals'
    }
}


def player_file(sport, filename):
    if sport == 'nba':
        return os.path.join(NBA_DATA_DIR, filename)
    return os.path.join(MLB_DATA_DIR, filename)


def get_player_config(player_id):
    return next((player for player in PLAYERS if player['id'] == player_id), None)



# Player config (add more as needed)
PLAYERS = [
    {
        'id': 'aaron_judge',
        'name': 'Aaron Judge',
        'sport': 'mlb',
        'file': player_file('mlb', 'aaron_judge.json')
    },
    {
        'id': 'giancarlo_stanton',
        'name': 'Giancarlo Stanton',
        'sport': 'mlb',
        'file': player_file('mlb', 'giancarlo_stanton.json')
    },
    {
        'id': 'ben_rice',
        'name': 'Ben Rice',
        'sport': 'mlb',
        'file': player_file('mlb', 'ben_rice.json')
    },
    {
        'id': 'jazz_chisholm_jr',
        'name': 'Jazz Chisholm Jr.',
        'sport': 'mlb',
        'file': player_file('mlb', 'jazz_chisholm_jr.json')
    },
    {
        'id': 'trent_grisham',
        'name': 'Trent Grisham',
        'sport': 'mlb',
        'file': player_file('mlb', 'trent_grisham.json')
    },
    {
        'id': 'cody_bellinger',
        'name': 'Cody Bellinger',
        'sport': 'mlb',
        'file': player_file('mlb', 'cody_bellinger.json')
    },
    {
        'id': 'ryan_mcmahon',
        'name': 'Ryan McMahon',
        'sport': 'mlb',
        'file': player_file('mlb', 'ryan_mcmahon.json')
    },
    {
        'id': 'jalen_brunson',
        'name': 'Jalen Brunson',
        'sport': 'nba',
        'file': player_file('nba', 'jalen_brunson.json')
    },
    {
        'id': 'karl_anthony_towns',
        'name': 'Karl-Anthony Towns',
        'sport': 'nba',
        'file': player_file('nba', 'karl_anthony_towns.json')
    },
    {
        'id': 'mikal_bridges',
        'name': 'Mikal Bridges',
        'sport': 'nba',
        'file': player_file('nba', 'mikal_bridges.json')
    },
    {
        'id': 'og_anunoby',
        'name': 'OG Anunoby',
        'sport': 'nba',
        'file': player_file('nba', 'og_anunoby.json')
    },
    {
        'id': 'josh_hart',
        'name': 'Josh Hart',
        'sport': 'nba',
        'file': player_file('nba', 'josh_hart.json')
    },
    {
        'id': 'landry_shamet',
        'name': 'Landry Shamet',
        'sport': 'nba',
        'file': os.path.join(NBA_DATA_DIR, 'landry_shamet.json')
    },
    {
        'id': 'victor_wembanyama',
        'name': 'Victor Wembanyama',
        'sport': 'nba',
        'file': os.path.join(SPURS_DATA_DIR, 'victor_wembanyama.json')
    },
    {
        'id': 'julian_champagnie',
        'name': 'Julian Champagnie',
        'sport': 'nba',
        'file': os.path.join(SPURS_DATA_DIR, 'julian_champagnie.json')
    },
    {
        'id': 'stephon_castle',
        'name': 'Stephon Castle',
        'sport': 'nba',
        'file': os.path.join(SPURS_DATA_DIR, 'stephon_castle.json')
    },
    {
        'id': 'devin_vassell',
        'name': 'Devin Vassell',
        'sport': 'nba',
        'file': os.path.join(SPURS_DATA_DIR, 'devin_vassell.json')
    },
    {
        'id': 'dylan_harper',
        'name': 'Dylan Harper',
        'sport': 'nba',
        'file': os.path.join(SPURS_DATA_DIR, 'dylan_harper.json')
    },
    {
        'id': 'deaaron_fox',
        'name': "De'Aaron Fox",
        'sport': 'nba',
        'file': os.path.join(SPURS_DATA_DIR, 'deaaron_fox.json')
    },
    {
        'id': 'keldon_johnson',
        'name': 'Keldon Johnson',
        'sport': 'nba',
        'file': os.path.join(SPURS_DATA_DIR, 'keldon_johnson.json')
    }
    
]

def load_player_data(player_id):
    player = get_player_config(player_id)
    if not player:
        return None
    try:
        with open(player['file'], encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None

def load_player_logs(player_id):
    data = load_player_data(player_id)
    if not data:
        return None
    # New structure: {"player_logs": [...], "current_game": {...}, "next_game": {...}}
    if isinstance(data, dict) and "player_logs" in data:
        return data["player_logs"]
    return data

def load_current_game(player_id):
    data = load_player_data(player_id)
    if not data:
        return None
    if isinstance(data, dict) and "current_game" in data:
        return data["current_game"]
    return None

def load_next_game(player_id):
    data = load_player_data(player_id)
    if not data:
        return None
    if isinstance(data, dict) and "next_game" in data:
        return data["next_game"]
    return None


def load_teams_for_sport(sport):
    teams_path = NBA_TEAMS_PATH if sport == 'nba' else MLB_TEAMS_PATH
    with open(teams_path, encoding='utf-8') as f:
        return json.load(f)


def resolve_opponent_abbreviation(player_id, opponent_name):
    player = get_player_config(player_id)
    if not player or not opponent_name:
        return None
    for team in load_teams_for_sport(player['sport']):
        if team['name'] == opponent_name:
            return team['abbreviation']
    return None


def get_player_team_name(player):
    if player['sport'] == 'mlb':
        return 'New York Yankees'
    if os.path.normpath(player['file']).startswith(os.path.normpath(SPURS_DATA_DIR)):
        return 'San Antonio Spurs'
    return 'New York Knicks'


def normalize_name(value):
    return ''.join(char.lower() for char in str(value or '') if char.isalnum())


def get_target_game(player_id):
    return load_current_game(player_id) or load_next_game(player_id)


def get_prop_market(player, stat):
    return PLAYER_PROP_MARKETS.get(player['sport'], {}).get(stat)


def get_cached_value(cache, cache_key):
    now = time.time()
    with ODDS_CACHE_LOCK:
        entry = cache.get(cache_key)
        if not entry:
            return None
        if entry['expires_at'] <= now:
            cache.pop(cache_key, None)
            return None
        return entry['value']


def set_cached_value(cache, cache_key, value, ttl_seconds):
    with ODDS_CACHE_LOCK:
        cache[cache_key] = {
            'value': value,
            'expires_at': time.time() + ttl_seconds
        }


def fetch_odds_api_json(url, params, cache, cache_key, ttl_seconds):
    cached_value = get_cached_value(cache, cache_key)
    if cached_value is not None:
        return cached_value

    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
    payload = response.json()
    set_cached_value(cache, cache_key, payload, ttl_seconds)
    return payload


def find_event_for_player(player, game_info):
    if not ODDS_API_KEY:
        raise RuntimeError('THE_ODDS_API_KEY is not configured.')

    sport_key = SPORT_ODDS_KEYS.get(player['sport'])
    if not sport_key or not game_info:
        return None

    events = fetch_odds_api_json(
        f'{ODDS_API_BASE_URL}/sports/{sport_key}/events',
        {'apiKey': ODDS_API_KEY},
        ODDS_EVENTS_CACHE,
        ('events', sport_key),
        ODDS_EVENTS_CACHE_TTL_SECONDS
    )

    team_name = get_player_team_name(player)
    opponent_name = game_info.get('opponent')
    home_away = game_info.get('homeAway')
    for event in events:
        home_team = event.get('home_team')
        away_team = event.get('away_team')
        if home_away == 'Home' and home_team == team_name and away_team == opponent_name:
            return event
        if home_away == 'Away' and away_team == team_name and home_team == opponent_name:
            return event
        if {home_team, away_team} == {team_name, opponent_name}:
            return event
    return None


def extract_player_lines(odds_data, player_name, market_key):
    normalized_player_name = normalize_name(player_name)
    lines = []

    for bookmaker in odds_data.get('bookmakers', []):
        market = next((item for item in bookmaker.get('markets', []) if item.get('key') == market_key), None)
        if not market:
            continue

        grouped_lines = {}
        for outcome in market.get('outcomes', []):
            if normalize_name(outcome.get('description')) != normalized_player_name:
                continue

            point = outcome.get('point')
            if point is None:
                continue

            grouped_line = grouped_lines.setdefault(
                str(point),
                {
                    'bookmaker': bookmaker.get('title'),
                    'point': point,
                    'over_price': None,
                    'under_price': None,
                    'last_update': market.get('last_update')
                }
            )
            outcome_name = str(outcome.get('name') or '').lower()
            if outcome_name == 'over':
                grouped_line['over_price'] = outcome.get('price')
            elif outcome_name == 'under':
                grouped_line['under_price'] = outcome.get('price')

        lines.extend(grouped_lines.values())

    return lines


def fetch_player_prop_lines(player_id, stat):
    player = get_player_config(player_id)
    if not player:
        return {'error': 'Player not found.'}, 404

    market = get_prop_market(player, stat)
    if not market:
        return {'error': 'Unsupported stat for player sport.'}, 404

    if not ODDS_API_KEY:
        return {'error': 'THE_ODDS_API_KEY is not configured.'}, 503

    game_info = get_target_game(player_id)
    if not game_info:
        return {'error': 'No current or next game found for player.'}, 404

    try:
        event = find_event_for_player(player, game_info)
        if not event:
            return {'error': 'No matching event found in odds feed.'}, 404

        odds_data = fetch_odds_api_json(
            f"{ODDS_API_BASE_URL}/sports/{SPORT_ODDS_KEYS[player['sport']]}/events/{event['id']}/odds",
            {
                'apiKey': ODDS_API_KEY,
                'regions': 'us',
                'markets': market,
                'oddsFormat': 'american'
            },
            ODDS_MARKET_CACHE,
            ('event-odds', player['sport'], event['id'], market, 'us', 'american'),
            ODDS_MARKET_CACHE_TTL_SECONDS
        )
        lines = extract_player_lines(odds_data, player['name'], market)
        if not lines:
            return {'error': 'No prop line available for this player/stat.'}, 404

        return {
            'player_id': player_id,
            'player_name': player['name'],
            'sport': player['sport'],
            'stat': stat,
            'market': market,
            'event': {
                'id': event.get('id'),
                'home_team': event.get('home_team'),
                'away_team': event.get('away_team'),
                'commence_time': event.get('commence_time')
            },
            'line': lines[0],
            'lines': lines
        }, 200
    except requests.RequestException as exc:
        return {'error': f'Odds API request failed: {exc}'}, 502


@app.route('/run-task1')
def run_task1():
    def run_all_scripts():
        try:
            print('Flask is running as user:', getpass.getuser())
            scripts = [
                ("/opt/render/project/src/mlb/yankees/Yankees.py", "/opt/render/project/src/mlb/yankees/"),
                ("/opt/render/project/src/nba/knicks/Knicks.py", "/opt/render/project/src/nba/knicks/"),
                ("/opt/render/project/src/nba/spurs/Spurs.py", "/opt/render/project/src/nba/spurs/")
                
            ]
            for script, cwd in scripts:
                try:
                    result = subprocess.run(
                        ['python', script],
                        check=True,
                        cwd=cwd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True
                    )
                    print(f"{os.path.basename(script)} ran successfully!")
                    print('STDOUT:', result.stdout)
                    print('STDERR:', result.stderr)
                except subprocess.CalledProcessError as e:
                    error_trace = traceback.format_exc()
                    print(f"Error running {os.path.basename(script)}:\n{error_trace}")
                    print('STDOUT:', e.stdout)
                    print('STDERR:', e.stderr)
        finally:
            RUN_TASK_LOCK.release()

    if not RUN_TASK_LOCK.acquire(blocking=False):
        return 'Task is already running.', 409

    threading.Thread(target=run_all_scripts, daemon=True).start()
    return 'Task started in background! Check logs folder for output.', 200



# List all available players
@app.route('/api/players')
def api_players():
    players_out = []
    for p in PLAYERS:
        team_name = get_player_team_name(p)
        team_abbr = None
        try:
            for team in load_teams_for_sport(p['sport']):
                if team.get('name') == team_name:
                    team_abbr = team.get('abbreviation')
                    break
        except Exception:
            team_abbr = None
        players_out.append({'id': p['id'], 'name': p['name'], 'sport': p['sport'], 'team_abbr': team_abbr})
    return jsonify(players_out)

# Get games for a specific player

# Get games for a specific player (all years, flat list)
@app.route('/api/games/<player_id>')
def api_games_player(player_id):
    logs = load_player_logs(player_id)
    if not logs:
        return jsonify({'error': 'Player not found or data missing.'}), 404
    all_games = []
    for year in logs:
        all_games.extend(year['games'])
    return jsonify(all_games)

# API to get the player name from the JSON file (dynamic)
@app.route('/api/player_name/<player_id>')
def api_player_name(player_id):
    player = get_player_config(player_id)
    if not player:
        return jsonify({'player_name': 'Unknown Player', 'sport': None})
    return jsonify({'player_name': player['name'], 'sport': player['sport']})



# API to get the next game info (with opponent abbreviation) for a player
@app.route('/api/next_game/<player_id>')
def api_next_game(player_id):
    next_game = load_next_game(player_id)
    if not next_game:
        return jsonify({'error': 'No next game found.'}), 404
    response = dict(next_game)
    response['opponent_abbr'] = resolve_opponent_abbreviation(player_id, next_game.get('opponent'))
    return jsonify(response)


# API to get the current game info for a player
@app.route('/api/current_game/<player_id>')
def api_current_game(player_id):
    current_game = load_current_game(player_id)
    if current_game:
        return jsonify(current_game)
    else:
        return jsonify({'error': 'No game today.'}), 404


@app.route('/api/teams/<sport>')
def api_teams(sport):
    if sport not in {'mlb', 'nba'}:
        return jsonify({'error': 'Unsupported sport.'}), 404
    return jsonify(load_teams_for_sport(sport))


@app.route('/api/player_line/<player_id>/<stat>')
def api_player_line(player_id, stat):
    payload, status_code = fetch_player_prop_lines(player_id, stat)
    return jsonify(payload), status_code

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
