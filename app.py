from flask import Flask, render_template, request, session, redirect, url_for
from datetime import datetime
import sqlite3
import requests

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace with a secure key later
API_KEY = 'beef82de399058c610840c67429aaf50'  # Your Odds API key

def init_db():
    with sqlite3.connect('users.db') as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS users
                        (username TEXT PRIMARY KEY, xp INTEGER, level INTEGER, last_login TEXT, badges TEXT, chests INTEGER, locked INTEGER, hit INTEGER)''')
        conn.commit()

def get_user_data(username):
    with sqlite3.connect('users.db') as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute('SELECT * FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()
        if user:
            return dict(user)
        return {'username': username, 'xp': 0, 'level': 0, 'last_login': '1970-01-01 00:00:00', 'badges': '', 'chests': 0, 'locked': 0, 'hit': 0}

def update_user_data(username, data):
    with sqlite3.connect('users.db') as conn:
        conn.execute('INSERT OR REPLACE INTO users (username, xp, level, last_login, badges, chests, locked, hit) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                    (username, data['xp'], data['level'], data['last_login'], data['badges'], data['chests'], data['locked'], data['hit']))
        conn.commit()

def get_level(xp):
    levels = [0, 100, 250, 500]
    for i, threshold in enumerate(levels):
        if xp < threshold:
            return i
    return len(levels)

def get_odds_api_data():
    sports = ['basketball_nba', 'americanfootball_nfl']  # Try multiple sports
    for sport in sports:
        url = f"https://api.the-odds-api.com/v4/sports/{sport}/odds"
        params = {'api_key': API_KEY, 'regions': 'us', 'markets': 'h2h', 'oddsFormat': 'american'}
        try:
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data and isinstance(data, list) and len(data) > 0:
                    print("Odds API Data:", data[0])  # Debug first item
                    return data
                print(f"No valid odds data for {sport}")
            else:
                print(f"API Error for {sport}: {response.status_code} - {response.text}")
        except requests.RequestException as e:
            print(f"API Request Failed for {sport}: {e}")
    print("No valid data from any sport")
    return []

@app.route('/')
def home():
    init_db()
    if 'username' in session:
        username = session['username']
        user_data = get_user_data(username)
        xp = user_data['xp']
        level = get_level(xp)
        locked = bool(user_data['locked'])
        hit = bool(user_data['hit'])
        last = datetime.strptime(user_data['last_login'], '%Y-%m-%d %H:%M:%S')
        show_bonus = last.date() < datetime.now().date()
        if show_bonus:
            xp += 10
            user_data['last_login'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        chest = user_data['chests']
        if chest < 1 and show_bonus:
            chest += 1
            xp += 25
        user_badges = user_data['badges'].split(',') if user_data['badges'] else []
        user_data.update({'xp': xp, 'level': level, 'locked': locked, 'hit': hit, 'last_login': user_data['last_login'], 'chests': chest, 'badges': ','.join(user_badges)})
        update_user_data(username, user_data)
    else:
        xp = 0
        level = 0
        locked = False
        hit = False
        show_bonus = False
        chest = 0
        user_badges = []
    leaderboard = []
    with sqlite3.connect('users.db') as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute('SELECT username, xp FROM users ORDER BY xp DESC LIMIT 3')
        leaderboard = [dict(row) for row in cursor.fetchall()]
    odds_data = get_odds_api_data()
    return render_template('index.html', logged_in='username' in session, xp=xp, level=level, leaderboard=leaderboard, locked=locked, hit=hit, show_bonus=show_bonus, chest=chest, badges=user_badges, odds_data=odds_data)

@app.route('/login', methods=['GET', 'POST'])
def login():
    init_db()
    if request.method == 'POST':
        username = request.form['username']
        session['username'] = username
        user_data = get_user_data(username)
        if not user_data['last_login']:
            user_data['last_login'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            update_user_data(username, user_data)
        return redirect(url_for('home'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('home'))

@app.route('/lock_pick', methods=['POST'])
def lock_pick():
    if 'username' in session:
        username = session['username']
        user_data = get_user_data(username)
        if not user_data['locked']:
            user_data['xp'] += 25
            user_data['locked'] = 1
            update_user_data(username, user_data)
    return redirect(url_for('home'))

@app.route('/vote', methods=['POST'])
def vote():
    if 'username' in session:
        username = session['username']
        user_data = get_user_data(username)
        user_data['xp'] += 10
        update_user_data(username, user_data)
    return redirect(url_for('home'))

@app.route('/hit_parlay', methods=['POST'])
def hit_parlay():
    if 'username' in session:
        username = session['username']
        user_data = get_user_data(username)
        if user_data['locked'] and not user_data['hit']:
            user_data['xp'] += 100
            user_data['hit'] = 1
            if user_data['xp'] >= 100 and 'Sharp Shooter' not in user_data['badges'].split(','):
                user_data['badges'] = user_data['badges'] + ',Sharp Shooter' if user_data['badges'] else 'Sharp Shooter'
            update_user_data(username, user_data)
    return redirect(url_for('home'))

@app.route('/open_chest', methods=['POST'])
def open_chest():
    if 'username' in session:
        username = session['username']
        user_data = get_user_data(username)
        if user_data['chests'] < 1:
            user_data['chests'] += 1
            user_data['xp'] += 25
            update_user_data(username, user_data)
    return redirect(url_for('home'))

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=True)