# Vortex Arena - User App (Python + Flask + SQLite)
# Run: python Vortex_Arena_User_App.py
# First run installs Flask if missing. Opens your browser automatically.
import os, sys, sqlite3, subprocess, webbrowser, threading, time, base64, re, html
from datetime import datetime, timezone, timedelta
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
DB = Path(os.environ.get('VORTEX_DB_PATH', str(BASE / 'vortex_arena_users.db'))).resolve()
UPLOADS = Path(os.environ.get('VORTEX_UPLOADS_DIR', str(BASE / 'vortex_uploads'))).resolve()
UPLOADS.mkdir(exist_ok=True)
UPI_ID = '8796674832@fam'
CONTACT_PHONE = '8796674832'
WHATSAPP_SUPPORT = 'https://wa.me/9187966744832'
DISCORD_URL = 'https://discord.gg/pY9dvhaxs'
YOUTUBE = 'https://youtube.com/@smaltanime_00'
app = Flask(__name__)
app.secret_key = os.environ.get('VORTEX_SECRET_KEY', 'change-this-secret-key-before-public-hosting')
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # video evidence uploads up to 50 MB
app.config['PERMANENT_SESSION_LIFETIME'] = 60 * 60 * 24 * 30  # 30 days; logout clears it

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
        c.execute('''CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT,email TEXT UNIQUE NOT NULL,password_hash TEXT NOT NULL,phone TEXT DEFAULT '',username TEXT DEFAULT '',player_uid TEXT DEFAULT '',team_name TEXT DEFAULT '',game TEXT DEFAULT 'Free Fire',game_uid TEXT DEFAULT '',avatar TEXT DEFAULT '',created_at TEXT DEFAULT CURRENT_TIMESTAMP,arena_uid TEXT DEFAULT '',rank_points INTEGER DEFAULT 0,rank_name TEXT DEFAULT 'Bronze',master_right_until TEXT DEFAULT '')''')
        cols=[r[1] for r in c.execute('PRAGMA table_info(users)')]
        for col,definition in [('arena_uid',"TEXT DEFAULT ''"),('rank_points','INTEGER DEFAULT 0'),('rank_name',"TEXT DEFAULT 'Bronze'"),('master_right_until',"TEXT DEFAULT ''"),('player_country',"TEXT DEFAULT 'India'"),('player_theme',"TEXT DEFAULT 'Neon Blue'"),('player_bio',"TEXT DEFAULT ''")]:
            if col not in cols: c.execute(f'ALTER TABLE users ADD COLUMN {col} {definition}')
        rows=c.execute("SELECT id,arena_uid FROM users WHERE arena_uid IS NULL OR arena_uid=''").fetchall()
        for row in rows: c.execute('UPDATE users SET arena_uid=? WHERE id=?',(f'VA-{10000+row[0]}',row[0]))
        c.execute('''CREATE TABLE IF NOT EXISTS tournaments(id INTEGER PRIMARY KEY AUTOINCREMENT,game TEXT NOT NULL,title TEXT NOT NULL,entry_fee INTEGER NOT NULL,prize_pool INTEGER NOT NULL,slots INTEGER NOT NULL,players INTEGER NOT NULL,start_time TEXT NOT NULL,end_time TEXT NOT NULL,room_id TEXT DEFAULT '',room_password TEXT DEFAULT '',status TEXT DEFAULT 'Upcoming',youtube_url TEXT DEFAULT '')''')
        c.execute('''CREATE TABLE IF NOT EXISTS registrations(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER NOT NULL,tournament_id INTEGER NOT NULL,utr TEXT DEFAULT '',payment_status TEXT DEFAULT 'Pending review',created_at TEXT DEFAULT CURRENT_TIMESTAMP,UNIQUE(user_id,tournament_id))''')
        c.execute('''CREATE TABLE IF NOT EXISTS tournament_results(id INTEGER PRIMARY KEY AUTOINCREMENT,tournament_id INTEGER NOT NULL,player_name TEXT NOT NULL,team_name TEXT DEFAULT '',kills INTEGER DEFAULT 0,score INTEGER DEFAULT 0,position INTEGER NOT NULL,created_at TEXT DEFAULT CURRENT_TIMESTAMP,team_position INTEGER DEFAULT 0)''')
        result_cols=[r[1] for r in c.execute('PRAGMA table_info(tournament_results)')]
        if 'team_position' not in result_cols: c.execute('ALTER TABLE tournament_results ADD COLUMN team_position INTEGER DEFAULT 0')
        c.execute('''CREATE TABLE IF NOT EXISTS rank_history(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER NOT NULL,delta INTEGER NOT NULL,reason TEXT NOT NULL,created_at TEXT DEFAULT CURRENT_TIMESTAMP)''')
        # New feature tables: additive migrations only; existing tables/data remain intact.
        for sql in [
          "CREATE TABLE IF NOT EXISTS announcements(id INTEGER PRIMARY KEY AUTOINCREMENT,title TEXT NOT NULL,message TEXT NOT NULL,image_url TEXT DEFAULT '',active INTEGER DEFAULT 1,created_at TEXT DEFAULT CURRENT_TIMESTAMP)",
          "CREATE TABLE IF NOT EXISTS banners(id INTEGER PRIMARY KEY AUTOINCREMENT,title TEXT DEFAULT '',image_url TEXT NOT NULL,link_url TEXT DEFAULT '',active INTEGER DEFAULT 1,created_at TEXT DEFAULT CURRENT_TIMESTAMP)",
          "CREATE TABLE IF NOT EXISTS teams(id INTEGER PRIMARY KEY AUTOINCREMENT,team_uid TEXT UNIQUE,name TEXT NOT NULL,game TEXT DEFAULT 'Free Fire',leader_id INTEGER NOT NULL,created_at TEXT DEFAULT CURRENT_TIMESTAMP)",
          "CREATE TABLE IF NOT EXISTS team_members(id INTEGER PRIMARY KEY AUTOINCREMENT,team_id INTEGER NOT NULL,user_id INTEGER NOT NULL,status TEXT DEFAULT 'Pending',created_at TEXT DEFAULT CURRENT_TIMESTAMP,UNIQUE(team_id,user_id))",
          "CREATE TABLE IF NOT EXISTS team_requests(id INTEGER PRIMARY KEY AUTOINCREMENT,from_user_id INTEGER NOT NULL,to_user_id INTEGER NOT NULL,message TEXT DEFAULT '',status TEXT DEFAULT 'Pending',created_at TEXT DEFAULT CURRENT_TIMESTAMP)",
          "CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY AUTOINCREMENT,from_user_id INTEGER NOT NULL,to_user_id INTEGER,team_id INTEGER,message TEXT NOT NULL,created_at TEXT DEFAULT CURRENT_TIMESTAMP)",
          "CREATE TABLE IF NOT EXISTS reports(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER NOT NULL,category TEXT NOT NULL,details TEXT NOT NULL,status TEXT DEFAULT 'Open',admin_note TEXT DEFAULT '',created_at TEXT DEFAULT CURRENT_TIMESTAMP)",
          "CREATE TABLE IF NOT EXISTS user_notifications(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER NOT NULL,message TEXT NOT NULL,seen INTEGER DEFAULT 0,created_at TEXT DEFAULT CURRENT_TIMESTAMP)",
          "CREATE TABLE IF NOT EXISTS achievements(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER NOT NULL,code TEXT NOT NULL,title TEXT NOT NULL,created_at TEXT DEFAULT CURRENT_TIMESTAMP,UNIQUE(user_id,code))",
          "CREATE TABLE IF NOT EXISTS admin_audit(id INTEGER PRIMARY KEY AUTOINCREMENT,admin_name TEXT DEFAULT 'Admin',action TEXT NOT NULL,details TEXT DEFAULT '',created_at TEXT DEFAULT CURRENT_TIMESTAMP)",
          "CREATE TABLE IF NOT EXISTS result_awards(id INTEGER PRIMARY KEY AUTOINCREMENT,tournament_id INTEGER NOT NULL,user_id INTEGER NOT NULL,delta INTEGER NOT NULL,reason TEXT NOT NULL,UNIQUE(tournament_id,user_id,reason))",
          "CREATE TABLE IF NOT EXISTS support_messages(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER NOT NULL,sender_role TEXT NOT NULL,sender_id INTEGER,message TEXT NOT NULL,created_at TEXT DEFAULT CURRENT_TIMESTAMP,seen INTEGER DEFAULT 0)",
          "CREATE TABLE IF NOT EXISTS challenge_entries(id INTEGER PRIMARY KEY AUTOINCREMENT,challenge_id INTEGER NOT NULL,user_id INTEGER NOT NULL,player_name TEXT NOT NULL,game_uid TEXT NOT NULL,player_card_id TEXT DEFAULT '',created_at TEXT DEFAULT CURRENT_TIMESTAMP,UNIQUE(challenge_id,user_id))"
        ]: c.execute(sql)
        msg_cols=[r[1] for r in c.execute('PRAGMA table_info(messages)')]
        if 'seen' not in msg_cols: c.execute('ALTER TABLE messages ADD COLUMN seen INTEGER DEFAULT 0')
        # Additive columns for game/map/team/banner support.
        cols=[r[1] for r in c.execute('PRAGMA table_info(tournaments)')]
        for col,definition in [('image_url',"TEXT DEFAULT ''"),('map_name',"TEXT DEFAULT ''"),('mode',"TEXT DEFAULT 'Squad'"),('team_size','INTEGER DEFAULT 4'),('countdown_minutes','INTEGER DEFAULT 10')]:
            if col not in cols: c.execute(f'ALTER TABLE tournaments ADD COLUMN {col} {definition}')
        cols=[r[1] for r in c.execute('PRAGMA table_info(registrations)')]
        for col,definition in [('registration_status',"TEXT DEFAULT 'Pending'"),('winner_status',"TEXT DEFAULT ''"),('payout_status',"TEXT DEFAULT 'Not paid'"),('team_id','INTEGER'),('slot_number','INTEGER')]:
            if col not in cols: c.execute(f'ALTER TABLE registrations ADD COLUMN {col} {definition}')
        # Remove only known demo tournaments seeded by earlier versions. Real/admin-created records stay intact.
        demo_titles=('Free Fire Squad Battle','BGMI Classic Tournament','Roblox Build & Fight','Minecraft Survival Cup','COD Mobile Battle','Valorant Squad Cup','eFootball Showdown')
        c.executemany("DELETE FROM tournaments WHERE title=? AND COALESCE(room_id,'')='' AND COALESCE(room_password,'')='' AND status='Upcoming' AND NOT EXISTS (SELECT 1 FROM registrations r WHERE r.tournament_id=tournaments.id)", [(x,) for x in demo_titles])

def rank_for_points(points):
    points=max(0,int(points or 0))
    if points>=3000:return 'Master Right'
    if points>=2500:return 'Master'
    if points>=1000:return 'Diamond'
    if points>=400:return 'Gold'
    if points>=200:return 'Silver'
    return 'Bronze'

def refresh_tournament_slots(conn, tournament_id):
    """Assign verified/approved entrants to numbered team slots; 4 players share each squad slot."""
    t=conn.execute('SELECT slots,team_size FROM tournaments WHERE id=?',(tournament_id,)).fetchone()
    if not t:return
    size=max(1,min(4,int(t['team_size'] or 4)))
    rows=conn.execute("SELECT id FROM registrations WHERE tournament_id=? AND payment_status='Verified' AND registration_status!='Rejected' ORDER BY id",(tournament_id,)).fetchall()
    for i,row in enumerate(rows):
        slot=(i//size)+1
        if slot<=int(t['slots']): conn.execute('UPDATE registrations SET slot_number=? WHERE id=?',(slot,row['id']))
        else: conn.execute('UPDATE registrations SET slot_number=NULL WHERE id=?',(row['id'],))
    conn.execute('UPDATE tournaments SET players=? WHERE id=?',(len(rows),tournament_id))

def room_is_released(row):
    if row['payment_status']!='Verified': return False
    try:
        start=datetime.strptime(row['start_time'],'%Y-%m-%d %H:%M').replace(tzinfo=timezone(timedelta(hours=5,minutes=30)))
        release_at=start-timedelta(minutes=max(0,int(row['countdown_minutes'] or 0)))
        return datetime.now(timezone(timedelta(hours=5,minutes=30)))>=release_at
    except (ValueError,TypeError,KeyError):
        return str(row['status'] if 'status' in row.keys() else '')=='Live'

def current_user():
    uid = session.get('user_id')
    return db().execute('SELECT * FROM users WHERE id=?',(uid,)).fetchone() if uid else None

STYLE = r'''
:root{--bg:#030817;--panel:#08152d;--panel2:#0b1d3b;--line:#2145a1;--blue:#287cff;--purple:#7c20ff;--cyan:#35c7ff;--text:#f2f6ff;--muted:#8fa9d8;--green:#2ce6a6}*{box-sizing:border-box}html,body{max-width:100%;overflow-x:hidden}body{margin:0;background:radial-gradient(ellipse at 50% -10%,#172c70 0,#050b1d 42%,#020611 100%);font-family:Arial,Helvetica,sans-serif;color:var(--text);min-height:100vh}a{color:inherit;text-decoration:none}button,input,select{font:inherit}.wrap{max-width:540px;margin:auto;min-height:100vh;padding-bottom:84px}.top{height:68px;display:flex;align-items:center;gap:10px;padding:10px 16px;border-bottom:1px solid #1b3d91;background:#040b1b;position:sticky;top:0;z-index:5}.logo{width:44px;height:44px;object-fit:contain}.brand{font-size:17px;font-weight:900;letter-spacing:1.5px}.brand small{display:block;color:#57b8ff;font-size:8px;letter-spacing:4px;text-align:center}.right{margin-left:auto;color:#b9d5ff}.content{padding:15px 14px}.card{background:linear-gradient(145deg,#0c1d3b,#050d20);border:1px solid var(--line);border-radius:14px;padding:13px;margin:10px 0;box-shadow:0 0 18px #09246a25}.muted{color:var(--muted);font-size:12px}.title{font-size:22px;font-weight:900;margin:3px 0}.subtitle{color:#57b8ff;font-size:13px;margin-top:4px}.btn{display:inline-flex;align-items:center;justify-content:center;border:1px solid #436fff;border-radius:10px;padding:10px 13px;background:linear-gradient(100deg,#164cff,#831aff);color:white;font-weight:bold;cursor:pointer}.btn.secondary{background:#0c1d3b}.btn.green{background:linear-gradient(100deg,#008cbb,#00b88a);border-color:#12c7e5}.btn.youtube{background:#ff0033;border:1px solid #ff526f;box-shadow:0 0 18px #ff003344;transition:transform .18s ease,box-shadow .18s ease}.btn.youtube:hover{transform:translateY(-2px);box-shadow:0 0 24px #ff003377}.card,.btn,.pill,.game{transition:transform .18s ease,box-shadow .18s ease}.card:hover{box-shadow:0 0 22px #254fff30}.btn.full{width:100%;margin-top:9px}.field{margin:12px 0}.field label{display:block;font-size:12px;color:#a9c5ff;margin-bottom:6px}.field input,.field select{width:100%;background:#030a19;color:white;border:1px solid #2b4b98;border-radius:9px;padding:12px;outline:none}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}.game{overflow:hidden;padding:0}.game img,.tourimg{width:100%;height:100px;object-fit:cover;display:block;background:#101e3d}.game img{transition:transform .25s ease}.game:hover img{transform:scale(1.035)}.game .pad{padding:10px}.game h3{font-size:14px;margin:0 0 5px}.row{display:flex;align-items:center;gap:10px}.between{justify-content:space-between}.avatar{width:76px;height:76px;border-radius:50%;border:2px solid #4c7dff;object-fit:cover;background:#101e3d}.avatar-pick{position:relative;width:96px;height:96px;flex:0 0 96px}.avatar-pick .avatar{width:96px;height:96px;display:block}.avatar-pick button{position:absolute;right:0;bottom:0;width:34px;height:34px;border-radius:50%;border:2px solid #07142b;background:linear-gradient(135deg,#267cff,#8b22ff);color:white;font-size:18px;cursor:pointer;box-shadow:0 0 12px #713bff88}.avatar-hint{font-size:11px;color:#8fa9d8;margin-top:5px}.stat{flex:1;text-align:center;border-right:1px solid #254075}.stat:last-child{border:0}.stat b{display:block;font-size:18px}.hero{background:linear-gradient(100deg,#111e59,#4014a2 60%,#07162e);border:1px solid #5948ff;border-radius:14px;padding:17px;min-height:130px}.hero h2{margin:0 0 7px}.quick{display:grid;grid-template-columns:repeat(4,1fr);gap:7px}.quick a{border:1px solid #23479a;background:#081631;border-radius:10px;text-align:center;padding:12px 3px;font-size:11px}.quick strong{display:block;color:#8c79ff;font-size:21px;margin-bottom:6px}.tour{display:grid;grid-template-columns:94px 1fr;gap:10px;align-items:center}.tour img{width:94px;height:92px;border-radius:10px;object-fit:cover}.tour h3{margin:0 0 5px;font-size:14px}.banner-slider{display:flex;gap:10px;overflow-x:auto;max-width:100%;scroll-snap-type:x mandatory;padding-bottom:8px}.banner-slide{min-width:0;overflow:hidden}.banner-slide img{width:100%;max-width:100%;height:140px;object-fit:cover;display:block;border-radius:10px}.hero-banner{display:block;width:100%;max-width:100%;height:160px;object-fit:cover;border-radius:10px;margin:10px 0}.featured-hero{overflow:hidden;position:relative}.live-badge{display:inline-block;background:#ed1737;color:#fff;font-weight:900;letter-spacing:1px;border-radius:5px;padding:5px 10px;font-size:12px;box-shadow:0 0 12px #ed173755;margin-bottom:8px}.tour-image-wrap{position:relative;min-width:0}.tour-image-wrap img{width:100%;height:92px;object-fit:cover;border-radius:10px}.tour-image-wrap .live-badge{position:absolute;z-index:1;top:6px;left:6px;margin:0}.game-image-wrap{height:100px;overflow:hidden}.game-image-wrap img{width:100%;height:100%;object-fit:cover}.game-placeholder{height:100%;display:flex;align-items:center;justify-content:center;background:#101e3d;color:#b9d5ff;font-weight:bold}.player-card{border:1px solid #6547ff;border-radius:18px;overflow:hidden;background:linear-gradient(135deg,#07142c,#1c1450 55%,#07142c);box-shadow:0 0 28px #4228c455}.player-card-head{padding:16px;background:linear-gradient(90deg,#0c2d70,#5b18c7);display:flex;justify-content:space-between;gap:8px;align-items:center}.player-card-brand{font-weight:900;letter-spacing:2px}.player-card-tag{font-size:10px;letter-spacing:1px}.player-card-main{display:flex;gap:15px;align-items:center;padding:18px}.player-card-avatar{width:90px;height:90px;border-radius:50%;object-fit:cover;border:3px solid #7d6aff}.player-card-rank{display:inline-block;margin-top:8px;padding:5px 10px;border-radius:20px;background:#211b57;border:1px solid #8b70ff;color:#fff}.player-card-stats{display:grid;grid-template-columns:repeat(4,1fr);border-top:1px solid #34316f;border-bottom:1px solid #34316f;padding:12px 5px}.player-card-stats div{text-align:center;border-right:1px solid #34316f}.player-card-stats div:last-child{border:0}.player-card-stats b,.player-card-stats span{display:block}.player-card-stats span{font-size:10px;color:#9eb5e5;margin-top:4px}.player-card-footer{padding:12px;text-align:center;color:#a9c5ff;font-size:12px}.banner-slide{flex:0 0 86%;scroll-snap-align:center}.fee{color:#ffd65b;font-weight:bold}.nav{position:fixed;bottom:0;left:50%;transform:translateX(-50%);width:min(540px,100%);display:grid;grid-template-columns:repeat(6,1fr);background:#030a19;border-top:1px solid #2549a8;padding:7px 3px calc(7px + env(safe-area-inset-bottom));z-index:9}.nav a{text-align:center;color:#9eb5e5;font-size:10px;padding:4px 0}.nav a.active{color:#ad79ff;text-shadow:0 0 12px #7b20ff}.nav b{display:block;font-size:18px;margin-bottom:4px}.flash{padding:10px;border-radius:9px;background:#11264b;border:1px solid #365ab3;margin-bottom:10px;font-size:13px}.search{display:flex;gap:8px}.search input{flex:1;min-width:0}.pill{border:1px solid #244a99;padding:7px 11px;border-radius:20px;color:#c7d8ff;font-size:12px}.live{color:#ff5d7a;font-weight:bold}.hidden{display:none}@media(min-width:700px){.wrap{margin:20px auto;border:1px solid #1c3d8b;border-radius:18px;overflow:hidden;min-height:90vh}.top{position:relative}}
'''
BASE_HTML = r'''<!doctype html><html lang="hi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Vortex Arena</title><style>''' + STYLE + r'''</style></head><body><div class="wrap"><header class="top"><img class="logo" src="https://dummyimage.com/100x100/091b46/7c7cff.png&text=V" alt="Vortex logo"><div class="brand">VORTEX ARENA<small>ESPORTS</small></div><div class="right"><a href="/notifications">Updates</a> · <a href="/shop">Shop</a> · <a href="/social">Players</a> · <a href="/support-chat">Admin Chat</a> · <a href="/profile">Profile</a></div></header><main class="content">{% with messages=get_flashed_messages() %}{% for m in messages %}<div class="flash">{{m}}</div>{% endfor %}{% endwith %}{{body|safe}}</main>{% if user %}<nav class="nav"><a class="{{'active' if page=='home' else ''}}" href="/"><b>⌂</b>Home</a><a class="{{'active' if page=='games' else ''}}" href="/games"><b>▦</b>Games</a><a class="{{'active' if page=='tournaments' else ''}}" href="/tournaments"><b>♜</b>Match</a><a class="{{'active' if page=='live' else ''}}" href="/live"><b>◉</b>Live</a><a class="{{'active' if page=='leaderboard' else ''}}" href="/leaderboard"><b>▥</b>Result</a><a class="{{'active' if page=='settings' else ''}}" href="/settings"><b>⚙</b>Setting</a></nav>{% endif %}</div></body></html>'''
def page(body, page='home', needs_profile=False):
    user=current_user()
    if user and needs_profile and (not user['username'] or not user['game_uid']): return redirect(url_for('profile'))
    return render_template_string(BASE_HTML,body=body,user=user,page=page)

@app.route('/')
def home():
    if not current_user(): return redirect(url_for('login'))
    u=current_user()
    stat_conn=db()
    total_matches=stat_conn.execute('SELECT COUNT(*) FROM registrations WHERE user_id=? AND payment_status=\'Verified\'',(u['id'],)).fetchone()[0]
    name_keys=[(u['username'] or '').strip().lower(),(u['player_uid'] or '').strip().lower(),(u['arena_uid'] or '').strip().lower(),(u['game_uid'] or '').strip().lower()]
    name_keys=[x for x in name_keys if x]
    player_results=[]
    if name_keys:
        marks=','.join('?' for _ in name_keys)
        player_results=stat_conn.execute(f'SELECT kills,position FROM tournament_results WHERE lower(player_name) IN ({marks})',name_keys).fetchall()
    total_kills=sum(int(x['kills'] or 0) for x in player_results)
    wins=sum(1 for x in player_results if int(x['position'])==1)
    win_rate=round(wins*100/len(player_results)) if player_results else 0
    featured=stat_conn.execute("SELECT * FROM tournaments WHERE status!='Completed' ORDER BY CASE status WHEN 'Live' THEN 0 ELSE 1 END,id DESC LIMIT 1").fetchone()
    if featured:
        featured_img=html.escape(featured['image_url'] or '')
        live_badge='<span class="live-badge">LIVE</span>' if featured['status']=='Live' else ''
        home_featured=f'''<div class="hero featured-hero">{live_badge}<div class="muted">{html.escape(featured['game'])} · {html.escape(featured['status'])}</div>{('<img class="hero-banner" src="'+featured_img+'" alt="Tournament banner">') if featured_img else ''}<h2>{html.escape(featured['title'])}</h2><div>Start: {html.escape(featured['start_time'])}</div><p><a class="btn" href="/tournaments">View Tournament</a></p></div>'''
    else:
        home_featured='<div class="hero featured-hero"><h2>No tournaments yet</h2><p class="muted">Admin के Tournament जोड़ने के बाद यहाँ अपने-आप दिखेंगे।</p><a class="btn" href="/tournaments">View Matches</a></div>'
    body=f'''<div class="row"><img class="avatar" src="{u['avatar'] or 'https://dummyimage.com/160x160/101e3d/91a8ff.png&text=PLAYER'}"><div style="flex:1"><b style="font-size:18px">{u['username'] or 'Player'} ✓</b><div class="muted">UID: {u['player_uid'] or 'Add your UID'}</div><span class="pill">Player</span></div><div class="card" style="margin:0"><b>{u['rank_name'] or 'Bronze'}</b><div class="muted">{u['rank_points'] or 0} Rank Points</div><div style="color:#9d72ff">{u['arena_uid'] or ('VA-'+str(10000+u['id']))}</div></div></div>
<div class="card row"><div class="stat"><b>{total_matches}</b><span class="muted">Verified Matches</span></div><div class="stat"><b>{total_kills}</b><span class="muted">Total Kills</span></div><div class="stat"><b>{win_rate}%</b><span class="muted">Win Rate</span></div></div>
{home_featured}
<h3>Quick Access</h3><div class="quick"><a href="/games"><strong>▦</strong>Games</a><a href="/tournaments"><strong>♜</strong>Tournaments</a><a href="/live"><strong>◉</strong>Live Matches</a><a href="/leaderboard"><strong>▥</strong>Leaderboard</a><a href="/player-card"><strong>♙</strong>Player Card</a><a href="/social"><strong>♧</strong>Friends / Teams</a></div><div class="card"><div class="row between"><a href="/pops" title="POPS Report" aria-label="POPS Report" style="display:grid;place-items:center;width:58px;height:58px;border-radius:16px;background:linear-gradient(135deg,#6f1cff,#075de8);font-size:27px;border:1px solid #8e6aff">◈</a><a href="/challenges" title="Challenges" aria-label="Challenges" style="display:grid;place-items:center;width:58px;height:58px;border-radius:16px;background:linear-gradient(135deg,#00a8d6,#4430db);font-size:27px;border:1px solid #39c8ff">⚔</a><a href="/rulebook" title="Rulebook" aria-label="Rulebook" style="display:grid;place-items:center;width:58px;height:58px;border-radius:16px;background:linear-gradient(135deg,#6b7280,#25375d);font-size:27px;border:1px solid #7e9bd8">▤</a></div><p class="muted" style="margin-bottom:0">तीनों आइकन खोलकर रिपोर्ट, चैलेंज और नियम देख सकते हैं।</p></div>
<div class="card row between"><div><b>News & Updates</b><div class="muted">New tournaments and match updates</div></div><a href="/tournaments">›</a></div><a class="btn green full" href="{YOUTUBE}" target="_blank" rel="noopener">▶　Go to YouTube Live / Channel</a>'''
    try:
        banners=db().execute('SELECT * FROM banners WHERE active=1 ORDER BY id DESC LIMIT 8').fetchall()
        news=db().execute('SELECT * FROM announcements WHERE active=1 ORDER BY id DESC LIMIT 5').fetchall()
        if banners:
            body += '<h3>Featured Banners</h3><div class="banner-slider">' + ''.join(f'<a class="card banner-slide" href="{html.escape(b["link_url"] or '/tournaments')}"><img class="tourimg" src="{html.escape(b["image_url"])}" alt="Banner"><b>{html.escape(b["title"] or 'Vortex Arena')}</b></a>' for b in banners) + '</div>'
        if news:
            body += '<h3>📢 Announcements</h3>' + ''.join(f'<div class="card"><b>{html.escape(n["title"])}</b><p>{html.escape(n["message"])}</p><small class="muted">{html.escape(n["created_at"])}</small></div>' for n in news)
    except sqlite3.Error:
        pass
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
    body=f'''<h1 class="title">Player Profile</h1><div class="subtitle">Set up your player card</div><div class="card"><b>Vortex ID: {u['arena_uid'] or ('VA-'+str(10000+u['id']))}</b><p class="muted">Rank: {u['rank_name'] or 'Bronze'} · {u['rank_points'] or 0} points</p><p class="muted">Silver: 200 • Gold: 400 • Diamond: 1000 • Master: 2500 • Master Right: 3000</p></div><form method="post" enctype="multipart/form-data"><div class="field"><label>Your profile photo</label><div class="avatar-pick"><img id="avatarPreview" class="avatar" src="{avatar_src}" alt="Profile photo"><button type="button" title="Choose photo" aria-label="Choose profile photo" onclick="document.getElementById('avatarFile').click()">＋</button></div><div class="avatar-hint">फोटो बदलने के लिए गोल + आइकन दबाएँ</div><input id="avatarFile" type="file" name="avatar" accept="image/png,image/jpeg,image/webp" hidden onchange="if(this.files[0]) document.getElementById('avatarPreview').src=URL.createObjectURL(this.files[0])"></div><div class="field"><label>Player name</label><input name="username" value="{u['username']}" required placeholder="Your player name"></div><div class="field"><label>Player UID (optional)</label><input name="player_uid" value="{u['player_uid']}" placeholder="Your player ID"></div><div class="field"><label>Team name</label><input name="team_name" value="{u['team_name']}" placeholder="Your team"></div><div class="field"><label>Main game</label><select name="game">{opts}</select></div><div class="field"><label>Game UID</label><input name="game_uid" value="{u['game_uid']}" required placeholder="UID for selected game"></div><button class="btn full">Finish Profile</button></form>'''
    return page(body)
@app.route('/uploads/<path:name>')
def uploaded(name):
    from flask import send_from_directory
    return send_from_directory(UPLOADS,secure_filename(name))

@app.route('/games')
def games():
    if not current_user(): return redirect(url_for('login'))
    q=request.args.get('q','').strip().lower()
    rows=db().execute("SELECT game,MAX(image_url) image_url,MIN(entry_fee) min_fee,COUNT(*) tournament_count FROM tournaments WHERE game IS NOT NULL AND TRIM(game)!='' GROUP BY game ORDER BY game COLLATE NOCASE").fetchall()
    matches=[r for r in rows if q in r['game'].lower()]
    cards=''.join(f'''<div class="card game"><div class="game-image-wrap">{('<img src="'+html.escape(r['image_url'])+'" alt="'+html.escape(r['game'])+' banner" loading="lazy">') if r['image_url'] else '<div class="game-placeholder">'+html.escape(r['game'])+'</div>'}</div><div class="pad"><h3>{html.escape(r['game'])}</h3><div class="muted">{r['tournament_count']} tournament(s) from Admin</div><div class="row between" style="margin-top:10px"><span class="fee">Entry from ₹{int(r['min_fee'] or 0)}</span><a class="btn" href="/tournaments?game={quote(r['game'])}">View Matches</a></div></div></div>''' for r in matches)
    if not cards: cards='<div class="card">अभी कोई Admin-added game/tournament नहीं है। Admin Panel से Tournament जोड़ने पर यहाँ दिखेगा।</div>'
    body=f'''<h1 class="title">Games</h1><div class="subtitle">केवल Admin द्वारा जोड़े गए गेम</div><form class="search" method="get" action="/games"><input class="field" style="margin:0;background:#030a19;color:white;border:1px solid #2b4b98;border-radius:9px;padding:12px" name="q" value="{html.escape(q)}" placeholder="Search game name"><button class="btn">Search</button></form><p class="muted">{len(matches)} games found</p><div class="grid">{cards}</div>'''
    return page(body,'games',True)
@app.route('/tournaments')
def tournaments():
    if not current_user():return redirect(url_for('login'))
    game=request.args.get('game','').strip(); status=request.args.get('status',''); free_only=request.args.get('free','')=='1'
    sql='SELECT * FROM tournaments WHERE 1=1'; args=[]
    if game:sql+=' AND game=?';args.append(game)
    if status:sql+=' AND status=?';args.append(status)
    if free_only:sql+=' AND entry_fee=0'
    ts=db().execute(sql+' ORDER BY id',args).fetchall()
    cards=''.join(f'''<div class="card tour"><div class="tour-image-wrap">{('<span class=\"live-badge\">LIVE</span>') if t['status']=='Live' else ''}<img src="{html.escape(t['image_url'] or 'https://dummyimage.com/500x300/08152d/7c7cff.png&text=Vortex+Arena')}" alt="{html.escape(t['game'])} game"></div><div><h3>{html.escape(t['title'])}</h3><div class="fee">₹ {t['prize_pool']:,} Prize Pool</div><div class="muted">◉ {t['players']}/{int(t['slots'])*max(1,int(t['team_size'] or 4))} players · {t['slots']} team slots</div><div class="muted">{html.escape(t['map_name'] or 'Map not set')} · {html.escape(t['mode'] or 'Squad')}</div><div class="muted">Start: {html.escape(t['start_time'])}</div><div class="row between" style="margin-top:7px"><span class="muted">Entry ₹{t['entry_fee']}</span><a class="btn" href="/join/{t['id']}">Join</a></div></div></div>''' for t in ts)
    if not cards:cards='<div class="card">इस गेम के लिए अभी tournament नहीं है। Admin के द्वारा इसी डेटाबेस में मैच जोड़ने के बाद यहाँ दिखेगा।</div>'
    body=f'''<h1 class="title">Tournaments</h1><div class="subtitle">Big Prizes • Real Competition</div><div class="row" style="flex-wrap:wrap;margin:14px 0"><a class="pill" href="/tournaments">All Tournaments</a> <a class="pill" href="/tournaments?status=Upcoming">Upcoming Events</a> <a class="pill" href="/tournaments?status=Live">Live</a> <a class="pill" href="/tournaments?free=1">Free Tournaments</a> <a class="pill" href="/my-matches">My Tournaments</a></div>{cards}'''
    return page(body,'tournaments',True)
@app.route('/join/<int:tid>',methods=['GET','POST'])
def join(tid):
    u=current_user()
    if not u:return redirect(url_for('login'))
    t=db().execute('SELECT * FROM tournaments WHERE id=?',(tid,)).fetchone()
    if not t:return 'Tournament not found',404
    until=u['master_right_until'] if 'master_right_until' in u.keys() else ''
    try: master_free=bool((u['rank_name']=='Master Right') and int(u['rank_points'] or 0)>=3000 and until and datetime.strptime(until,'%Y-%m-%d %H:%M:%S')>datetime.utcnow() and int(t['entry_fee'])<=10)
    except (ValueError,TypeError): master_free=False
    if request.method=='POST':
        conn=db()
        existing=conn.execute('SELECT id FROM registrations WHERE user_id=? AND tournament_id=?',(u['id'],tid)).fetchone()
        if existing:
            flash('आप पहले ही इस tournament में join कर चुके हैं।'); return redirect(url_for('my_matches'))
        confirmed=conn.execute("SELECT COUNT(*) FROM registrations WHERE tournament_id=? AND registration_status!='Rejected'",(tid,)).fetchone()[0]
        if confirmed >= int(t['slots'])*max(1,min(4,int(t['team_size'] or 4))):
            flash('इस tournament के सभी player slots भर चुके हैं।'); return redirect(url_for('tournaments'))
        if master_free:
            try:
                conn.execute("INSERT INTO registrations(user_id,tournament_id,utr,payment_status,registration_status) VALUES(?,?,?,?,'Confirmed')",(u['id'],tid,'','Verified'))
                refresh_tournament_slots(conn,tid); conn.commit(); flash('Master Right benefit applied: entry fee waived for this tournament.'); return redirect(url_for('my_matches'))
            except sqlite3.IntegrityError:
                flash('आप पहले ही इस tournament में join कर चुके हैं।'); return redirect(url_for('my_matches'))
        utr=request.form.get('utr','').strip()
        normalized=re.sub(r'\s+','',utr).upper()
        if not re.fullmatch(r'[A-Z0-9]{12,22}',normalized) or not any(ch.isdigit() for ch in normalized):
            flash('UTR format सही नहीं लग रहा। Payment receipt वाला 12–22 अक्षर/अंक reference डालें।')
        elif db().execute('SELECT 1 FROM registrations WHERE UPPER(utr)=? LIMIT 1',(normalized,)).fetchone():
            flash('यह UTR पहले इस्तेमाल हो चुका है।')
        else:
            try:
                conn.execute("INSERT INTO registrations(user_id,tournament_id,utr,payment_status,registration_status) VALUES(?,?,?,?,'Pending')",(u['id'],tid,normalized,'Submitted for review'))
                conn.commit(); flash('UTR जमा हुआ है। Admin verification के बाद slot assign होगा।'); return redirect(url_for('my_matches'))
            except sqlite3.IntegrityError: flash('आप पहले ही इस tournament में join कर चुके हैं।')
    payable=0 if master_free else int(t['entry_fee'])
    upi=f"upi://pay?pa={quote(UPI_ID)}&pn={quote('Vortex Arena')}&am={payable}&cu=INR&tn={quote(t['title'])}"
    if master_free:
        payment_html='<div class="card"><b>Master Right Reward</b><p class="muted">आपकी 30-दिन की eligibility active है। इस ₹10 तक की entry fee वाले tournament में कोई payment नहीं लगेगा।</p><form method="post"><button class="btn full">Claim Free Entry</button></form></div>'
    else:
        payment_html=f'''<div class="card"><b>Step 1 — Pay Entry Fee</b><p class="muted">UPI app खुलेगा। पेमेंट करने से पहले नाम और amount जाँचें।</p><a class="btn green full" href="{upi}">Open UPI App</a><p class="muted">UPI ID: <b>{UPI_ID}</b></p><button class="btn secondary full" onclick="navigator.clipboard.writeText('{UPI_ID}').then(()=>alert('UPI ID copied'))">Copy UPI ID</button></div><div class="card"><b>Step 2 — Submit UTR</b><p class="muted">Payment receipt से UTR डालें। Admin verification ज़रूरी है।</p><form method="post"><div class="field"><label>UTR / UPI transaction reference</label><input name="utr" minlength="12" maxlength="22" pattern="[A-Za-z0-9]{{12,22}}" required autocomplete="off" placeholder="Paste real UTR"></div><button class="btn full">Submit & Register</button></form></div>'''
    body=f'''<h1 class="title">Register Tournament</h1><div class="card"><h3>{t['title']}</h3><div class="fee">Entry Fee: ₹{payable}{' (FREE)' if master_free else ''}</div><div class="muted">Prize pool ₹{t['prize_pool']:,} • {t['players']}/{t['slots']} players</div></div>{payment_html}'''
    return page(body,'tournaments',True)

@app.route('/my-matches')
def my_matches():
    u=current_user()
    if not u:return redirect(url_for('login'))
    rows=db().execute('SELECT r.*,t.title,t.game,t.start_time,t.end_time,t.room_id,t.room_password,t.countdown_minutes,t.status FROM registrations r JOIN tournaments t ON t.id=r.tournament_id WHERE r.user_id=? ORDER BY r.id DESC',(u['id'],)).fetchall()
    cards=''.join(f'''<div class="card"><h3>{r['title']}</h3><div class="muted">{r['game']} • {r['start_time']} – {r['end_time']}</div><p>Status: <b>{r['payment_status']}</b></p>{('<p class="muted">Match countdown: <span class="match-countdown" data-start="'+html.escape(r['start_time'])+'">'+html.escape(r['start_time'])+'</span></p>') if r['payment_status']=='Verified' else '<p class="muted">Countdown और room details payment verification के बाद दिखेंगे।</p>'}<p>Team Slot: <b>{('Slot '+str(r['slot_number'])) if r['slot_number'] else 'Payment verification / slot assignment pending'}</b></p>{('<div>Room ID: <b>'+html.escape(r['room_id'])+'</b></div><div>Room Password: <b>'+html.escape(r['room_password'])+'</b></div>') if r['room_id'] and r['payment_status']=='Verified' and room_is_released(r) else '<div class="muted">Room ID/password केवल verified players को match start time पर दिखेगा।</div>'}</div>''' for r in rows)
    body='<h1 class="title">My Matches</h1>'+ (cards or '<div class="card">अभी कोई tournament join नहीं किया।</div>')
    body += '''<script>(function(){function tick(){document.querySelectorAll('.match-countdown').forEach(function(el){var s=(el.dataset.start||'').replace(' ','T');var target=new Date(s).getTime();if(!Number.isFinite(target)){el.textContent=el.dataset.start+' (time set by admin)';return;}var diff=target-Date.now();if(diff<=0){el.textContent='Match started / start time passed';return;}var d=Math.floor(diff/86400000),h=Math.floor(diff%86400000/3600000),m=Math.floor(diff%3600000/60000),sec=Math.floor(diff%60000/1000);el.textContent=(d?d+'d ':'')+h+'h '+m+'m '+sec+'s';});}tick();setInterval(tick,1000);})();</script>'''
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
    rows=db().execute('SELECT username,team_name,game,rank_name,rank_points,arena_uid FROM users WHERE username!="" ORDER BY rank_points DESC,username LIMIT 50').fetchall()
    month_rows=db().execute("SELECT u.username,u.rank_name,COALESCE(SUM(rh.delta),0) AS month_points FROM users u LEFT JOIN rank_history rh ON rh.user_id=u.id AND strftime('%Y-%m',rh.created_at)=strftime('%Y-%m','now') WHERE u.username!='' GROUP BY u.id ORDER BY month_points DESC,u.rank_points DESC LIMIT 20").fetchall()
    body+='<h2 class="title" style="font-size:18px;margin-top:20px">Monthly Rank Points</h2>'+''.join(f'<div class="card row between"><b>{i}. {html.escape(x["username"])}</b><span>{int(x["month_points"] or 0):+d} pts · {html.escape(x["rank_name"] or "Bronze")}</span></div>' for i,x in enumerate(month_rows,1))
    body+='<h2 class="title" style="font-size:18px;margin-top:20px">Player Rank Leaderboard · Win Streak</h2>'
    for i,r in enumerate(rows,1):
        recent=db().execute('SELECT position FROM tournament_results WHERE lower(player_name)=lower(?) ORDER BY tournament_id DESC,position ASC',(r['username'],)).fetchall()
        streak=0
        for result in recent:
            if int(result['position'])==1: streak+=1
            else: break
        body+=f'<div class="card row"><b style="color:#9d7aff">#{i}</b><div style="flex:1"><b>{html.escape(r["username"])}</b><div class="muted">{html.escape(r["team_name"] or "Solo Player")} • {html.escape(r["game"] or "")} • {html.escape(r["rank_name"] or "Bronze")} • 🔥 {streak} win streak</div></div><b>{int(r["rank_points"] or 0)} pts</b></div>'
    team_rows=db().execute("""SELECT team_name,COUNT(*) AS matches, SUM(CASE WHEN team_position=1 THEN 1 ELSE 0 END) AS wins, COALESCE(SUM(score),0) AS total_score FROM tournament_results WHERE trim(COALESCE(team_name,''))!='' GROUP BY lower(team_name) ORDER BY wins DESC,total_score DESC,matches DESC LIMIT 20""").fetchall()
    body+='<h2 class="title" style="font-size:18px;margin-top:20px">Team Leaderboard</h2>'
    body+=''.join(f'<div class="card row between"><div><b>{i}. {html.escape(x["team_name"])}</b><div class="muted">{int(x["matches"] or 0)} player results · {int(x["wins"] or 0)} first-place results</div></div><b>{int(x["total_score"] or 0)} pts</b></div>' for i,x in enumerate(team_rows,1)) or '<div class="card muted">Team leaderboard के लिए अभी कोई result नहीं है।</div>'
    return page(body,'leaderboard',True)

@app.route('/rank')
def rank_page():
    if not current_user(): return redirect(url_for('login'))
    u=current_user()
    thresholds=[('Bronze',0,199),('Silver',200,399),('Gold',400,999),('Diamond',1000,2499),('Master',2500,2999),('Master Right',3000,999999999)]
    pts=max(0,int(u['rank_points'] or 0)); current='Bronze'
    for name,lo,hi in thresholds:
        if lo<=pts<=hi: current=name
    history=db().execute('SELECT delta,reason,created_at FROM rank_history WHERE user_id=? ORDER BY id DESC LIMIT 20',(u['id'],)).fetchall()
    badges=db().execute('SELECT title,created_at FROM achievements WHERE user_id=? ORDER BY id DESC',(u['id'],)).fetchall()
    body=f"<h1 class='title'>🏅 Rank & Performance</h1><div class='card'><div class='muted'>Permanent Player ID</div><h2>{u['arena_uid'] or ('VA-'+str(10000+u['id']))}</h2><h2>{current}</h2><p>{pts} Rank Points</p><p class='muted'>Silver 200 · Gold 400 · Diamond 1000 · Master 2500 · Master Right 3000+</p></div><div class='card'><h3>Master Right Reward</h3><p class='muted'>Master Right पर पहुँचने पर अधिकतम ₹10 entry fee वाले tournaments के लिए 30 दिन की free-entry eligibility होगी। Admin द्वारा सेट की गई तारीख के बाद ही यह लागू होगी।</p></div><h3>Point History</h3>"
    body += '<h3>Achievements & Medals</h3>' + (''.join(f"<div class='card'>🏅 <b>{html.escape(b['title'])}</b><div class='muted'>{b['created_at']}</div></div>" for b in badges) or '<div class="card muted">अभी कोई achievement नहीं।</div>')
    for h in history: body+=f"<div class='card'><b>{'+' if h['delta']>0 else ''}{h['delta']} points</b><div>{h['reason']}</div><div class='muted'>{h['created_at']}</div></div>"
    if not history: body+='<div class="card muted">अभी कोई point history नहीं है।</div>'
    return page(body,'leaderboard',True)

@app.route('/social',methods=['GET','POST'])
def social():
    u=current_user()
    if not u:return redirect(url_for('login'))
    c=db()
    if request.method=='POST':
        action=request.form.get('action','')
        try:
            if action=='team':
                name=request.form.get('team_name','').strip()[:60]; game=request.form.get('game','Free Fire')
                if not name: flash('Team name लिखें।')
                else:
                    c.execute('INSERT INTO teams(team_uid,name,game,leader_id) VALUES(?,?,?,?)',(f'VT-{10000+u["id"]}-{int(time.time())%100000}',name,game,u['id']))
                    tid=c.execute('SELECT last_insert_rowid()').fetchone()[0]
                    c.execute('INSERT INTO team_members(team_id,user_id,status) VALUES(?,?,?)',(tid,u['id'],'Accepted')); c.commit(); flash('Team बन गई। Team Finder में दिखेगी।')
            elif action=='join_team':
                team_id=int(request.form.get('team_id','0'))
                team=c.execute('SELECT * FROM teams WHERE id=?',(team_id,)).fetchone()
                if not team: flash('Team नहीं मिली।')
                elif team['leader_id']==u['id']: flash('यह आपकी अपनी team है।')
                elif c.execute("SELECT 1 FROM team_members WHERE team_id=? AND user_id=?",(team_id,u['id'])).fetchone(): flash('आप पहले से इस team में request/member हैं।')
                elif c.execute("SELECT COUNT(*) FROM team_members WHERE team_id=? AND status='Accepted'",(team_id,)).fetchone()[0]>=4: flash('इस team के 4 सदस्य पूरे हैं।')
                else:
                    c.execute("INSERT INTO team_members(team_id,user_id,status) VALUES(?,?,'Pending')",(team_id,u['id']))
                    c.execute('INSERT INTO user_notifications(user_id,message) VALUES(?,?)',(team['leader_id'],f'{u["username"] or u["arena_uid"]} ने {team["name"]} में join request भेजी।')); c.commit(); flash('Team join request भेज दी।')
            elif action=='team_reply':
                member_id=int(request.form.get('member_id','0')); status=request.form.get('status','Rejected')
                membership=c.execute('SELECT tm.*,t.leader_id,t.name FROM team_members tm JOIN teams t ON t.id=tm.team_id WHERE tm.id=?',(member_id,)).fetchone()
                if not membership or membership['leader_id']!=u['id'] or membership['status']!='Pending': flash('यह team request उपलब्ध नहीं है।')
                elif status=='Accepted' and c.execute("SELECT COUNT(*) FROM team_members WHERE team_id=? AND status='Accepted'",(membership['team_id'],)).fetchone()[0]>=4: flash('Team में पहले से 4 accepted सदस्य हैं।')
                else:
                    c.execute('UPDATE team_members SET status=? WHERE id=?',(status if status in ('Accepted','Rejected') else 'Rejected',member_id))
                    c.execute('INSERT INTO user_notifications(user_id,message) VALUES(?,?)',(membership['user_id'],f'Team request for {membership["name"]}: {status}.')); c.commit(); flash('Team request status update हुआ।')
            elif action=='team_message':
                team_id=int(request.form.get('team_id','0')); msg=request.form.get('message','').strip()[:1000]
                membership=c.execute("SELECT 1 FROM team_members WHERE team_id=? AND user_id=? AND status='Accepted'",(team_id,u['id'])).fetchone()
                if msg and membership:
                    c.execute('INSERT INTO messages(from_user_id,team_id,message) VALUES(?,?,?)',(u['id'],team_id,msg))
                    c.execute("INSERT INTO user_notifications(user_id,message) SELECT user_id,? FROM team_members WHERE team_id=? AND status='Accepted' AND user_id!=?",(f'{u["username"] or u["arena_uid"]} ने team chat में message भेजा।',team_id,u['id']))
                    c.commit(); flash('Team message भेज दिया।')
                else: flash('Team chat के लिए accepted member होना जरूरी है।')
            elif action=='request':
                target=int(request.form.get('to_user_id','0')); msg=request.form.get('message','').strip()[:300]
                if target==u['id']: flash('अपने आप को request नहीं भेज सकते।')
                elif not c.execute('SELECT id FROM users WHERE id=?',(target,)).fetchone(): flash('Player नहीं मिला।')
                else:
                    c.execute('INSERT INTO team_requests(from_user_id,to_user_id,message) VALUES(?,?,?)',(u['id'],target,msg)); c.execute('INSERT INTO user_notifications(user_id,message) VALUES(?,?)',(target,f'{u["username"] or u["arena_uid"]} ने Add Me request भेजी।')); c.commit(); flash('Request भेज दी गई।')
            elif action=='reply':
                rid=int(request.form.get('request_id','0')); status=request.form.get('status','Rejected')
                if status not in ('Accepted','Rejected'): status='Rejected'
                c.execute('UPDATE team_requests SET status=? WHERE id=? AND to_user_id=?',(status,rid,u['id'])); c.commit(); flash('Request status अपडेट हुआ।')
            elif action=='message':
                target=int(request.form.get('to_user_id','0')); msg=request.form.get('message','').strip()[:1000]
                if msg and target!=u['id'] and c.execute('SELECT id FROM users WHERE id=?',(target,)).fetchone():
                    c.execute('INSERT INTO messages(from_user_id,to_user_id,message) VALUES(?,?,?)',(u['id'],target,msg)); c.execute('INSERT INTO user_notifications(user_id,message) VALUES(?,?)',(target,f'{u["username"] or u["arena_uid"]} ने आपको message भेजा।')); c.commit(); flash('Message भेज दिया।')
                else: flash('सही खिलाड़ी और message लिखें।')
            elif action=='report':
                category=request.form.get('category','Other')[:60]; details=request.form.get('details','').strip()[:2000]
                if details: c.execute('INSERT INTO reports(user_id,category,details) VALUES(?,?,?)',(u['id'],category,details)); c.commit(); flash('Report support team को भेज दी गई।')
        except (ValueError,sqlite3.Error): c.rollback(); flash('Request पूरी नहीं हुई। दोबारा कोशिश करें।')
        if action=='message':
            return redirect(url_for('social',chat_with=request.form.get('to_user_id','')))
        return redirect(url_for('social'))
    players=c.execute('SELECT id,username,arena_uid,game,team_name FROM users WHERE id!=? ORDER BY username LIMIT 100',(u['id'],)).fetchall()
    reqs=c.execute('SELECT tr.*,u.username,u.arena_uid FROM team_requests tr JOIN users u ON u.id=tr.from_user_id WHERE tr.to_user_id=? ORDER BY tr.id DESC LIMIT 20',(u['id'],)).fetchall()
    teams=c.execute('SELECT t.*,u.username,(SELECT COUNT(*) FROM team_members tm WHERE tm.team_id=t.id AND tm.status=\'Accepted\') AS members FROM teams t JOIN users u ON u.id=t.leader_id ORDER BY t.id DESC LIMIT 50').fetchall()
    body='<h1 class="title">Squad Finder & Social</h1><div class="card"><h3>Create Team</h3><form method="post"><input type="hidden" name="action" value="team"><label>Team Name</label><input name="team_name" required maxlength="60"><label>Game</label><select name="game"><option>Free Fire</option><option>BGMI</option></select><button class="btn">Create Team</button></form></div><h3>Teams</h3>'
    for t in teams:
        body+=f'<div class="card"><b>{html.escape(t["name"])}</b><p class="muted">{html.escape(t["team_uid"] or "Team")} · {html.escape(t["game"])} · {t["members"]}/4 members · Leader {html.escape(t["username"] or "Player")}</p>'
        member=c.execute('SELECT * FROM team_members WHERE team_id=? AND user_id=?',(t['id'],u['id'])).fetchone()
        if not member and t['members']<4 and t['leader_id']!=u['id']:
            body+=f'<form method="post"><input type="hidden" name="action" value="join_team"><input type="hidden" name="team_id" value="{t["id"]}"><button class="btn">Request to Join</button></form>'
        elif member and member['status']=='Pending': body+='<span class="pill">Join request pending</span>'
        elif member and member['status']=='Accepted':
            body+=f'<form method="post"><input type="hidden" name="action" value="team_message"><input type="hidden" name="team_id" value="{t["id"]}"><input name="message" maxlength="1000" placeholder="Message team" required><button class="btn">Send to Team</button></form>'
            team_msgs=c.execute('SELECT m.*,u.username FROM messages m JOIN users u ON u.id=m.from_user_id WHERE m.team_id=? ORDER BY m.id DESC LIMIT 10',(t['id'],)).fetchall()
            body+=''.join(f'<p><b>{html.escape(m["username"] or "Player")}:</b> {html.escape(m["message"])}</p>' for m in reversed(team_msgs))
        body+='</div>'
    if not teams: body+='<div class="card">अभी कोई team नहीं।</div>'
    team_reqs=c.execute("SELECT tm.id,tm.team_id,tm.user_id,tm.created_at,u.username,t.name FROM team_members tm JOIN teams t ON t.id=tm.team_id JOIN users u ON u.id=tm.user_id WHERE t.leader_id=? AND tm.status='Pending' ORDER BY tm.id DESC",(u['id'],)).fetchall()
    body+='<h3>Team Join Requests</h3>'
    for q in team_reqs:
        body+=f'<div class="card"><b>{html.escape(q["username"] or "Player")}</b> wants to join {html.escape(q["name"])}<form method="post"><input type="hidden" name="action" value="team_reply"><input type="hidden" name="member_id" value="{q["id"]}"><button name="status" value="Accepted">Accept</button> <button class="secondary" name="status" value="Rejected">Reject</button></form></div>'
    body+='<h3>Players · Add Me / Message</h3>'
    for p in players:
        body+=f'<div class="card"><b>{html.escape(p["username"] or "Player")}</b><div class="muted">{html.escape(p["arena_uid"] or "")} · {html.escape(p["game"] or "")}</div><form method="post"><input type="hidden" name="action" value="request"><input type="hidden" name="to_user_id" value="{p["id"]}"><input name="message" maxlength="300" placeholder="Request message"><button class="btn">Add Me</button></form><form method="post"><input type="hidden" name="action" value="message"><input type="hidden" name="to_user_id" value="{p["id"]}"><input name="message" maxlength="1000" placeholder="Message"><button class="btn secondary">Send Message</button></form><a class="btn secondary full" href="/social?chat_with={p['id']}">Open Chat / Reply</a></div>'
    inbox=c.execute('''SELECT m.*,u.username AS sender,u.id AS sender_id FROM messages m JOIN users u ON u.id=m.from_user_id
        WHERE m.to_user_id=? ORDER BY m.id DESC LIMIT 30''',(u['id'],)).fetchall()
    conversations=c.execute('''SELECT u.id,u.username,u.arena_uid,MAX(m.id) last_id,
        SUM(CASE WHEN m.to_user_id=? AND m.seen=0 THEN 1 ELSE 0 END) unread
        FROM messages m JOIN users u ON u.id=CASE WHEN m.from_user_id=? THEN m.to_user_id ELSE m.from_user_id END
        WHERE (m.from_user_id=? OR m.to_user_id=?) AND u.id IS NOT NULL
        GROUP BY u.id,u.username,u.arena_uid ORDER BY MAX(m.id) DESC LIMIT 50''',(u['id'],u['id'],u['id'],u['id'])).fetchall()
    body+='<h3>Inbox · Player Chats</h3>'
    body+=''.join(f'<div class="card row between"><div><b>{html.escape(x["username"] or "Player")}</b><div class="muted">{html.escape(x["arena_uid"] or "") } · Unread: {int(x["unread"] or 0)}</div></div><a class="btn" href="/social?chat_with={x["id"]}">Open Chat</a></div>' for x in conversations) or '<div class="card muted">अभी कोई direct message नहीं है।</div>'
    chat_with=request.args.get('chat_with','')
    if chat_with.isdigit():
        target_id=int(chat_with)
        target_user=c.execute('SELECT id,username,arena_uid FROM users WHERE id=? AND id!=?',(target_id,u['id'])).fetchone()
        if target_user:
            c.execute('UPDATE messages SET seen=1 WHERE from_user_id=? AND to_user_id=?',(target_id,u['id'])); c.commit()
            thread=c.execute('''SELECT m.*,u.username AS sender FROM messages m JOIN users u ON u.id=m.from_user_id
                WHERE (m.from_user_id=? AND m.to_user_id=?) OR (m.from_user_id=? AND m.to_user_id=?) ORDER BY m.id ASC LIMIT 100''',(u['id'],target_id,target_id,u['id'])).fetchall()
            body+=f'<div class="card"><h3>Chat with {html.escape(target_user["username"] or "Player")}</h3><div class="muted">{html.escape(target_user["arena_uid"] or "")}</div>'
            body+=''.join(f'<p><b>{html.escape(m["sender"] or "Player")}:</b> {html.escape(m["message"]) }<br><small class="muted">{html.escape(m["created_at"])}</small></p>' for m in thread)
            body+=f'<form method="post"><input type="hidden" name="action" value="message"><input type="hidden" name="to_user_id" value="{target_id}"><label>Reply</label><textarea name="message" required maxlength="1000" placeholder="Type your message..."></textarea><button class="btn full">Send Reply</button></form></div>'
    body+='<h3>Incoming Requests</h3>'
    for q in reqs:
        body+=f'<div class="card"><b>{html.escape(q["username"] or "Player")}</b> · {html.escape(q["message"] or "Add Me") } <span class="pill">{q["status"]}</span>'
        if q['status']=='Pending': body+=f'<form method="post"><input type="hidden" name="action" value="reply"><input type="hidden" name="request_id" value="{q["id"]}"><button name="status" value="Accepted">Accept</button> <button class="secondary" name="status" value="Rejected">Reject</button></form>'
        body+='</div>'
    body+='<div class="card"><h3>Report / Help</h3><form method="post"><input type="hidden" name="action" value="report"><label>Category</label><select name="category"><option>Payment</option><option>Wrong Result</option><option>Player Behaviour</option><option>Technical Issue</option><option>Other</option></select><label>Details</label><textarea name="details" required maxlength="2000"></textarea><button class="btn">Submit Report</button></form></div>'
    body+=f'<div class="card"><h3>Support Us</h3><a class="btn" href="/support-chat">Chat with Admin</a> <a class="btn green" href="{WHATSAPP_SUPPORT}" target="_blank" rel="noopener">WhatsApp Support</a><p class="muted">Contact / UPI number: <b>{CONTACT_PHONE}</b></p><a class="btn secondary full" href="{DISCORD_URL}" target="_blank" rel="noopener">Join Vortex Arena Discord</a><p class="muted">यह Vortex Arena का Discord server invite link है।</p></div>'
    return page(body,'settings',True)

@app.route('/player-card',methods=['GET','POST'])
def player_card():
    u=current_user()
    if not u: return redirect(url_for('login'))
    c=db()
    if request.method=='POST':
        country=request.form.get('player_country','India').strip()[:50]; theme=request.form.get('player_theme','Neon Blue').strip()[:50]; bio=request.form.get('player_bio','').strip()[:180]
        c.execute('UPDATE users SET player_country=?,player_theme=?,player_bio=? WHERE id=?',(country,theme,bio,u['id'])); c.commit(); flash('Player Card updated.'); return redirect(url_for('player_card'))
    u=c.execute('SELECT * FROM users WHERE id=?',(u['id'],)).fetchone()
    keys=[(u['username'] or '').strip().lower(),(u['player_uid'] or '').strip().lower(),(u['arena_uid'] or '').strip().lower(),(u['game_uid'] or '').strip().lower()]; keys=[x for x in keys if x]
    result_rows=[]
    if keys:
        marks=','.join('?' for _ in keys); result_rows=c.execute(f'SELECT * FROM tournament_results WHERE lower(player_name) IN ({marks}) ORDER BY id DESC',keys).fetchall()
    wins=sum(1 for x in result_rows if int(x['position'] or 0)==1); kills=sum(int(x['kills'] or 0) for x in result_rows)
    avatar=html.escape(u['avatar'] or ''); name=html.escape(u['username'] or 'Player')
    theme_color='#174bd6' if (u['player_theme'] or 'Neon Blue')=='Neon Blue' else '#7025d9' if u['player_theme']=='Neon Purple' else '#b82a45'
    body=f'''<h1 class="title">Vortex Player Card</h1><div class="player-card" style="border-color:{theme_color}"><div class="player-card-head"><div class="player-card-brand">VORTEX ARENA</div><div class="player-card-tag">PLAYER PROFILE</div></div><div class="player-card-main"><img class="player-card-avatar" src="{avatar or 'https://dummyimage.com/200x200/101e3d/91a8ff.png&text=PLAYER'}" alt="Player avatar"><div><h2>{name}</h2><div class="muted">UID: {html.escape(u['arena_uid'] or '—')}</div><div class="player-card-rank">{html.escape(u['rank_name'] or 'Bronze')}</div></div></div><div class="player-card-stats"><div><b>{len(result_rows)}</b><span>Matches</span></div><div><b>{wins}</b><span>Wins</span></div><div><b>{kills}</b><span>Kills</span></div><div><b>{int(u['rank_points'] or 0)}</b><span>Points</span></div></div><div class="player-card-footer">{html.escape(u['game'] or 'Game not set')} · {html.escape(u['team_name'] or 'No Team')} · {html.escape(u['player_country'] or 'India')}<br>{html.escape(u['player_bio'] or '')}</div></div><div class="card"><h3>Edit Player Card</h3><form method="post"><div class="field"><label>Country</label><input name="player_country" value="{html.escape(u['player_country'] or 'India')}" maxlength="50"></div><div class="field"><label>Card Theme</label><select name="player_theme"><option {'selected' if u['player_theme']=='Neon Blue' else ''}>Neon Blue</option><option {'selected' if u['player_theme']=='Neon Purple' else ''}>Neon Purple</option><option {'selected' if u['player_theme']=='Crimson Red' else ''}>Crimson Red</option></select></div><div class="field"><label>Bio</label><input name="player_bio" value="{html.escape(u['player_bio'] or '')}" maxlength="180"></div><button class="btn full">Save Player Card</button></form></div><a class="btn full" href="/profile">Edit Player Profile</a><a class="btn secondary full" href="/social">Friends & Teams</a>'''
    return page(body,'settings',True)

@app.route('/support-chat',methods=['GET','POST'])
def support_chat():
    u=current_user()
    if not u:return redirect(url_for('login'))
    c=db()
    if request.method=='POST':
        msg=request.form.get('message','').strip()[:2000]
        if msg:
            c.execute("INSERT INTO support_messages(user_id,sender_role,sender_id,message) VALUES(?,'user',?,?)",(u['id'],u['id'],msg))
            c.execute('INSERT INTO admin_audit(admin_name,action,details) VALUES(?,?,?)',('System','Player contacted support',f'user_id={u["id"]}'))
            c.commit(); flash('आपका मैसेज Admin Support Inbox में भेज दिया गया।')
        return redirect(url_for('support_chat'))
    c.execute("UPDATE support_messages SET seen=1 WHERE user_id=? AND sender_role='admin'",(u['id'],)); c.commit()
    rows=c.execute('SELECT * FROM support_messages WHERE user_id=? ORDER BY id DESC LIMIT 100',(u['id'],)).fetchall()
    body='<h1 class="title">Admin Support Chat</h1><p class="muted">यहाँ अपना सवाल या dispute सीधे Admin को भेजें। Admin के जवाब इसी चैट में दिखेंगे।</p><div class="card"><form method="post"><label>Message to Admin</label><textarea name="message" required maxlength="2000" placeholder="अपनी समस्या लिखें..."></textarea><button class="btn full">Send to Admin</button></form></div>'
    for m in reversed(rows):
        who='You' if m['sender_role']=='user' else 'Vortex Arena Admin'
        body+=f'<div class="card"><b>{who}</b><p>{html.escape(m["message"])}</p><small class="muted">{html.escape(m["created_at"])}</small></div>'
    if not rows: body+='<div class="card muted">अभी कोई चैट नहीं है। ऊपर से Admin को पहला message भेजें।</div>'
    body+=f'<div class="card"><a class="btn green" href="{WHATSAPP_SUPPORT}" target="_blank" rel="noopener">WhatsApp Support</a> <a class="btn secondary" href="{DISCORD_URL}" target="_blank" rel="noopener">Discord Server</a></div>'
    return page(body,'settings',True)

@app.route('/notifications')
def notifications():
    u=current_user()
    if not u:return redirect(url_for('login'))
    c=db(); rows=c.execute('SELECT * FROM user_notifications WHERE user_id=? ORDER BY id DESC LIMIT 50',(u['id'],)).fetchall(); c.execute('UPDATE user_notifications SET seen=1 WHERE user_id=?',(u['id'],)); c.commit()
    body='<h1 class="title">Notifications</h1>'+''.join(f'<div class="card"><b>{html.escape(n["message"])}</b><div class="muted">{n["created_at"]}</div></div>' for n in rows)
    return page(body,'settings',True)

@app.route('/settings')
def settings():
    u=current_user()
    if not u:return redirect(url_for('login'))
    body=f'''<h1 class="title">Settings</h1><div class="card"><b>Account</b><p class="muted">{u['email']}</p><a class="btn secondary" href="/profile">Edit Profile</a></div><div class="card"><b>Social, Squad & Help</b><p><a class="btn" href="/social">Squad Finder / Player Chat</a> <a class="btn secondary" href="/support-chat">Chat with Admin</a> <a class="btn secondary" href="/notifications">Notifications</a></p></div><div class="card"><b>Support & Channel</b><p class="muted">Contact / UPI number: {CONTACT_PHONE}</p><a class="btn green" href="{WHATSAPP_SUPPORT}" target="_blank" rel="noopener">WhatsApp Support</a><a class="btn secondary full" href="{DISCORD_URL}" target="_blank" rel="noopener">Join Discord</a><a class="btn green full" href="{YOUTUBE}" target="_blank" rel="noopener">▶ Go to YouTube</a></div><a class="btn full" href="/logout">Logout</a>'''
    return page(body,'settings',True)

# Initialize schema on import too, so WSGI deployments also prepare tables.

@app.route('/pops', methods=['GET','POST'])
def pops_reports():
    u=current_user()
    if not u: return redirect(url_for('login'))
    c=db()
    c.execute("CREATE TABLE IF NOT EXISTS pops_reports(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER NOT NULL,category TEXT NOT NULL,details TEXT NOT NULL,evidence_url TEXT DEFAULT '',status TEXT DEFAULT 'Sent to Host',created_at TEXT DEFAULT CURRENT_TIMESTAMP)")
    cols=[x['name'] for x in c.execute('PRAGMA table_info(pops_reports)').fetchall()]
    for col,definition in [('reporter_uid',"TEXT DEFAULT ''"),('reported_uid',"TEXT DEFAULT ''"),('video_path',"TEXT DEFAULT ''"),('admin_note',"TEXT DEFAULT ''")]:
        if col not in cols: c.execute(f'ALTER TABLE pops_reports ADD COLUMN {col} {definition}')
    c.commit()
    if request.method=='POST':
        category=request.form.get('category','Gameplay concern').strip()[:80]
        details=request.form.get('details','').strip()[:2000]
        reporter_uid=request.form.get('reporter_uid','').strip()[:100]
        reported_uid=request.form.get('reported_uid','').strip()[:100]
        evidence=request.form.get('evidence_url','').strip()[:500]
        f=request.files.get('evidence_video')
        video_path=''
        if f and f.filename:
            ext=Path(secure_filename(f.filename)).suffix.lower()
            if ext not in ('.mp4','.webm','.mov','.m4v'):
                flash('Video MP4, WEBM या MOV format में अपलोड करें।'); return redirect(url_for('pops_reports'))
            name=f'pops_{u["id"]}_{int(time.time())}{ext}'
            f.save(UPLOADS/name); video_path='/uploads/'+name
        if details and reporter_uid and reported_uid:
            c.execute('INSERT INTO pops_reports(user_id,category,details,evidence_url,reporter_uid,reported_uid,video_path) VALUES(?,?,?,?,?,?,?)',(u['id'],category,details,evidence,reporter_uid,reported_uid,video_path)); c.commit()
            flash('रिपोर्ट Admin review queue में भेज दी गई है। वीडियो दोबारा भेजने से बचने के लिए पेज redirect किया गया है।')
        else: flash('अपना UID, दूसरे खिलाड़ी का UID और घटना का विवरण भरें।')
        return redirect(url_for('pops_reports'))
    rows=c.execute('SELECT * FROM pops_reports WHERE user_id=? ORDER BY id DESC',(u['id'],)).fetchall()
    body='<h1 class="title">POPS</h1><p class="muted">संदिग्ध हैक, गलत व्यवहार या UID misuse की रिपोर्ट करें। वीडियो एक बार अपलोड होगा; Admin जाँच के बाद स्थिति अपडेट करेगा।</p><div class="card"><form method="post" enctype="multipart/form-data"><div class="field"><label>Report category</label><select name="category"><option>Suspected hack / teleport</option><option>Auto-aim / unfair play</option><option>Admin conduct</option><option>False report / UID misuse</option><option>Other</option></select></div><div class="field"><label>आपका UID</label><input name="reporter_uid" required maxlength="100" placeholder="अपना Vortex / Game UID"></div><div class="field"><label>दूसरे खिलाड़ी का UID</label><input name="reported_uid" required maxlength="100" placeholder="जिसकी रिपोर्ट करनी है"></div><div class="field"><label>क्या हुआ? पूरा विवरण</label><textarea name="details" required maxlength="2000" placeholder="मैच, समय और घटना बताएं"></textarea></div><div class="field"><label>वीडियो सबूत (MP4 / WEBM / MOV, max 50 MB)</label><input type="file" name="evidence_video" accept="video/mp4,video/webm,video/quicktime,video/x-m4v"></div><div class="field"><label>या वीडियो लिंक (optional)</label><input name="evidence_url" type="url" maxlength="500" placeholder="https://..."></div><button class="btn full">Send to Admin</button></form></div>'
    for r in rows:
        video=(f'<p><a class="btn secondary" href="{html.escape(r["video_path"])}" target="_blank">देखें: वीडियो सबूत</a></p>' if r['video_path'] else '')
        body+=f'<div class="card"><b>{html.escape(r["category"])}</b><p>Reported UID: {html.escape(r["reported_uid"] or "—")}</p><p>{html.escape(r["details"])}</p>{video}<span class="pill">{html.escape(r["status"])}</span><p class="muted">{html.escape(r["created_at"])}</p></div>'
    return page(body,'home',True)

@app.route('/rulebook')
def rulebook():
    u=current_user()
    if not u: return redirect(url_for('login'))
    rules=[('Rule 1 — Fair Play','Hack, teleport, auto-aim, scripts या किसी भी exploit का इस्तेमाल प्रतिबंधित है।'),('Rule 4 — Account Safety','अपना UID सही रखें और किसी दूसरे खिलाड़ी का UID बनकर दावा न करें।'),('Rule 5 — Match Conduct','मैच में टीम और टूर्नामेंट के नियमों का पालन करें।'),('Rule 6 — Evidence','रिपोर्ट में मूल वीडियो/रिकॉर्डिंग और घटना का समय दें; एडिट किया हुआ क्लिप संदर्भ के साथ दें।'),('Rule 7 — Reports','जानबूझकर गलत रिपोर्ट या नकली सबूत पर कार्रवाई हो सकती है; आरोप साबित न होना अपने-आप झूठी रिपोर्ट नहीं है।'),('Rule 14 — Evidence Verification','Admin उपलब्ध वीडियो, UID और मैच रिकॉर्ड जाँचकर स्थिति अपडेट करेगा।'),('Rule 62 — Admin Conflict','यदि रिपोर्ट Admin के विरुद्ध है, तो उसे Host review के लिए भेजा जाए; संबंधित Admin अकेले अंतिम निर्णय न करे।'),('Rule 76 — Suspected Hacks','संदिग्ध hack को POPS में UID, विवरण और वीडियो के साथ रिपोर्ट करें; खुद से प्रतिशोध न लें।'),('Rule 81 — Community Vote','24 घंटे बाद वोट/समुदाय प्रतिक्रिया ली जा सकती है, लेकिन अंतिम निर्णय सबूत देखकर Admin/Host करेगा।'),('Rule 96 — Privacy','रिपोर्ट में निजी जानकारी, पासवर्ड या भुगतान गोपनीय जानकारी साझा न करें।'),('Rule 123 — Appeal','गलत UID या रिपोर्ट के गलत वर्गीकरण पर सबूत सहित Admin/Host से appeal करें।'),('Rule 126 — Final Review','सभी रिपोर्टों की स्थिति और निर्णय कारण सहित उपलब्ध होने पर अपडेट किया जाएगा।'),('Challenges','केवल Admin द्वारा प्रकाशित सक्रिय challenges आधिकारिक हैं; eligibility और reward विवरण पढ़ें।'),('Match Results','मैच परिणाम और रैंकिंग उपलब्ध सत्यापित रिकॉर्ड के आधार पर अपडेट होंगे।')]
    body='<h1 class="title">Rulebook</h1><p class="muted">Vortex Arena के सभी खिलाड़ियों के लिए नियम</p>'
    for title,desc in rules: body+=f'<div class="card"><h3>{html.escape(title)}</h3><p>{html.escape(desc)}</p></div>'
    body+='<a class="btn full" href="/pops">POPS Report</a><a class="btn secondary full" href="/challenges">Challenges</a>'
    return page(body,'home',True)

@app.route('/challenges', methods=['GET','POST'])
def user_challenges():
    u=current_user()
    if not u: return redirect(url_for('login'))
    c=db()
    c.execute("CREATE TABLE IF NOT EXISTS arena_challenges(id INTEGER PRIMARY KEY AUTOINCREMENT,title TEXT NOT NULL,description TEXT DEFAULT '',game TEXT DEFAULT 'All games',starts_at TEXT DEFAULT '',ends_at TEXT DEFAULT '',active INTEGER DEFAULT 1,created_at TEXT DEFAULT CURRENT_TIMESTAMP)")
    c.execute("CREATE TABLE IF NOT EXISTS challenge_entries(id INTEGER PRIMARY KEY AUTOINCREMENT,challenge_id INTEGER NOT NULL,user_id INTEGER NOT NULL,player_name TEXT NOT NULL,game_uid TEXT NOT NULL,player_card_id TEXT DEFAULT '',created_at TEXT DEFAULT CURRENT_TIMESTAMP,UNIQUE(challenge_id,user_id))")
    if request.method=='POST':
        cid=request.form.get('challenge_id',''); pname=request.form.get('player_name','').strip()[:80]; game_uid=request.form.get('game_uid','').strip()[:100]; card_id=request.form.get('player_card_id','').strip()[:100]
        ch=c.execute('SELECT * FROM arena_challenges WHERE id=? AND active=1',(int(cid),)).fetchone() if cid.isdigit() else None
        if not ch: flash('यह Challenge अभी उपलब्ध नहीं है।')
        elif not pname or not game_uid or not card_id: flash('अपना नाम, Game UID और Player Card चुनना जरूरी है।')
        else:
            try:
                c.execute('INSERT INTO challenge_entries(challenge_id,user_id,player_name,game_uid,player_card_id) VALUES(?,?,?,?,?)',(int(cid),u['id'],pname,game_uid,card_id)); c.commit(); flash('आप Challenge में शामिल हो गए। Admin की manual verification की जरूरत नहीं है।')
            except sqlite3.IntegrityError: flash('आप पहले ही इस Challenge में शामिल हैं।')
        return redirect(url_for('user_challenges'))
    rows=c.execute('SELECT * FROM arena_challenges WHERE active=1 ORDER BY id DESC').fetchall()
    entries=c.execute('SELECT challenge_id,COUNT(*) n FROM challenge_entries GROUP BY challenge_id').fetchall(); counts={int(x['challenge_id']):int(x['n']) for x in entries}
    # Last seven days of the current user's challenge activity
    daily=c.execute("SELECT date(created_at) d,COUNT(*) n FROM challenge_entries WHERE user_id=? AND datetime(created_at)>=datetime('now','-6 days') GROUP BY date(created_at) ORDER BY d",(u['id'],)).fetchall(); daymap={x['d']:int(x['n']) for x in daily}
    from datetime import date,timedelta
    graph=''.join(f'<div style="flex:1;text-align:center"><div style="height:{max(5,daymap.get((date.today()-timedelta(days=i)).isoformat(),0)*22)}px;background:linear-gradient(#31c8ff,#762bff);border-radius:6px 6px 0 0;margin-top:auto"></div><small>{(date.today()-timedelta(days=i)).strftime("%a")}</small></div>' for i in reversed(range(7)))
    body='<h1 class="title">Challenges</h1><p class="muted">Admin द्वारा प्रकाशित सक्रिय challenges में शामिल हों। नाम, Game UID और अपना Player Card चुनें; entry सीधे सेव होगी।</p>'
    body+=f'<div class="card"><h3>आपकी 7-दिन की Challenge Activity</h3><div style="height:95px;display:flex;align-items:end;gap:8px;padding-top:8px">{graph}</div><p class="muted">यह ग्राफ आपके पिछले सात दिनों की challenge entries दिखाता है; मैच स्कोर तभी दिखेगा जब मैच रिज़ल्ट रिकॉर्ड उपलब्ध होगा।</p></div>'
    for r in rows:
        joined=c.execute('SELECT id FROM challenge_entries WHERE challenge_id=? AND user_id=?',(r['id'],u['id'])).fetchone()
        body+=f'<div class="card"><h3>{html.escape(r["title"])}</h3><p>{html.escape(r["description"] or "")}</p><span class="pill">{html.escape(r["game"] or "All games")}</span> <span class="pill">{counts.get(int(r["id"]),0)} joined</span>'
        if joined: body+='<p class="pill">You joined this challenge</p>'
        else:
            body+=f'''<form method="post"><input type="hidden" name="challenge_id" value="{r['id']}"><div class="field"><label>आपका नाम</label><input name="player_name" value="{html.escape(u['username'] or '',quote=True)}" required maxlength="80"></div><div class="field"><label>Game UID</label><input name="game_uid" value="{html.escape(u['game_uid'] or '',quote=True)}" required maxlength="100" placeholder="अपनी Free Fire / game UID"></div><div class="field"><label>Player Card चुनें</label><select name="player_card_id" required><option value="">अपना Player Card चुनें</option><option value="VA-{10000+int(u['id'])}">Vortex Player Card · {html.escape(u['arena_uid'] or ('VA-'+str(10000+int(u['id']))))}</option></select></div><button class="btn full">Join Challenge</button></form>'''
        body+='</div>'
    if not rows: body+='<div class="card">अभी कोई active challenge नहीं है। Admin के publish करने पर यहाँ दिखाई देगा।</div>'
    body+='<a class="btn secondary full" href="/player-card">Open / Edit Player Card</a><a class="btn secondary full" href="/rulebook">Rulebook</a>'
    return page(body,'settings',True)


# Additive Shop / currency / equipped-card system (keeps all existing data).
def ensure_shop_schema():
    with sqlite3.connect(DB) as c:
        cols=[r[1] for r in c.execute('PRAGMA table_info(users)')]
        for col,definition in [('coins','INTEGER DEFAULT 0'),('diamonds','INTEGER DEFAULT 0'),('equipped_card_id','INTEGER')]:
            if col not in cols: c.execute(f'ALTER TABLE users ADD COLUMN {col} {definition}')
        c.execute("CREATE TABLE IF NOT EXISTS shop_items(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL,item_type TEXT DEFAULT 'Cosmetic',description TEXT DEFAULT '',image_url TEXT DEFAULT '',price INTEGER DEFAULT 0,currency TEXT DEFAULT 'Points',duration_days INTEGER DEFAULT 0,stock INTEGER DEFAULT -1,active INTEGER DEFAULT 1,created_at TEXT DEFAULT CURRENT_TIMESTAMP)")
        c.execute("CREATE TABLE IF NOT EXISTS shop_inventory(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER NOT NULL,item_id INTEGER NOT NULL,quantity INTEGER DEFAULT 1,expires_at TEXT DEFAULT '',created_at TEXT DEFAULT CURRENT_TIMESTAMP,UNIQUE(user_id,item_id))")
        c.execute("CREATE TABLE IF NOT EXISTS shop_ledger(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER NOT NULL,currency TEXT NOT NULL,delta INTEGER NOT NULL,reason TEXT NOT NULL,created_at TEXT DEFAULT CURRENT_TIMESTAMP)")
        c.execute("CREATE TABLE IF NOT EXISTS spin_history(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER NOT NULL,cost INTEGER DEFAULT 500,reward_type TEXT NOT NULL,reward_amount INTEGER DEFAULT 0,reward_label TEXT NOT NULL,created_at TEXT DEFAULT CURRENT_TIMESTAMP)")
        c.execute("CREATE TABLE IF NOT EXISTS spin_rewards(id INTEGER PRIMARY KEY AUTOINCREMENT,label TEXT NOT NULL,reward_type TEXT NOT NULL,amount INTEGER DEFAULT 0,weight INTEGER DEFAULT 1,active INTEGER DEFAULT 1)")
        c.execute("CREATE TABLE IF NOT EXISTS equipped_cards(user_id INTEGER PRIMARY KEY,item_id INTEGER NOT NULL)")
        if c.execute('SELECT COUNT(*) FROM spin_rewards').fetchone()[0]==0:
            c.executemany('INSERT INTO spin_rewards(label,reward_type,amount,weight,active) VALUES(?,?,?,?,1)', [('10 Diamonds','diamonds',10,25),('25 Diamonds','diamonds',25,10),('100 Diamonds','diamonds',100,3),('1,000 Points','points',1000,8),('50 Coins','coins',50,20),('Player Card','item',0,5),('Better luck next time','nothing',0,29)])
        c.commit()

@app.route('/shop', methods=['GET','POST'])
def shop():
    u=current_user()
    if not u: return redirect(url_for('login'))
    c=db()
    if request.method=='POST':
        action=request.form.get('action','buy')
        if action=='spin':
            u=c.execute('SELECT * FROM users WHERE id=?',(u['id'],)).fetchone()
            if int(u['coins'] or 0)<500: flash('एक Spin के लिए 500 Coins चाहिए।')
            else:
                rewards=c.execute('SELECT * FROM spin_rewards WHERE active=1 AND weight>0').fetchall()
                import random
                total=sum(int(x['weight']) for x in rewards)
                pick=random.randint(1,max(1,total)); chosen=rewards[-1]
                for reward in rewards:
                    pick-=int(reward['weight'])
                    if pick<=0: chosen=reward; break
                c.execute('UPDATE users SET coins=coins-500 WHERE id=? AND coins>=500',(u['id'],))
                if c.execute('SELECT changes()').fetchone()[0]:
                    typ=chosen['reward_type']; amount=int(chosen['amount'] or 0); label=chosen['label']
                    if typ=='points': c.execute('UPDATE users SET rank_points=rank_points+? WHERE id=?',(amount,u['id']))
                    elif typ=='coins': c.execute('UPDATE users SET coins=coins+? WHERE id=?',(amount,u['id']))
                    elif typ=='diamonds': c.execute('UPDATE users SET diamonds=diamonds+? WHERE id=?',(amount,u['id']))
                    elif typ=='item':
                        item=c.execute("SELECT id FROM shop_items WHERE active=1 AND item_type='Player Card' ORDER BY RANDOM() LIMIT 1").fetchone()
                        if item:
                            c.execute('INSERT OR IGNORE INTO shop_inventory(user_id,item_id) VALUES(?,?)',(u['id'],item['id']))
                            label='Player Card unlocked'
                        else: typ='coins'; amount=100; label='100 Coins (card stock unavailable)'; c.execute('UPDATE users SET coins=coins+100 WHERE id=?',(u['id'],))
                    c.execute('INSERT INTO shop_ledger(user_id,currency,delta,reason) VALUES(?,?,?,?)',(u['id'],'Coins',-500,'Lucky Spin'))
                    c.execute('INSERT INTO spin_history(user_id,cost,reward_type,reward_amount,reward_label) VALUES(?,?,?,?,?)',(u['id'],500,typ,amount,label))
                    c.commit(); flash('Lucky Spin result: '+label)
        elif action=='buy':
            try:
                item_id=int(request.form.get('item_id','0')); item=c.execute('SELECT * FROM shop_items WHERE id=? AND active=1',(item_id,)).fetchone()
                if not item: raise ValueError('यह आइटम उपलब्ध नहीं है।')
                if item['stock']==0: raise ValueError('यह आइटम Sold Out है।')
                owned=c.execute('SELECT id FROM shop_inventory WHERE user_id=? AND item_id=?',(u['id'],item_id)).fetchone()
                if owned: raise ValueError('यह आइटम पहले से Inventory में है।')
                currency=item['currency']; price=int(item['price']); col={'Points':'rank_points','Coins':'coins','Diamonds':'diamonds'}.get(currency)
                if not col: raise ValueError('इस आइटम की Currency सेटिंग गलत है।')
                fresh=c.execute(f'SELECT {col} FROM users WHERE id=?',(u['id'],)).fetchone()
                if int(fresh[col] or 0)<price: raise ValueError('आपके पास पर्याप्त '+currency+' नहीं हैं।')
                c.execute(f'UPDATE users SET {col}={col}-? WHERE id=? AND {col}>=?',(price,u['id'],price))
                if c.execute('SELECT changes()').fetchone()[0]!=1: raise ValueError('Balance अपडेट नहीं हुआ।')
                expires=''
                if int(item['duration_days'] or 0)>0: expires=(datetime.now()+timedelta(days=int(item['duration_days']))).isoformat(timespec='seconds')
                c.execute('INSERT INTO shop_inventory(user_id,item_id,expires_at) VALUES(?,?,?)',(u['id'],item_id,expires))
                if int(item['stock'])>0: c.execute('UPDATE shop_items SET stock=stock-1 WHERE id=?',(item_id,))
                c.execute('INSERT INTO shop_ledger(user_id,currency,delta,reason) VALUES(?,?,?,?)',(u['id'],currency,-price,'Shop purchase: '+item['name']))
                c.commit(); flash('आइटम खरीदा गया। Inventory में जाकर equip करें।')
            except (ValueError,sqlite3.Error) as e: c.rollback(); flash(str(e))
        elif action=='equip':
            try:
                item_id=int(request.form.get('item_id','0'))
                owned=c.execute('SELECT i.id FROM shop_inventory i JOIN shop_items s ON s.id=i.item_id WHERE i.user_id=? AND i.item_id=? AND (i.expires_at="" OR i.expires_at>?) AND s.item_type="Player Card"',(u['id'],item_id,datetime.now().isoformat(timespec='seconds'))).fetchone()
                if not owned: raise ValueError('पहले Player Card खरीदें और valid Inventory item चुनें।')
                c.execute('INSERT INTO equipped_cards(user_id,item_id) VALUES(?,?) ON CONFLICT(user_id) DO UPDATE SET item_id=excluded.item_id',(u['id'],item_id)); c.execute('UPDATE users SET equipped_card_id=? WHERE id=?',(item_id,u['id'])); c.commit(); flash('Player Card प्रोफाइल पर लगा दिया गया।')
            except (ValueError,sqlite3.Error) as e: c.rollback(); flash(str(e))
        return redirect(url_for('shop'))
    u=c.execute('SELECT * FROM users WHERE id=?',(u['id'],)).fetchone()
    items=c.execute('SELECT * FROM shop_items WHERE active=1 ORDER BY id DESC').fetchall()
    banners=c.execute('SELECT * FROM banners WHERE active=1 ORDER BY id DESC LIMIT 5').fetchall()
    inv=c.execute('SELECT i.*,s.name,s.item_type,s.image_url FROM shop_inventory i JOIN shop_items s ON s.id=i.item_id WHERE i.user_id=? ORDER BY i.id DESC',(u['id'],)).fetchall()
    spins=c.execute('SELECT * FROM spin_rewards WHERE active=1 ORDER BY id').fetchall()
    body='<h1 class="title">Vortex Shop</h1><p class="muted">Points, Coins और Diamonds अलग-अलग balances हैं।</p><div class="grid"><div class="card">Points <h2>'+str(u['rank_points'] or 0)+'</h2></div><div class="card">Coins <h2>'+str(u['coins'] or 0)+'</h2></div><div class="card">Diamonds <h2>'+str(u['diamonds'] or 0)+'</h2></div></div>'
    if banners:
        body+='<div class="banner-slider">'+''.join('<a class="banner-slide" href="'+html.escape(x['link_url'] or '/shop',quote=True)+'"><img src="'+html.escape(x['image_url'],quote=True)+'" alt="'+html.escape(x['title'],quote=True)+'"><b>'+html.escape(x['title'])+'</b></a>' for x in banners)+'</div>'
    body+='<div class="card"><h2>Lucky Spin / Lucky Royale</h2><p>एक Spin = 500 Coins. संभावित इनाम और probability-weighted rewards:</p><ul>'+''.join('<li>'+html.escape(x['label'])+' — '+str(round(100*int(x['weight'])/max(1,sum(int(y['weight']) for y in spins)),1))+'%</li>' for x in spins)+'</ul><form method="post"><input type="hidden" name="action" value="spin"><button class="btn full">Spin for 500 Coins</button></form></div><h2>Shop Items</h2>'
    for x in items:
        img='<img src="'+html.escape(x['image_url'],quote=True)+'" style="width:100%;height:120px;object-fit:cover;border-radius:9px" alt="item">' if x['image_url'] else ''
        body+='<div class="card">'+img+'<h3>'+html.escape(x['name'])+'</h3><p>'+html.escape(x['description'] or '')+'</p><span class="pill">'+html.escape(x['item_type'])+'</span> <span class="pill">'+str(x['price'])+' '+html.escape(x['currency'])+'</span><p class="muted">'+('Permanent' if not x['duration_days'] else str(x['duration_days'])+' days')+' · '+('Unlimited stock' if x['stock']<0 else str(x['stock'])+' left')+'</p><form method="post"><input type="hidden" name="action" value="buy"><input type="hidden" name="item_id" value="'+str(x['id'])+'"><button class="btn full" '+('disabled' if x['stock']==0 else '')+'>Buy</button></form></div>'
    body+='<h2>My Inventory</h2>'
    for x in inv:
        body+='<div class="card">'+html.escape(x['name'])+' <span class="pill">'+html.escape(x['item_type'])+'</span>'+(('<p class="muted">Expires: '+html.escape(x['expires_at'])+'</p>') if x['expires_at'] else '<p class="muted">Permanent</p>')
        if x['item_type']=='Player Card': body+='<form method="post"><input type="hidden" name="action" value="equip"><input type="hidden" name="item_id" value="'+str(x['item_id'])+'"><button class="btn">Equip on Profile</button></form>'
        body+='</div>'
    body+='<a class="btn secondary full" href="/player-card">Open Player Card</a>'
    return page(body,'settings',True)


init_db()
ensure_shop_schema()

if __name__=='__main__':
    init_db()
    url='http://127.0.0.1:8082'
    threading.Timer(1.2,lambda:webbrowser.open(url)).start()
    print('\nVortex Arena User App is starting...')
    print('Browser URL:',url)
    print('Database:',DB)
    print('Stop with Ctrl+C. Keep this window open while using the app.\n')
    app.run(host='127.0.0.1',port=8082,debug=False)
