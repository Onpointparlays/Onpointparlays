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
                        (username TEXT PRIMARY KEY, xp INTEGER, level INTEGER, last_login TEXT, badges TEXT, chests INTEGER, locked INTEGER, hit INTEGER, parlay_count INTEGER, parlay_picks TEXT, parlay_history TEXT)''')
        conn.commit()

def get_user_data(username):
    with sqlite3.connect('users.db') as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute('SELECT * FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()
        if user:
            picks = user['parlay_picks'].split(',') if user['parlay_picks'] else []
            history = user['parlay_history'].split(',') if user['parlay_history'] else []
            return dict(user, parlay_picks=picks, parlay_history=history)
        return {'username': username, 'xp': 0, 'level': 0, 'last_login': '1970-01-01 00:00:00', 'badges': '', 'chests': 0, 'locked': 0, 'hit': 0, 'parlay_count': 0, 'parlay_picks': '', 'parlay_history': ''}

def update_user_data(username, data):
    with sqlite3.connect('users.db') as conn:
        picks = ','.join(data['parlay_picks']) if data['parlay_picks'] else ''
        history = ','.join(data['parlay_history']) if data['parlay_history'] else ''
        conn.execute('INSERT OR REPLACE INTO users (username, xp, level, last_login, badges, chests, locked, hit, parlay_count, parlay_picks, parlay_history) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                    (username, data['xp'], data['level'], data['last_login'], data['badges'], data['chests'], data['locked'], data['hit'], data['parlay_count'], picks, history))
        conn.commit()
        print(f"Updated user {username}: xp={data['xp']}, parlay_count={data['parlay_count']}, parlay_picks={picks}, parlay_history={history}")

def get_level(xp):
    levels = [0, 100, 250, 500]
    for i, threshold in enumerate(levels):
        if xp < threshold:
            return i
    return len(levels)

def get_odds_api_data():
    sports = ['basketball_nba', 'americanfootball_nfl']
    for sport in sports:
        url = f"https://api.the-odds-api.com/v4/sports/{sport}/odds"
        params = {'api_key': API_KEY, 'regions': 'us', 'markets': 'h2h', 'oddsFormat': 'american'}
        try:
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data and isinstance(data, list) and len(data) > 0:
                    print("Odds API Data:", data[0])
                    return data
                print(f"No valid odds data for {sport}")
            else:
                print(f"API Error for {sport}: {response.status_code} - {response.text}")
        except requests.RequestException as e:
            print(f"API Request Failed for {sport}: {e}")
    print("No valid data from any sport")
    return []

def calculate_parlay_odds(picks):
    if not picks or len(picks) < 2:
        return 0
    total_odds = 1
    for pick in picks:
        odds = pick['bookmakers'][0]['markets'][0]['outcomes'][0]['price']
        if odds > 0:
            total_odds *= (odds / 100) + 1
        else:
            total_odds *= (100 / abs(odds)) + 1
    return int((total_odds - 1) * 100)

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
        parlay_count = user_data['parlay_count']
        parlay_picks = user_data['parlay_picks']
        parlay_history = user_data['parlay_history']
        user_data.update({'xp': xp, 'level': level, 'locked': locked, 'hit': hit, 'last_login': user_data['last_login'], 'chests': chest, 'badges': ','.join(user_badges), 'parlay_count': parlay_count, 'parlay_picks': parlay_picks, 'parlay_history': parlay_history})
        update_user_data(username, user_data)
    else:
        xp = 0
        level = 0
        locked = False
        hit = False
        show_bonus = False
        chest = 0
        user_badges = []
        parlay_count = 0
        parlay_picks = []
        parlay_history = []
    leaderboard = []
    with sqlite3.connect('users.db') as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute('SELECT username, xp FROM users ORDER BY xp DESC LIMIT 3')
        leaderboard = [dict(row) for row in cursor.fetchall()]
    odds_data = get_odds_api_data()
    parlay_odds = calculate_parlay_odds(parlay_picks) if parlay_picks else 0
    return render_template('index.html', logged_in='username' in session, xp=xp, level=level, leaderboard=leaderboard, locked=locked, hit=hit, show_bonus=show_bonus, chest=chest, badges=user_badges, odds_data=odds_data, parlay_count=parlay_count, parlay_picks=parlay_picks, parlay_odds=parlay_odds, parlay_history=parlay_history)

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

@app.route('/profile')
def profile():
    if 'username' in session:
        username = session['username']
        user_data = get_user_data(username)
        return render_template('profile.html', user=user_data)
    return redirect(url_for('login'))

@app.route('/lock_pick', methods=['POST'])
def lock_pick():
    if 'username' in session:
        username = session['username']
        user_data = get_user_data(username)
        if not user_data['locked'] and len(user_data['parlay_picks']) < 3:
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
            if user_data['parlay_count'] >= 2 and user_data['parlay_picks']:
                user_data['xp'] += 50 * user_data['parlay_count']
                if 'Parlay Pro' not in user_data['badges'].split(','):
                    user_data['badges'] = user_data['badges'] + ',Parlay Pro' if user_data['badges'] else 'Parlay Pro'
                user_data['parlay_history'].append(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                user_data['parlay_count'] = 0
                user_data['parlay_picks'] = []
            update_user_data(username, user_data)
    return redirect(url_for('home'))

@app.route('/open_chest', methods=['POST'])
def open_chest():
    if 'username' in session:
        username = session['username']
        user_data = get_user_data(username)
        print(f"Chest check: chests={user_data['chests']}, xp={user_data['xp']}")
        if user_data['chests'] < 1:
            user_data['chests'] += 1
            user_data['xp'] += 25
            update_user_data(username, user_data)
            print(f"Chest opened: new chests={user_data['chests']}, new xp={user_data['xp']}")
    return redirect(url_for('home'))

@app.route('/add_to_parlay', methods=['POST'])
def add_to_parlay():
    if 'username' in session:
        username = session['username']
        user_data = get_user_data(username)
        if user_data['locked'] and len(user_data['parlay_picks']) < 3:
            odds_data = get_odds_api_data()
            if odds_data and len(odds_data) > 0:
                user_data['parlay_picks'].append(odds_data[0])
                user_data['parlay_count'] += 1
                user_data['locked'] = 0
                update_user_data(username, user_data)
    return redirect(url_for('home'))

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=True)