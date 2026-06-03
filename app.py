from flask import Flask, jsonify, render_template
import getpass
import json
import os
import subprocess
import threading
import traceback

app = Flask(__name__)
BASE_DIR = '/var/data'
APP_DIR = os.path.dirname(os.path.abspath(__file__))
MLB_DATA_DIR = os.path.join(BASE_DIR, 'mlb', 'yankees')
NBA_DATA_DIR = os.path.join(BASE_DIR, 'nba', 'knicks')
MLB_TEAMS_PATH = os.path.join(APP_DIR, 'mlb_teams.json')
NBA_TEAMS_PATH = os.path.join(APP_DIR, 'nba_teams.json')
YANKEES_SCRIPT = os.path.join(APP_DIR, 'mlb', 'yankees', 'Yankees.py')
BRUNSON_SCRIPT = os.path.join(APP_DIR, 'nba', 'knicks', 'JalenBrunson.py')


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


@app.route('/run-task1')
def run_task1():
    def run_all_scripts():
        print('Flask is running as user:', getpass.getuser())
        scripts = [
            ("/opt/render/project/src/mlb/yankees/Yankees.py", "/opt/render/project/src/mlb/yankees/"),
            ("/opt/render/project/src/nba/knicks/Knicks.py", "/opt/render/project/src/nba/knicks/")
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

    threading.Thread(target=run_all_scripts, daemon=True).start()
    return 'Task started in background! Check logs folder for output.', 200



# List all available players
@app.route('/api/players')
def api_players():
    return jsonify([{'id': p['id'], 'name': p['name'], 'sport': p['sport']} for p in PLAYERS])

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

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
