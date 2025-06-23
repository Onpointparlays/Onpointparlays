from flask import Flask, render_template, request, session, redirect, url_for

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace with a secure key later

# Simple in-memory XP and level system (placeholder)
user_xp = {'Jordan': 0, 'User2': 150, 'User3': 300}  # Example user data
xp_to_level = [0, 100, 250, 500]  # Levels 1, 2, 3 (expand later)

def get_level(xp):
    for i, threshold in enumerate(xp_to_level):
        if xp < threshold:
            return i
    return len(xp_to_level)

@app.route('/')
def home():
    if 'username' in session:
        xp = user_xp.get(session['username'], 0)
        level = get_level(xp)
    else:
        xp = 0
        level = 0
    leaderboard = sorted(user_xp.items(), key=lambda x: x[1], reverse=True)[:3]  # Top 3 users
    return render_template('index.html', logged_in='username' in session, xp=xp, level=level, leaderboard=leaderboard)

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

if __name__ == '__main__':
    app.run(debug=True)