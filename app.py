from flask import Flask, render_template, request, session, redirect, url_for
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace with a secure key later

# Simple in-memory XP and level system (placeholder)
user_xp = {'Jordan': 0, 'User2': 150, 'User3': 300}  # Example user data
xp_to_level = [0, 100, 250, 500]  # Levels 1, 2, 3 (expand later)
last_login = {}  # Track last login date for daily bonus

def get_level(xp):
    for i, threshold in enumerate(xp_to_level):
        if xp < threshold:
            return i
    return len(xp_to_level)

# Track locked picks, votes, and parlay hits
locked_picks = {}
votes = {}  # Track votes per user
parlay_hits = {}  # Track parlay hit status

@app.route('/')
def home():
    if 'username' in session:
        username = session['username']
        xp = user_xp.get(username, 0)
        level = get_level(xp)
        locked = locked_picks.get(username, False)
        hit = parlay_hits.get(username, False)
        # Check for daily login bonus
        last = last_login.get(username, datetime(1970, 1, 1))
        if last.date() < datetime.now().date():
            user_xp[username] += 10  # +10 XP for daily login
            last_login[username] = datetime.now()
    else:
        xp = 0
        level = 0
        locked = False
        hit = False
    leaderboard = sorted(user_xp.items(), key=lambda x: x[1], reverse=True)[:3]
    return render_template('index.html', logged_in='username' in session, xp=xp, level=level, leaderboard=leaderboard, locked=locked, hit=hit)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        if username not in user_xp:
            user_xp[username] = 0
        session['username'] = username
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
        if not locked_picks.get(username, False):
            user_xp[username] = user_xp.get(username, 0) + 25  # +25 XP for locking
            locked_picks[username] = True
    return redirect(url_for('home'))

@app.route('/vote', methods=['POST'])
def vote():
    if 'username' in session:
        username = session['username']
        votes[username] = votes.get(username, 0) + 1
        user_xp[username] = user_xp.get(username, 0) + 10  # +10 XP for voting
    return redirect(url_for('home'))

@app.route('/hit_parlay', methods=['POST'])
def hit_parlay():
    if 'username' in session:
        username = session['username']
        if locked_picks.get(username, False) and not parlay_hits.get(username, False):
            user_xp[username] = user_xp.get(username, 0) + 100  # +100 XP for hitting parlay
            parlay_hits[username] = True
    return redirect(url_for('home'))

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)