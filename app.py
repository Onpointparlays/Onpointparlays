from flask import Flask, render_template, request, session, redirect, url_for
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace with a secure key later

# Gamification data
user_xp = {'Jordan': 0, 'User2': 150, 'User3': 300}
xp_to_level = [0, 100, 250, 500]
last_login = {}
badges = {'Jordan': [], 'User2': ['Sharp Shooter'], 'User3': ['VIP']}
mystery_chests = {'Jordan': 0, 'User2': 1, 'User3': 2}

def get_level(xp):
    for i, threshold in enumerate(xp_to_level):
        if xp < threshold:
            return i
    return len(xp_to_level)

# Track game state
locked_picks = {}
votes = {}
parlay_hits = {}

@app.route('/')
def home():
    if 'username' in session:
        username = session['username']
        xp = user_xp.get(username, 0)
        level = get_level(xp)
        locked = locked_picks.get(username, False)
        hit = parlay_hits.get(username, False)
        last = last_login.get(username, datetime(1970, 1, 1))
        show_bonus = last.date() < datetime.now().date()
        if show_bonus:
            user_xp[username] += 10
            last_login[username] = datetime.now()
        chest = mystery_chests.get(username, 0)
        user_badges = badges.get(username, [])
    else:
        xp = 0
        level = 0
        locked = False
        hit = False
        show_bonus = False
        chest = 0
        user_badges = []
    leaderboard = sorted(user_xp.items(), key=lambda x: x[1], reverse=True)[:3]
    return render_template('index.html', logged_in='username' in session, xp=xp, level=level, leaderboard=leaderboard, locked=locked, hit=hit, show_bonus=show_bonus, chest=chest, badges=user_badges)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        if username not in user_xp:
            user_xp[username] = 0
            last_login[username] = datetime(1970, 1, 1)
            badges[username] = []
            mystery_chests[username] = 0
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
            user_xp[username] += 25
            locked_picks[username] = True
    return redirect(url_for('home'))

@app.route('/vote', methods=['POST'])
def vote():
    if 'username' in session:
        username = session['username']
        votes[username] = votes.get(username, 0) + 1
        user_xp[username] += 10
    return redirect(url_for('home'))

@app.route('/hit_parlay', methods=['POST'])
def hit_parlay():
    if 'username' in session:
        username = session['username']
        if locked_picks.get(username, False) and not parlay_hits.get(username, False):
            user_xp[username] += 100
            parlay_hits[username] = True
            if user_xp[username] >= 100 and 'Sharp Shooter' not in badges[username]:
                badges[username].append('Sharp Shooter')
    return redirect(url_for('home'))

@app.route('/open_chest', methods=['POST'])
def open_chest():
    if 'username' in session:
        username = session['username']
        if mystery_chests[username] < 1:
            mystery_chests[username] += 1
            user_xp[username] += 25  # Example chest reward
    return redirect(url_for('home'))

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=True)