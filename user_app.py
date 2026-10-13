# Vortex Arena - User App (Python + Flask + SQLite)
# Run: python Vortex_Arena_User_App.py
# First run installs Flask if missing. Opens your browser automatically.
import os, sys, sqlite3, subprocess, webbrowser, threading, time, base64, re
from pathlib import Path
from urllib.parse import quote

try:
    from flask import Flask, request, redirect, url_for, session, flash, render_template_string, g
except ImportError:
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'flask'])
    from flask import Flask, request, redirect, url_for, session, flash, render_template_string, g
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

BASE = Path(__file__).resolve().parent
DB = BASE / 'vortex_arena_users.db'
UPLOADS = BASE / 'vortex_uploads'
UPLOADS.mkdir(exist_ok=True)
UPI_ID = '8796674832@fam'
YOUTUBE = 'https://youtube.com/@smaltanime_00'
app = Flask(__name__)
app.secret_key = os.environ.get('VORTEX_SECRET_KEY', 'change-this-secret-key-before-public-hosting')
app.config['PERMANENT_SESSION_LIFETIME'] = 60 * 60 * 24 * 30  # 30 days; logout clears it
app.config['MAX_CONTENT_LENGTH'] = 4 * 1024 * 1024

GAMES = [
 ('Free Fire','Battle Royale','₹5','https://images.unsplash.com/photo-1542751371-adc38448a05e?w=700&fit=crop'),
 ('BGMI','Battle Royale','₹10','https://images.unsplash.com/photo-1511512578047-dfb367046420?w=700&fit=crop'),
 ('Roblox','Sandbox','₹10','https://images.unsplash.com/photo-1612287230202-1ff1d85d1bdf?w=700&fit=crop'),
 ('Minecraft','Sandbox','₹15','https://images.unsplash.com/photo-1607513746994-51f730a44832?w=700&fit=crop'),
 ('Call of Duty Mobile','Battle Royale','₹10','https://images.unsplash.com/photo-1542751371-adc38448a05e?w=700'),
 ('Valorant','Tactical','₹10','https://images.unsplash.com/photo-1542751371-adc38448a05e?w=700'),
 ('eFootball','Sports','₹10','https://images.unsplash.com/photo-1574629810360-7efbbe195018?w=700'),
 ('Viral Land','Other','₹5','https://images.unsplash.com/photo-1511512578047-dfb367046420?w=700'),
]

def db():
    if 'db' not in g:
        g.db = sqlite3.connect(DB)
        g.db.row_factory = sqlite3.Row
    return g.db
@app.teardown_appcontext
def close_db(exc):
    conn = g.pop('db', None)
    if conn is not None: conn.close()

def init_db():
    with sqlite3.connect(DB) as c:
        c.execute('''CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT,email TEXT UNIQUE NOT NULL,password_hash TEXT NOT NULL,phone TEXT DEFAULT '',username TEXT DEFAULT '',player_uid TEXT DEFAULT '',team_name TEXT DEFAULT '',game TEXT DEFAULT 'Free Fire',game_uid TEXT DEFAULT '',avatar TEXT DEFAULT '',created_at TEXT DEFAULT CURRENT_TIMESTAMP)''')
        c.execute('''CREATE TABLE IF NOT EXISTS tournaments(id INTEGER PRIMARY KEY AUTOINCREMENT,game TEXT NOT NULL,title TEXT NOT NULL,entry_fee INTEGER NOT NULL,prize_pool INTEGER NOT NULL,slots INTEGER NOT NULL,players INTEGER NOT NULL,start_time TEXT NOT NULL,end_time TEXT NOT NULL,room_id TEXT DEFAULT '',room_password TEXT DEFAULT '',status TEXT DEFAULT 'Upcoming',youtube_url TEXT DEFAULT '',image_url TEXT DEFAULT '')''')
        tournament_cols = [r[1] for r in c.execute('PRAGMA table_info(tournaments)')]
        if 'image_url' not in tournament_cols:
            c.execute("ALTER TABLE tournaments ADD COLUMN image_url TEXT DEFAULT ''")
        c.execute('''CREATE TABLE IF NOT EXISTS registrations(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER NOT NULL,tournament_id INTEGER NOT NULL,utr TEXT DEFAULT '',payment_status TEXT DEFAULT 'Pending review',created_at TEXT DEFAULT CURRENT_TIMESTAMP,UNIQUE(user_id,tournament_id))''')
        c.execute('''CREATE TABLE IF NOT EXISTS tournament_results(id INTEGER PRIMARY KEY AUTOINCREMENT,tournament_id INTEGER NOT NULL,player_name TEXT NOT NULL,team_name TEXT DEFAULT '',kills INTEGER DEFAULT 0,score INTEGER DEFAULT 0,position INTEGER NOT NULL,created_at TEXT DEFAULT CURRENT_TIMESTAMP)''')
        n = c.execute('SELECT COUNT(*) FROM tournaments').fetchone()[0]
        if n == 0:
            seed = [
              ('Free Fire','Free Fire Squad Battle',5,100,12,4,'Today • 7:00 PM','Today • 8:00 PM'),
              ('BGMI','BGMI Classic Tournament',10,100,128,64,'Today • 8:30 PM','Today • 9:30 PM'),
              ('Roblox','Roblox Build & Fight',10,100,64,32,'Tomorrow • 5:00 PM','Tomorrow • 6:00 PM'),
              ('Minecraft','Minecraft Survival Cup',15,100,32,18,'Tomorrow • 6:00 PM','Tomorrow • 7:00 PM'),
              ('Call of Duty Mobile','COD Mobile Battle',10,100,100,42,'Tomorrow • 8:00 PM','Tomorrow • 9:00 PM'),
              ('Valorant','Valorant Squad Cup',10,100,40,16,'Sunday • 6:00 PM','Sunday • 7:30 PM'),
              ('eFootball','eFootball Showdown',10,100,32,12,'Sunday • 7:00 PM','Sunday • 8:00 PM')]
            c.executemany('INSERT INTO tournaments(game,title,entry_fee,prize_pool,slots,players,start_time,end_time) VALUES(?,?,?,?,?,?,?,?)',seed)

def current_user():
    uid = session.get('user_id')
    return db().execute('SELECT * FROM users WHERE id=?',(uid,)).fetchone() if uid else None

STYLE = r'''
:root{--bg:#030817;--panel:#08152d;--panel2:#0b1d3b;--line:#2145a1;--blue:#287cff;--purple:#7c20ff;--cyan:#35c7ff;--text:#f2f6ff;--muted:#8fa9d8;--green:#2ce6a6}*{box-sizing:border-box}body{margin:0;background:radial-gradient(ellipse at 50% -10%,#172c70 0,#050b1d 42%,#020611 100%);font-family:Arial,Helvetica,sans-serif;color:var(--text);min-height:100vh}a{color:inherit;text-decoration:none}button,input,select{font:inherit}.wrap{max-width:540px;margin:auto;min-height:100vh;padding-bottom:84px}.top{height:68px;display:flex;align-items:center;gap:10px;padding:10px 16px;border-bottom:1px solid #1b3d91;background:#040b1b;position:sticky;top:0;z-index:5}.logo{width:44px;height:44px;object-fit:contain}.brand{font-size:17px;font-weight:900;letter-spacing:1.5px}.brand small{display:block;color:#57b8ff;font-size:8px;letter-spacing:4px;text-align:center}.right{margin-left:auto;color:#b9d5ff}.content{padding:15px 14px}.card{background:linear-gradient(145deg,#0c1d3b,#050d20);border:1px solid var(--line);border-radius:14px;padding:13px;margin:10px 0;box-shadow:0 0 18px #09246a25}.muted{color:var(--muted);font-size:12px}.title{font-size:22px;font-weight:900;margin:3px 0}.subtitle{color:#57b8ff;font-size:13px;margin-top:4px}.btn{display:inline-flex;align-items:center;justify-content:center;border:1px solid #436fff;border-radius:10px;padding:10px 13px;background:linear-gradient(100deg,#164cff,#831aff);color:white;font-weight:bold;cursor:pointer}.btn.secondary{background:#0c1d3b}.btn.green{background:linear-gradient(100deg,#008cbb,#00b88a);border-color:#12c7e5}.btn.youtube{background:#ff0033;border:1px solid #ff526f;box-shadow:0 0 18px #ff003344;transition:transform .18s ease,box-shadow .18s ease}.btn.youtube:hover{transform:translateY(-2px);box-shadow:0 0 24px #ff003377}.card,.btn,.pill,.game{transition:transform .18s ease,box-shadow .18s ease}.card:hover{box-shadow:0 0 22px #254fff30}.btn.full{width:100%;margin-top:9px}.field{margin:12px 0}.field label{display:block;font-size:12px;color:#a9c5ff;margin-bottom:6px}.field input,.field select{width:100%;background:#030a19;color:white;border:1px solid #2b4b98;border-radius:9px;padding:12px;outline:none}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}.game{overflow:hidden;padding:0}.game img,.tourimg{width:100%;height:100px;object-fit:cover;display:block;background:#101e3d}.game img{transition:transform .25s ease}.game:hover img{transform:scale(1.035)}.game .pad{padding:10px}.game h3{font-size:14px;margin:0 0 5px}.row{display:flex;align-items:center;gap:10px}.between{justify-content:space-between}.avatar{width:76px;height:76px;border-radius:50%;border:2px solid #4c7dff;object-fit:cover;background:#101e3d}.avatar-pick{position:relative;width:96px;height:96px;flex:0 0 96px}.avatar-pick .avatar{width:96px;height:96px;display:block}.avatar-pick button{position:absolute;right:0;bottom:0;width:34px;height:34px;border-radius:50%;border:2px solid #07142b;background:linear-gradient(135deg,#267cff,#8b22ff);color:white;font-size:18px;cursor:pointer;box-shadow:0 0 12px #713bff88}.avatar-hint{font-size:11px;color:#8fa9d8;margin-top:5px}.stat{flex:1;text-align:center;border-right:1px solid #254075}.stat:last-child{border:0}.stat b{display:block;font-size:18px}.hero{background:linear-gradient(100deg,#111e59,#4014a2 60%,#07162e);border:1px solid #5948ff;border-radius:14px;padding:17px;min-height:130px}.hero h2{margin:0 0 7px}.quick{display:grid;grid-template-columns:repeat(4,1fr);gap:7px}.quick a{border:1px solid #23479a;background:#081631;border-radius:10px;text-align:center;padding:12px 3px;font-size:11px}.quick strong{display:block;color:#8c79ff;font-size:21px;margin-bottom:6px}.tour{display:grid;grid-template-columns:94px 1fr;gap:10px;align-items:center}.tour img{width:94px;height:92px;border-radius:10px;object-fit:cover}.tour h3{margin:0 0 5px;font-size:14px}.fee{color:#ffd65b;font-weight:bold}.nav{position:fixed;bottom:0;left:50%;transform:translateX(-50%);width:min(540px,100%);display:grid;grid-template-columns:repeat(6,1fr);background:#030a19;border-top:1px solid #2549a8;padding:7px 3px calc(7px + env(safe-area-inset-bottom));z-index:9}.nav a{text-align:center;color:#9eb5e5;font-size:10px;padding:4px 0}.nav a.active{color:#ad79ff;text-shadow:0 0 12px #7b20ff}.nav b{display:block;font-size:18px;margin-bottom:4px}.flash{padding:10px;border-radius:9px;background:#11264b;border:1px solid #365ab3;margin-bottom:10px;font-size:13px}.search{display:flex;gap:8px}.search input{flex:1;min-width:0}.pill{border:1px solid #244a99;padding:7px 11px;border-radius:20px;color:#c7d8ff;font-size:12px}.live{color:#ff5d7a;font-weight:bold}.hidden{display:none}@media(min-width:700px){.wrap{margin:20px auto;border:1px solid #1c3d8b;border-radius:18px;overflow:hidden;min-height:90vh}.top{position:relative}}
'''
BASE_HTML = r'''<!doctype html><html lang="hi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Vortex Arena</title><style>''' + STYLE + r'''</style></head><body><div class="wrap"><header class="top"><img class="logo" src="https://dummyimage.com/100x100/091b46/7c7cff.png&text=V" alt="Vortex logo"><div class="brand">VORTEX ARENA<small>ESPORTS</small></div><div class="right">♧　<a href="/profile">◉</a></div></header><main class="content">{% with messages=get_flashed_messages() %}{% for m in messages %}<div class="flash">{{m}}</div>{% endfor %}{% endwith %}{{body|safe}}</main>{% if user %}<nav class="nav"><a class="{{'active' if page=='home' else ''}}" href="/"><b>⌂</b>Home</a><a class="{{'active' if page=='games' else ''}}" href="/games"><b>▦</b>Games</a><a class="{{'active' if page=='tournaments' else ''}}" href="/tournaments"><b>♜</b>Match</a><a class="{{'active' if page=='live' else ''}}" href="/live"><b>◉</b>Live</a><a class="{{'active' if page=='leaderboard' else ''}}" href="/leaderboard"><b>▥</b>Result</a><a class="{{'active' if page=='settings' else ''}}" href="/settings"><b>⚙</b>Setting</a></nav>{% endif %}</div></body></html>'''
def page(body, page='home', needs_profile=False):
    user=current_user()
    if user and needs_profile and (not user['username'] or not user['game_uid']): return redirect(url_for('profile'))
    return render_template_string(BASE_HTML,body=body,user=user,page=page)

@app.route('/')
def home():
    if not current_user(): return redirect(url_for('login'))
    u=current_user()
    body=f'''<div class="row"><img class="avatar" src="{u['avatar'] or 'https://dummyimage.com/160x160/101e3d/91a8ff.png&text=PLAYER'}"><div style="flex:1"><b style="font-size:18px">{u['username'] or 'Player'} ✓</b><div class="muted">UID: {u['player_uid'] or 'Add your UID'}</div><span class="pill">Player</span></div><div class="card" style="margin:0"><b>Bronze III</b><div class="muted">Player Level</div><div style="color:#9d72ff">━━━━━━━━</div></div></div>
<div class="card row"><div class="stat"><b>0</b><span class="muted">Total Matches</span></div><div class="stat"><b>0</b><span class="muted">Total Kills</span></div><div class="stat"><b>0%</b><span class="muted">Win Rate</span></div></div>
<div class="hero"><div class="muted">NEXT TOURNAMENT</div><h2>Free Fire — Squad Battle</h2><div>◷ Today • 7:00 PM</div><p><a class="btn" href="/tournaments">Join Tournament</a></p></div>
<h3>Quick Access</h3><div class="quick"><a href="/games"><strong>▦</strong>Games</a><a href="/tournaments"><strong>♜</strong>Tournaments</a><a href="/live"><strong>◉</strong>Live Matches</a><a href="/leaderboard"><strong>▥</strong>Leaderboard</a></div>
<div class="card row between"><div><b>News & Updates</b><div class="muted">New tournaments and match updates</div></div><a href="/tournaments">›</a></div><a class="btn green full" href="{YOUTUBE}" target="_blank" rel="noopener">▶　Go to YouTube Live / Channel</a>'''
    return page(body,'home',True)

@app.route('/register',methods=['GET','POST'])
def register():
    if request.method=='POST':
        email=request.form.get('email','').strip().lower(); password=request.form.get('password',''); phone=request.form.get('phone','').strip()
        if not email or len(password)<8: flash('सही ईमेल और कम से कम 8 अक्षर का पासवर्ड डालें।')
        else:
            try:
                db().execute('INSERT INTO users(email,password_hash,phone) VALUES(?,?,?)',(email,generate_password_hash(password),phone)); db().commit(); flash('Account बन गया! अब Login करें।'); return redirect(url_for('login'))
            except sqlite3.IntegrityError: flash('यह ईमेल पहले से registered है। Login करें।')
    body='''<h1 class="title">Create Account</h1><div class="subtitle">Join Vortex Arena • Play • Compete • Win</div><form method="post"><div class="field"><label>Email address</label><input type="email" name="email" placeholder="you@example.com" required></div><div class="field"><label>Phone (optional)</label><input type="tel" name="phone" placeholder="Phone number"></div><div class="field"><label>Password (minimum 8 characters)</label><input type="password" name="password" minlength="8" required></div><button class="btn full">Create Account</button></form><p class="muted">Already registered? <a href="/login" style="color:#8d8cff">Login</a></p>'''
    return page(body)
@app.route('/login',methods=['GET','POST'])
def login():
    if current_user():
        u=current_user()
        return redirect(url_for('profile' if (not u['username'] or not u['game_uid']) else 'home'))
    if request.method=='POST':
        email=request.form.get('email','').strip().lower(); password=request.form.get('password','')
        u=db().execute('SELECT * FROM users WHERE email=?',(email,)).fetchone()
        if u and check_password_hash(u['password_hash'],password):
            session.clear(); session.permanent=True; session['user_id']=u['id']
            return redirect(url_for('profile' if (not u['username'] or not u['game_uid']) else 'home'))
        flash('ईमेल या पासवर्ड सही नहीं है।')
    body='''<div class="hero"><h2>Welcome Back, Player</h2><div class="muted">Your arena. Your victory.</div></div><h1 class="title">Login</h1><form method="post"><div class="field"><label>Email address</label><input type="email" name="email" placeholder="you@example.com" required></div><div class="field"><label>Password</label><input type="password" name="password" required></div><button class="btn full">Login</button></form><p class="muted">New player? <a href="/register" style="color:#8d8cff">Create Your Account</a></p>'''
    return page(body)
@app.route('/logout')
def logout(): session.clear(); return redirect(url_for('login'))

@app.route('/profile',methods=['GET','POST'])
def profile():
    u=current_user()
    if not u:return redirect(url_for('login'))
    if request.method=='POST':
        username=request.form.get('username','').strip(); puid=request.form.get('player_uid','').strip(); team=request.form.get('team_name','').strip(); game=request.form.get('game','Free Fire'); guid=request.form.get('game_uid','').strip(); avatar=u['avatar']
        f=request.files.get('avatar')
        if f and f.filename:
            if f.mimetype not in ('image/png','image/jpeg','image/webp'): flash('JPG, PNG या WEBP फोटो चुनें।'); return redirect(url_for('profile'))
            ext='.png' if f.mimetype=='image/png' else '.webp' if f.mimetype=='image/webp' else '.jpg'; name=f'user_{u["id"]}{ext}'; f.save(UPLOADS/name); avatar='/uploads/'+name
        db().execute('UPDATE users SET username=?,player_uid=?,team_name=?,game=?,game_uid=?,avatar=? WHERE id=?',(username,puid,team,game,guid,avatar,u['id'])); db().commit(); flash('Profile saved! Welcome to Vortex Arena.'); return redirect(url_for('home'))
    opts=''.join(f'<option {"selected" if g[0]==u['game'] else ""}>{g[0]}</option>' for g in GAMES)
    avatar_src=u['avatar'] or 'https://dummyimage.com/160x160/101e3d/91a8ff.png&text=PLAYER'
    body=f'''<h1 class="title">Player Profile</h1><div class="subtitle">Set up your player card</div><form method="post" enctype="multipart/form-data"><div class="field"><label>Your profile photo</label><div class="avatar-pick"><img id="avatarPreview" class="avatar" src="{avatar_src}" alt="Profile photo"><button type="button" title="Choose photo" aria-label="Choose profile photo" onclick="document.getElementById('avatarFile').click()">＋</button></div><div class="avatar-hint">फोटो बदलने के लिए गोल + आइकन दबाएँ</div><input id="avatarFile" type="file" name="avatar" accept="image/png,image/jpeg,image/webp" hidden onchange="if(this.files[0]) document.getElementById('avatarPreview').src=URL.createObjectURL(this.files[0])"></div><div class="field"><label>Player name</label><input name="username" value="{u['username']}" required placeholder="Your player name"></div><div class="field"><label>Player UID (optional)</label><input name="player_uid" value="{u['player_uid']}" placeholder="Your player ID"></div><div class="field"><label>Team name</label><input name="team_name" value="{u['team_name']}" placeholder="Your team"></div><div class="field"><label>Main game</label><select name="game">{opts}</select></div><div class="field"><label>Game UID</label><input name="game_uid" value="{u['game_uid']}" required placeholder="UID for selected game"></div><button class="btn full">Finish Profile</button></form>'''
    return page(body)
@app.route('/uploads/<path:name>')
def uploaded(name):
    from flask import send_from_directory
    return send_from_directory(UPLOADS,secure_filename(name))

@app.route('/games')
def games():
    if not current_user():return redirect(url_for('login'))
    q=request.args.get('q','').strip().lower()
    matches=[x for x in GAMES if q in x[0].lower()] if q else GAMES
    cards=''.join(f'''<div class="card game"><img src="{img}" alt="{name} game image" loading="lazy"><div class="pad"><h3>{name}</h3><div class="muted">{kind} • Solo / Team</div><div class="row between" style="margin-top:10px"><span class="fee">Entry from {fee}</span><a class="btn" href="/tournaments?game={quote(name)}">Play Now</a></div></div></div>''' for name,kind,fee,img in matches)
    if not cards:cards='<div class="card">इस नाम का गेम नहीं मिला। spelling जाँचें।</div>'
    body=f'''<h1 class="title">All Games</h1><div class="subtitle">Play • Compete • Win</div><form class="search" method="get" action="/games"><input class="field" style="margin:0;background:#030a19;color:white;border:1px solid #2b4b98;border-radius:9px;padding:12px" name="q" value="{q}" placeholder="Search exact game name"><button class="btn">Search</button></form><p class="muted">{len(matches)} games found</p><div class="grid">{cards}</div>'''
    return page(body,'games',True)
@app.route('/tournaments')
def tournaments():
    if not current_user():return redirect(url_for('login'))
    game=request.args.get('game','').strip(); status=request.args.get('status','')
    sql='SELECT * FROM tournaments WHERE 1=1'; args=[]
    if game:sql+=' AND game=?';args.append(game)
    if status:sql+=' AND status=?';args.append(status)
    ts=db().execute(sql+' ORDER BY id',args).fetchall()
    cards=''.join(f'''<div class="card tour"><img src="{(t['image_url'] or next((x[3] for x in GAMES if x[0]==t['game']),GAMES[0][3]))}" alt="{t['game']} game"><div><h3>{t['title']}</h3><div class="fee">₹ {t['prize_pool']:,} Prize Pool</div><div class="muted">◉ {t['players']}/{t['slots']} Players</div><div class="muted">Start: {t['start_time']}</div><div class="row between" style="margin-top:7px"><span class="muted">Entry ₹{t['entry_fee']}</span><a class="btn" href="/join/{t['id']}">Join</a></div></div></div>''' for t in ts)
    if not cards:cards='<div class="card">इस गेम के लिए अभी tournament नहीं है। Admin के द्वारा इसी डेटाबेस में मैच जोड़ने के बाद यहाँ दिखेगा।</div>'
    body=f'''<h1 class="title">Tournaments</h1><div class="subtitle">Big Prizes • Real Competition</div><div class="row" style="flex-wrap:wrap;margin:14px 0"><a class="pill" href="/tournaments">All Games</a> <a class="pill" href="/my-matches">My Tournaments</a></div>{cards}'''
    return page(body,'tournaments',True)
@app.route('/join/<int:tid>',methods=['GET','POST'])
def join(tid):
    u=current_user()
    if not u:return redirect(url_for('login'))
    t=db().execute('SELECT * FROM tournaments WHERE id=?',(tid,)).fetchone()
    if not t:return 'Tournament not found',404
    if request.method=='POST':
        utr=request.form.get('utr','').strip()
        # Basic format/duplicate checks only. Real payment verification requires bank/UPI gateway or authorized admin review.
        # Remove common copy/paste artifacts (spaces, hyphens, quotes); format check only.
        normalized = re.sub(r"[\s\-\u2010-\u2015\u2212'\"`]", '', utr).upper()
        if not re.fullmatch(r'[A-Z0-9]{12,22}', normalized) or not any(ch.isdigit() for ch in normalized):
            flash('UTR format सही नहीं लग रहा। पेमेंट receipt से असली 12–22 अक्षरों/अंकों वाला UPI reference डालें; random text स्वीकार नहीं होगा।')
        elif any(re.sub(r"[\s\-\u2010-\u2015\u2212'\"`]", '', row['utr'] or '').upper() == normalized
                 for row in db().execute('SELECT utr FROM registrations WHERE utr IS NOT NULL').fetchall()):
            flash('यह UTR पहले इस्तेमाल हो चुका है। हर payment reference केवल एक बार जमा हो सकता है।')
        else:
            try:
                db().execute('INSERT INTO registrations(user_id,tournament_id,utr,payment_status) VALUES(?,?,?,?)',(u['id'],tid,normalized,'Submitted for review'))
                db().commit()
                flash('UTR जमा हुआ है और जाँच के लिए pending है। अभी payment verified या confirmed नहीं है।')
                return redirect(url_for('my_matches'))
            except sqlite3.IntegrityError:flash('आप पहले ही इस tournament में join कर चुके हैं।')
    upi=f"upi://pay?pa={quote(UPI_ID)}&pn={quote('Vortex Arena')}&am={t['entry_fee']}&cu=INR&tn={quote(t['title'])}"
    body=f'''<h1 class="title">Register Tournament</h1><div class="card"><h3>{t['title']}</h3><div class="fee">Entry Fee: ₹{t['entry_fee']}</div><div class="muted">Prize pool ₹{t['prize_pool']:,} • {t['players']}/{t['slots']} players</div></div><div class="card"><b>Step 1 — Pay Entry Fee</b><p class="muted">UPI app खुलेगा। पेमेंट करने से पहले नाम और amount जाँचें।</p><a class="btn green full" href="{upi}">Open UPI App</a><p class="muted">UPI ID: <b>{UPI_ID}</b></p><button class="btn secondary full" onclick="navigator.clipboard.writeText('{UPI_ID}').then(()=>alert('UPI ID copied'))">Copy UPI ID</button></div><div class="card"><b>Step 2 — Submit UTR</b><p class="muted">Payment receipt से UTR / UPI reference कॉपी करके यहाँ paste करें। यह तुरंत payment proof नहीं है; admin verification ज़रूरी है।</p><form method="post"><div class="field"><label>UTR / UPI transaction reference</label><input name="utr" minlength="12" maxlength="22" required autocomplete="off" placeholder="Paste UPI reference from receipt"><p class="muted">Random text और पहले इस्तेमाल हुआ UTR reject होगा। Format check बैंक से payment की पुष्टि नहीं है; status review में रहेगा।</p></div><button class="btn full">Submit & Register</button></form></div>'''
    return page(body,'tournaments',True)
@app.route('/my-matches')
def my_matches():
    u=current_user()
    if not u:return redirect(url_for('login'))
    rows=db().execute('SELECT r.*,t.title,t.game,t.start_time,t.end_time,t.room_id,t.room_password FROM registrations r JOIN tournaments t ON t.id=r.tournament_id WHERE r.user_id=? ORDER BY r.id DESC',(u['id'],)).fetchall()
    cards=''.join(f'''<div class="card"><h3>{r['title']}</h3><div class="muted">{r['game']} • {r['start_time']} – {r['end_time']}</div><p>Status: <b>{r['payment_status']}</b></p>{('<div>Room ID: <b>'+r['room_id']+'</b></div>') if r['room_id'] and r['payment_status']=='Verified' else '<div class="muted">Room ID verification के बाद उपलब्ध होगा। Room password सार्वजनिक नहीं दिखाया जाता।</div>'}</div>''' for r in rows)
    body='<h1 class="title">My Matches</h1>'+ (cards or '<div class="card">अभी कोई tournament join नहीं किया।</div>')
    return page(body,'tournaments',True)
@app.route('/live')
def live():
    if not current_user():return redirect(url_for('login'))
    ts=db().execute("SELECT * FROM tournaments WHERE status='Live'").fetchall()
    cards=''.join(f'''<div class="card"><span class="live">● LIVE</span><h3>{t['title']}</h3><div class="muted">{t['players']}/{t['slots']} Players</div><a class="btn" href="{t['youtube_url'] or YOUTUBE}" target="_blank" rel="noopener">▶ Go to Stream</a></div>''' for t in ts)
    body='<h1 class="title">Live Stream</h1><div class="subtitle">Watch • Support • Enjoy</div>'+ (cards or '<div class="card">अभी कोई match live mark नहीं है। Official channel पर देखें।</div>')+f'<a class="btn youtube full" href="{YOUTUBE}" target="_blank" rel="noopener">▶ YouTube · GO TO STREAM</a>'
    return page(body,'live',True)
@app.route('/leaderboard')
def leaderboard():
    if not current_user():return redirect(url_for('login'))
    results=db().execute('SELECT tr.*,t.title,t.game FROM tournament_results tr JOIN tournaments t ON t.id=tr.tournament_id ORDER BY tr.tournament_id DESC,tr.position ASC').fetchall()
    body='<h1 class="title">🏆 Results & Leaderboard</h1><div class="subtitle">Admin द्वारा प्रकाशित टूर्नामेंट रिज़ल्ट</div>'
    if results:
        current_tid=None
        medals={1:'🥇',2:'🥈',3:'🥉'}
        for r in results:
            if r['tournament_id']!=current_tid:
                current_tid=r['tournament_id']
                body+=f'<div class="card"><h3>{r["game"]} — {r["title"]}</h3>'
            medal=medals.get(r['position'],f'#{r["position"]}')
            body+=f'<div class="row between" style="padding:9px 0;border-bottom:1px solid #203b75"><div style="flex:1"><b>{medal} {r["player_name"]}</b><div class="muted">{r["team_name"] or "Team not provided"}</div></div><div style="text-align:right"><b>{r["score"]} pts</b><div class="muted">{r["kills"]} kills</div></div></div>'
            # Close each tournament card before next heading / at end
        body+='</div>'
    else:
        body+='<div class="card"><b>अभी रिज़ल्ट प्रकाशित नहीं हुआ है।</b><p class="muted">Admin द्वारा रिज़ल्ट डालने के बाद यहाँ खिलाड़ियों की position, team, kills और score दिखेंगे।</p></div>'
    rows=db().execute('SELECT username,team_name,game FROM users WHERE username!="" ORDER BY username LIMIT 50').fetchall()
    body+='<h2 class="title" style="font-size:18px;margin-top:20px">Players</h2>'+''.join(f'<div class="card row"><b style="color:#9d7aff">#{i}</b><div style="flex:1"><b>{r["username"]}</b><div class="muted">{r["team_name"] or "Solo Player"} • {r["game"]}</div></div></div>' for i,r in enumerate(rows,1))
    return page(body,'leaderboard',True)
@app.route('/settings')
def settings():
    u=current_user()
    if not u:return redirect(url_for('login'))
    body=f'''<h1 class="title">Settings</h1><div class="card"><b>Account</b><p class="muted">{u['email']}</p><a class="btn secondary" href="/profile">Edit Profile</a></div><div class="card"><b>Support & Channel</b><p class="muted">Vortex Arena YouTube channel</p><a class="btn green" href="{YOUTUBE}" target="_blank" rel="noopener">▶ Go to YouTube</a></div><a class="btn full" href="/logout">Logout</a>'''
    return page(body,'settings',True)

if __name__=='__main__':
    init_db()
    url='http://127.0.0.1:8082'
    threading.Timer(1.2,lambda:webbrowser.open(url)).start()
    print('\nVortex Arena User App is starting...')
    print('Browser URL:',url)
    print('Database:',DB)
    print('Stop with Ctrl+C. Keep this window open while using the app.\n')
    app.run(host='127.0.0.1',port=8082,debug=False)
