from flask import Flask, jsonify, render_template
import getpass
import json
import os
import subprocess
import threading
import traceback

app = Flask(__name__)



# Player config (add more as needed)
PLAYERS = [
    {
        'id': 'aaron_judge',
        'name': 'Aaron Judge',
        'file': os.path.join('mlb', 'yankees', 'aaron_judge.json')
    },
    {
        'id': 'giancarlo_stanton',
        'name': 'Giancarlo Stanton',
        'file': os.path.join('mlb', 'yankees', 'giancarlo_stanton.json')
    },
    {
        'id': 'ben_rice',
        'name': 'Ben Rice',
        'file': os.path.join('mlb', 'yankees', 'ben_rice.json')
    },
    {
        'id': 'jazz_chisholm_jr',
        'name': 'Jazz Chisholm Jr.',
        'file': os.path.join('mlb', 'yankees', 'jazz_chisholm_jr.json')
    },
    {
        'id': 'trent_grisham',
        'name': 'Trent Grisham',
        'file': os.path.join('mlb', 'yankees', 'trent_grisham.json')
    },
    {
        'id': 'cody_bellinger',
        'name': 'Cody Bellinger',
        'file': os.path.join('mlb', 'yankees', 'cody_bellinger.json')
    },
    {
        'id': 'ryan_mcmahon',
        'name': 'Ryan McMahon',
        'file': os.path.join('mlb', 'yankees', 'ryan_mcmahon.json')
    }
]

next_game_path = os.path.join('mlb', 'yankees', 'next_yankees_game_output.json')
mlb_teams_path = 'mlb_teams.json'

SCHEDULE_URL = "https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/teams/nyy/schedule"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
YANKEES_SCRIPT = os.path.join(BASE_DIR, 'mlb', 'Yankees.py')



def load_player_data(player_id):
    player = next((p for p in PLAYERS if p['id'] == player_id), None)
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


def load_mlb_teams():
    with open(mlb_teams_path, encoding='utf-8') as f:
        return json.load(f)

def get_current_yankees_game():
    import requests
    from datetime import datetime
    resp = requests.get(SCHEDULE_URL)
    resp.raise_for_status()
    data = resp.json()
    today = datetime.now().date()
    for event in data.get('events', []):
        date_str = event['date'][:10]  # 'YYYY-MM-DD'
        game_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        if game_date == today:
            competitors = event['competitions'][0]['competitors']
            for team in competitors:
                if team['team']['abbreviation'] != 'NYY':
                    opponent = team['team']['displayName']
                    home_away = 'Home' if team['homeAway'] == 'away' else 'Away'
                    return {
                        'date': date_str,
                        'opponent': opponent,
                        'homeAway': home_away
                    }
    return None


@app.route('/run-task1')
def run_task1():
    def run_all_scripts():
        print('Flask is running as user:', getpass.getuser())
        scripts = [
            ("/opt/render/project/src/mlb/Yankees.py", "/opt/render/project/src/mlb"),
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
    return jsonify([{'id': p['id'], 'name': p['name']} for p in PLAYERS])

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
    data = load_player_data(player_id)
    if not data:
        return jsonify({'player_name': 'Unknown Player'})
    player_name = None
    # If data is a dict, try to get name fields
    if isinstance(data, dict):
        player_name = data.get('player') or data.get('name') or data.get('Player')
    # If data is a list, try to get from first item
    elif isinstance(data, list) and data and isinstance(data[0], dict):
        player_name = data[0].get('player') or data[0].get('name') or data[0].get('Player')
    if not player_name:
        player_name = 'Unknown Player'
    return jsonify({'player_name': player_name})



# API to get the next Yankees game info (with opponent abbreviation) for a player
@app.route('/api/next_yankees_game/<player_id>')
def api_next_yankees_game(player_id):
    next_game = load_next_game(player_id)
    if not next_game:
        return jsonify({'error': 'No next Yankees game found.'}), 404
    mlb_teams = load_mlb_teams()
    opp_name = next_game.get('opponent')
    opp_abbr = None
    for team in mlb_teams:
        if team['name'] == opp_name:
            opp_abbr = team['abbreviation']
            break
    next_game['opponent_abbr'] = opp_abbr
    return jsonify(next_game)


# API to get the current Yankees game info for a player
@app.route('/api/current_yankees_game/<player_id>')
def api_current_yankees_game(player_id):
    current_game = load_current_game(player_id)
    if current_game:
        return jsonify(current_game)
    else:
        return jsonify({'error': 'No Yankees game today.'}), 404

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
