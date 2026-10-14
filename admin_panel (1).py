# Vortex Arena Admin Panel - Python + Flask + shared SQLite database
# Run: python Vortex_Arena_Admin_Panel.py
# Place this file beside Vortex_Arena_User_App_Fixed.py. Both use vortex_arena_users.db.
import os, sys, sqlite3, threading, time, webbrowser, secrets, re, html, subprocess
from pathlib import Path
from datetime import datetime
try:
    from flask import Flask, request, redirect, url_for, session, flash, render_template_string, g
except ImportError:
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'flask'])
    from flask import Flask, request, redirect, url_for, session, flash, render_template_string, g
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

BASE=Path(__file__).resolve().parent
DB=Path(os.environ.get('VORTEX_DB_PATH',str(BASE/'vortex_arena_users.db'))).resolve()
UPLOADS=Path(os.environ.get('VORTEX_UPLOADS_DIR',str(BASE/'vortex_uploads'))).resolve()
UPLOADS.mkdir(exist_ok=True)
ALLOWED_IMAGE_EXTS={'.png','.jpg','.jpeg','.webp','.gif'}
app=Flask(__name__)
app.secret_key=os.environ.get('VORTEX_SECRET_KEY') or secrets.token_hex(32)
app.config['MAX_CONTENT_LENGTH']=4*1024*1024
GAMES=['Free Fire','BGMI','Roblox','Minecraft','Call of Duty Mobile','Valorant','eFootball','Viral Land','Other']

def connect():
    c=sqlite3.connect(DB, timeout=10); c.row_factory=sqlite3.Row; return c

def init_db():
    with connect() as c:
        c.execute('''CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT,email TEXT UNIQUE NOT NULL,password_hash TEXT NOT NULL,phone TEXT DEFAULT '',username TEXT DEFAULT '',player_uid TEXT DEFAULT '',team_name TEXT DEFAULT '',game TEXT DEFAULT 'Free Fire',game_uid TEXT DEFAULT '',avatar TEXT DEFAULT '',created_at TEXT DEFAULT CURRENT_TIMESTAMP)''')
        cols=[r['name'] for r in c.execute('PRAGMA table_info(users)')]
        for col,definition in [('arena_uid',"TEXT DEFAULT ''"),('rank_points','INTEGER DEFAULT 0'),('rank_name',"TEXT DEFAULT 'Bronze'"),('master_right_until',"TEXT DEFAULT ''")]:
            if col not in cols: c.execute(f'ALTER TABLE users ADD COLUMN {col} {definition}')
        for row in c.execute("SELECT id FROM users WHERE arena_uid IS NULL OR arena_uid=''").fetchall(): c.execute('UPDATE users SET arena_uid=? WHERE id=?',(f'VA-{10000+row["id"]}',row['id']))
        c.execute('''CREATE TABLE IF NOT EXISTS tournaments(id INTEGER PRIMARY KEY AUTOINCREMENT,game TEXT NOT NULL,title TEXT NOT NULL,entry_fee INTEGER NOT NULL,prize_pool INTEGER NOT NULL,slots INTEGER NOT NULL,players INTEGER NOT NULL,start_time TEXT NOT NULL,end_time TEXT NOT NULL,room_id TEXT DEFAULT '',room_password TEXT DEFAULT '',status TEXT DEFAULT 'Upcoming',youtube_url TEXT DEFAULT '',image_url TEXT DEFAULT '')''')
        c.execute('''CREATE TABLE IF NOT EXISTS registrations(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER NOT NULL,tournament_id INTEGER NOT NULL,utr TEXT DEFAULT '',payment_status TEXT DEFAULT 'Pending review',created_at TEXT DEFAULT CURRENT_TIMESTAMP,registration_status TEXT DEFAULT 'Pending',winner_status TEXT DEFAULT '',payout_status TEXT DEFAULT 'Not paid',UNIQUE(user_id,tournament_id))''')
        # Upgrade older user-app database without removing existing data.
        for table, col, definition in [('tournaments','image_url',"TEXT DEFAULT ''"),('registrations','registration_status',"TEXT DEFAULT 'Pending'"),('registrations','winner_status',"TEXT DEFAULT ''"),('registrations','payout_status',"TEXT DEFAULT 'Not paid'"),('registrations','team_id','INTEGER'),('registrations','slot_number','INTEGER')]:
            cols=[r['name'] for r in c.execute(f'PRAGMA table_info({table})')]
            if col not in cols: c.execute(f'ALTER TABLE {table} ADD COLUMN {col} {definition}')
        c.execute('''CREATE TABLE IF NOT EXISTS admin_accounts(id INTEGER PRIMARY KEY AUTOINCREMENT,username TEXT UNIQUE NOT NULL,password_hash TEXT NOT NULL,created_at TEXT DEFAULT CURRENT_TIMESTAMP)''')
        c.execute('''CREATE TABLE IF NOT EXISTS admin_notifications(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER NOT NULL,message TEXT NOT NULL,created_at TEXT DEFAULT CURRENT_TIMESTAMP,seen INTEGER DEFAULT 0)''')
        c.execute('''CREATE TABLE IF NOT EXISTS tournament_results(id INTEGER PRIMARY KEY AUTOINCREMENT,tournament_id INTEGER NOT NULL,player_name TEXT NOT NULL,team_name TEXT DEFAULT '',kills INTEGER DEFAULT 0,score INTEGER DEFAULT 0,position INTEGER NOT NULL,created_at TEXT DEFAULT CURRENT_TIMESTAMP,team_position INTEGER DEFAULT 0)''')
        result_cols=[r['name'] for r in c.execute('PRAGMA table_info(tournament_results)')]
        if 'team_position' not in result_cols: c.execute('ALTER TABLE tournament_results ADD COLUMN team_position INTEGER DEFAULT 0')
        c.execute('''CREATE TABLE IF NOT EXISTS rank_history(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER NOT NULL,delta INTEGER NOT NULL,reason TEXT NOT NULL,created_at TEXT DEFAULT CURRENT_TIMESTAMP)''')
        # Additive shared feature schema; safe for existing databases.
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
          "CREATE TABLE IF NOT EXISTS support_messages(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER NOT NULL,sender_role TEXT NOT NULL,sender_id INTEGER,message TEXT NOT NULL,created_at TEXT DEFAULT CURRENT_TIMESTAMP,seen INTEGER DEFAULT 0)"
        ]: c.execute(sql)
        msg_cols=[r['name'] for r in c.execute('PRAGMA table_info(messages)')]
        if 'seen' not in msg_cols: c.execute('ALTER TABLE messages ADD COLUMN seen INTEGER DEFAULT 0')
        cols=[r['name'] for r in c.execute('PRAGMA table_info(tournaments)')]
        for col,definition in [('map_name',"TEXT DEFAULT ''"),('mode',"TEXT DEFAULT 'Squad'"),('team_size','INTEGER DEFAULT 4'),('countdown_minutes','INTEGER DEFAULT 10')]:
            if col not in cols: c.execute(f'ALTER TABLE tournaments ADD COLUMN {col} {definition}')
        # First-run account is intentionally a temporary credential; change it immediately.
        if c.execute('SELECT COUNT(*) FROM admin_accounts').fetchone()[0]==0:
            username=os.environ.get('VORTEX_ADMIN_USER','admin')
            password=os.environ.get('VORTEX_ADMIN_PASSWORD','ChangeMe-123!')
            c.execute('INSERT INTO admin_accounts(username,password_hash) VALUES(?,?)',(username,generate_password_hash(password)))

def rank_for_points(points):
    points=max(0,int(points or 0))
    if points>=3000:return 'Master Right'
    if points>=2500:return 'Master'
    if points>=1000:return 'Diamond'
    if points>=400:return 'Gold'
    if points>=200:return 'Silver'
    return 'Bronze'

def refresh_tournament_slots(conn,tournament_id):
    t=conn.execute('SELECT slots,team_size FROM tournaments WHERE id=?',(tournament_id,)).fetchone()
    if not t:return
    size=max(1,min(4,int(t['team_size'] or 4)))
    rows=conn.execute("SELECT id FROM registrations WHERE tournament_id=? AND payment_status='Verified' AND registration_status!='Rejected' ORDER BY id",(tournament_id,)).fetchall()
    for i,row in enumerate(rows):
        slot=(i//size)+1
        conn.execute('UPDATE registrations SET slot_number=? WHERE id=?',(slot if slot<=int(t['slots']) else None,row['id']))
    conn.execute('UPDATE tournaments SET players=? WHERE id=?',(len(rows),tournament_id))

def apply_result_points(conn,tournament_id,entries):
    """Idempotently replace prior result awards; winner +100, loss -10, MVP +25."""
    old=conn.execute('SELECT * FROM result_awards WHERE tournament_id=?',(tournament_id,)).fetchall()
    for award in old:
        user=conn.execute('SELECT rank_points FROM users WHERE id=?',(award['user_id'],)).fetchone()
        if user:
            points=max(0,int(user['rank_points'] or 0)-int(award['delta']))
            conn.execute('UPDATE users SET rank_points=?,rank_name=? WHERE id=?',(points,rank_for_points(points),award['user_id']))
            conn.execute('INSERT INTO rank_history(user_id,delta,reason) VALUES(?,?,?)',(award['user_id'],-int(award['delta']),'Result correction reversal'))
    conn.execute('DELETE FROM result_awards WHERE tournament_id=?',(tournament_id,))
    regs=conn.execute("SELECT r.user_id,u.username,u.arena_uid,u.player_uid,u.game_uid,u.email FROM registrations r JOIN users u ON u.id=r.user_id WHERE r.tournament_id=? AND r.payment_status='Verified'",(tournament_id,)).fetchall()
    normalized=lambda v: re.sub(r'[^a-z0-9]','',(v or '').lower())
    mapped={}
    for e in entries:
        key=normalized(e['player_name'])
        for reg in regs:
            candidates=[reg['username'],reg['arena_uid'],reg['player_uid'],reg['game_uid'],reg['email']]
            if key and key in [normalized(x) for x in candidates if x]: mapped[reg['user_id']]=e; break
    if not mapped:return 0
    mvp=max(mapped.items(),key=lambda item:int(item[1]['kills'] or 0))[0]
    awarded=0
    for reg in regs:
        if reg['user_id'] not in mapped: continue
        e=mapped[reg['user_id']]
        team_pos=int(e.get('team_position') or 0) if isinstance(e,dict) else 0
        # For squad results, every matched player whose team is ranked first gets the win award.
        winning_team=next((normalized(x.get('team_name','')) for x in entries if int(x.get('team_position') or 0)==1 and x.get('team_name')), '')
        is_winner=(team_pos==1) or (bool(winning_team) and normalized(e.get('team_name',''))==winning_team) or (not winning_team and int(e['position'])==1)
        base=100 if is_winner else -10
        reason='Tournament win' if base>0 else 'Tournament loss'
        deltas=[(base,reason)]
        if reg['user_id']==mvp and int(e['kills'] or 0)>0:deltas.append((25,'MVP bonus'))
        for delta,why in deltas:
            user=conn.execute('SELECT rank_points,master_right_until FROM users WHERE id=?',(reg['user_id'],)).fetchone()
            old_points=int(user['rank_points'] or 0)
            points=max(0,old_points+delta); applied_delta=points-old_points; rank=rank_for_points(points); until=user['master_right_until'] or ''
            if rank=='Master Right' and rank_for_points(old_points)!='Master Right':
                from datetime import timedelta
                until=(datetime.utcnow()+timedelta(days=30)).strftime('%Y-%m-%d %H:%M:%S')
            conn.execute('UPDATE users SET rank_points=?,rank_name=?,master_right_until=? WHERE id=?',(points,rank,until,reg['user_id']))
            conn.execute('INSERT INTO rank_history(user_id,delta,reason) VALUES(?,?,?)',(reg['user_id'],applied_delta,why))
            conn.execute('INSERT INTO result_awards(tournament_id,user_id,delta,reason) VALUES(?,?,?,?)',(tournament_id,reg['user_id'],applied_delta,why))
            if why=='Tournament win': conn.execute('INSERT OR IGNORE INTO achievements(user_id,code,title) VALUES(?,?,?)',(reg['user_id'],f'win_{tournament_id}','Tournament Winner'))
            if why=='MVP bonus': conn.execute('INSERT OR IGNORE INTO achievements(user_id,code,title) VALUES(?,?,?)',(reg['user_id'],f'mvp_{tournament_id}','Match MVP'))
            conn.execute('INSERT INTO user_notifications(user_id,message) VALUES(?,?)',(reg['user_id'],f'{why}: {delta:+d} rank points. Current rank: {rank} ({points}).'))
            awarded+=1
    return awarded

def db():
    if 'db' not in g:g.db=connect()
    return g.db
@app.teardown_appcontext
def close_db(exc):
    c=g.pop('db',None)
    if c:c.close()

def logged(): return bool(session.get('admin_id'))
def need_login():
    if not logged(): return redirect(url_for('login'))
    return None

def shell(title,active,body):
    return render_template_string('''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{{title}} · Vortex Arena Admin</title><style>
:root{color-scheme:dark;--bg:#050916;--panel:#0b1430;--line:#283b70;--purple:#842cff;--blue:#086be9;--text:#f3f5ff;--muted:#9eafd7;--cyan:#08c8ef}*{box-sizing:border-box}body{margin:0;background:radial-gradient(ellipse at 75% 0%,#111c4b 0,transparent 45%),var(--bg);color:var(--text);font:15px system-ui,Arial}a{color:inherit;text-decoration:none}button,.btn{border:0;border-radius:10px;padding:11px 15px;background:linear-gradient(110deg,var(--purple),var(--blue));color:white;font-weight:700;cursor:pointer;display:inline-block}button:hover,.btn:hover{filter:brightness(1.14);transform:translateY(-1px)}input,select,textarea{width:100%;padding:12px;border:1px solid #314675;border-radius:9px;background:#070d20;color:white;margin:5px 0 12px}label{display:block;color:#c4d0f5;font-size:13px}h1{font-size:clamp(24px,3vw,34px);margin:0 0 6px}h2{font-size:20px;margin:0 0 12px}.muted{color:var(--muted)}.layout{display:grid;grid-template-columns:245px 1fr;min-height:100vh}.side{padding:22px 14px;border-right:1px solid #1a2c55;background:#040918}.brand{font-weight:900;font-size:20px;letter-spacing:2px;padding:6px 10px 25px}.brand b{color:#a34cff}.nav{display:grid;gap:7px}.nav a{padding:13px;border-radius:10px;color:#c2cdef}.nav a.active,.nav a:hover{background:linear-gradient(100deg,#7417ef,#064bb9);color:#fff}.main{min-width:0}.top{height:76px;border-bottom:1px solid #1b2c54;display:flex;align-items:center;justify-content:space-between;padding:0 28px}.online{color:#28e6a0}.content{padding:26px;max-width:1500px;margin:auto}.hero{padding:25px;border:1px solid #6025d8;border-radius:17px;background:linear-gradient(105deg,#0c1432,#080b20 65%,#21105a);margin-bottom:22px}.grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px;margin:18px 0}.stat,.card{background:linear-gradient(145deg,#0d1735,#080e20);border:1px solid #263e76;border-radius:14px;padding:17px;min-width:0}.stat strong{display:block;font-size:28px;margin-top:8px}.stat:nth-child(3n+1){border-color:#7828df}.stat:nth-child(3n+2){border-color:#067fe7}.row{display:flex;gap:10px;align-items:center;flex-wrap:wrap}.between{justify-content:space-between}.tablewrap{overflow-x:auto;border:1px solid #243866;border-radius:12px;margin:14px 0}table{border-collapse:collapse;width:100%;min-width:760px;background:#080f24}th,td{text-align:left;padding:12px;border-bottom:1px solid #1c2d50;vertical-align:top}th{color:#b4c8ff;background:#101b39;font-size:12px;text-transform:uppercase}td small{color:var(--muted)}.pill{display:inline-block;padding:4px 9px;border-radius:99px;background:#182d53;color:#a8c7ff;font-size:12px}.ok{color:#48e4a5}.warn{color:#ffd16d}.bad{color:#ff7d9c}.danger{background:#9c2449}.secondary{background:#1a2a4c}.two{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}.flash{background:#12284b;border:1px solid #315da2;border-radius:10px;padding:12px;margin-bottom:14px}.formgrid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}.full{grid-column:1/-1}.loginbox{max-width:420px;margin:8vh auto;padding:26px}.foot{color:#8295c7;border-top:1px solid #1b2c54;padding:20px 26px;font-size:13px}@media(max-width:850px){.layout{grid-template-columns:1fr}.side{padding:12px;border-right:0;border-bottom:1px solid #20325a}.brand{padding:8px}.nav{display:flex;overflow:auto}.nav a{white-space:nowrap;padding:10px}.top{padding:0 15px;height:60px}.content{padding:15px}.grid{grid-template-columns:repeat(2,minmax(0,1fr))}.two{grid-template-columns:1fr}.formgrid{grid-template-columns:1fr}.full{grid-column:auto}}@media(max-width:420px){.grid{gap:8px}.stat,.card{padding:12px}.stat strong{font-size:22px}}
</style></head><body>{% if logged %}<div class="layout"><aside class="side"><div class="brand">⚡ VORTEX <b>ARENA</b><div class="muted" style="font-size:10px;letter-spacing:3px">ESPORTS · ADMIN PANEL</div></div><nav class="nav">{% for href,label in nav %}<a class="{{'active' if active==href else ''}}" href="{{url_for(href)}}">{{label}}</a>{% endfor %}</nav></aside><section class="main"><header class="top"><b>♢ ADMIN PANEL</b><span class="online">● Online &nbsp; <span style="color:white">{{session.get('admin_name','Admin')}}</span></span></header><main class="content">{% for m in get_flashed_messages() %}<div class="flash">{{m}}</div>{% endfor %}{{body|safe}}</main><footer class="foot">Vortex Arena © 2026 · Admin Control Panel <span style="float:right">Play · Compete · Win</span></footer></section></div>{% else %}{% for m in get_flashed_messages() %}<div class="flash">{{m}}</div>{% endfor %}{{body|safe}}{% endif %}</body></html>''',title=title,active=active,body=body,logged=logged(),session=session,nav=[('dashboard','⌂ Dashboard'),('tournaments','🏆 Manage Tournaments'),('users','♙ Users'),('payments','₹ Payments'),('results','▥ Results'),('ranks','🏅 Rank Control'),('announcements','📢 Announcements'),('reports','🛡 Reports & Audit'),('messages','✉ Player Inbox'),('settings','⚙ Settings'),('logout','⇥ Logout')])

@app.route('/uploads/<path:name>')
def uploaded_file(name):
    from flask import send_from_directory
    return send_from_directory(UPLOADS,name)

@app.route('/')
def root():return redirect(url_for('dashboard' if logged() else 'login'))
@app.route('/login',methods=['GET','POST'])
def login():
    if request.method=='POST':
        name=request.form.get('username','').strip(); pw=request.form.get('password','')
        a=db().execute('SELECT * FROM admin_accounts WHERE username=?',(name,)).fetchone()
        if a and check_password_hash(a['password_hash'],pw):session.clear();session['admin_id']=a['id'];session['admin_name']=a['username'];return redirect(url_for('dashboard'))
        flash('Login details सही नहीं हैं।')
    body='''<div class="loginbox card"><div class="brand">⚡ VORTEX <b>ARENA</b><div class="muted">ADMIN CONTROL PANEL</div></div><h1>Welcome Back</h1><p class="muted">Sign in to manage tournaments, players and payments.</p><form method="post"><label>Admin username</label><input name="username" required autocomplete="username" placeholder="admin"><label>Password</label><input name="password" type="password" required autocomplete="current-password"><button style="width:100%">Secure Admin Login</button></form><p class="muted" style="font-size:12px">First run default: admin / ChangeMe-123! — change it in Settings immediately.</p></div>'''
    return shell('Admin Login','',body)
@app.route('/logout')
def logout():session.clear();return redirect(url_for('login'))
@app.route('/dashboard')
def dashboard():
    r=need_login()
    if r:return r
    c=db(); users=c.execute('SELECT COUNT(*) n FROM users').fetchone()['n']; ts=c.execute('SELECT COUNT(*) n FROM tournaments').fetchone()['n']; pending=c.execute("SELECT COUNT(*) n FROM registrations WHERE payment_status NOT IN ('Verified','Rejected')").fetchone()['n']; live=c.execute("SELECT COUNT(*) n FROM tournaments WHERE status='Live'").fetchone()['n']
    recent=c.execute('SELECT r.id,r.utr,r.payment_status,u.email,t.title,t.entry_fee FROM registrations r JOIN users u ON u.id=r.user_id JOIN tournaments t ON t.id=r.tournament_id ORDER BY r.id DESC LIMIT 8').fetchall()
    rows=''.join(f"<tr><td>#{x['id']}</td><td>{x['email']}</td><td>{x['title']}<br><small>₹{x['entry_fee']}</small></td><td>{x['utr'] or '—'}</td><td>{x['payment_status']}</td><td><a class='btn' href='{url_for('payments')}'>Review</a></td></tr>" for x in recent) or '<tr><td colspan="6">अभी कोई registration नहीं है।</td></tr>'
    body=f'''<section class="hero"><h1>Welcome Back, <span style="color:#a64cff">Admin</span></h1><p class="muted">Manage Tournaments · Verify Payments · Update Results · Grow Your Esports Community</p></section><div class="grid"><div class="stat"><span class="muted">Total Players</span><strong>{users}</strong></div><div class="stat"><span class="muted">Tournaments</span><strong>{ts}</strong></div><div class="stat"><span class="muted">Pending Payments</span><strong>{pending}</strong></div><div class="stat"><span class="muted">Live Matches</span><strong>{live}</strong></div></div><div class="grid"><a class="card" href="{url_for('tournaments')}" style="text-align:center"><div style="font-size:38px;color:#c35bff">＋</div><h2>Add Tournament</h2><p class="muted">Create match, fees, slots, timing and artwork.</p></a><a class="card" href="{url_for('results')}" style="text-align:center"><div style="font-size:38px;color:#13cafa">🏆</div><h2>Add Result</h2><p class="muted">Set winner and prize payout status.</p></a><a class="card" href="{url_for('users')}" style="text-align:center"><div style="font-size:38px;color:#a64cff">♙</div><h2>Users</h2><p class="muted">View registered players and game IDs.</p></a><a class="card" href="{url_for('messages')}" style="text-align:center"><div style="font-size:38px;color:#13cafa">✉</div><h2>Player Inbox</h2><p class="muted">Reply to players in the Admin Support Chat.</p></a><a class="card" href="{url_for('tournaments')}" style="text-align:center"><div style="font-size:38px;color:#a64cff">↗</div><h2>Live / Room Control</h2><p class="muted">Room ID, scheduled password release and YouTube link.</p></a></div><h2>Recent Registrations & Payments</h2><div class="tablewrap"><table><tr><th>ID</th><th>Player</th><th>Tournament</th><th>UTR</th><th>Status</th><th>Action</th></tr>{rows}</table></div>'''
    return shell('Dashboard','dashboard',body)

@app.route('/tournaments',methods=['GET','POST'])
def tournaments():
    r=need_login()
    if r:return r
    c=db()
    if request.method=='POST':
        action=request.form.get('action')
        try:
            if action=='delete':
                tid=int(request.form['id']); c.execute('DELETE FROM registrations WHERE tournament_id=?',(tid,)); c.execute('DELETE FROM tournaments WHERE id=?',(tid,)); c.commit(); flash('Tournament और उसकी registrations delete हुईं।')
            elif action=='save':
                game=request.form.get('game','Other'); title=request.form.get('title','').strip(); fee=int(request.form.get('entry_fee',0)); prize=int(request.form.get('prize_pool',100)); slots=int(request.form.get('slots',48)); start=request.form.get('start_time','').strip(); end=request.form.get('end_time','').strip(); status=request.form.get('status','Upcoming'); room=request.form.get('room_id','').strip(); pw=request.form.get('room_password','').strip(); yt=request.form.get('youtube_url','').strip(); img=request.form.get('image_url','').strip(); map_name=request.form.get('map_name','').strip()[:80]; mode=request.form.get('mode','Squad'); team_size=max(1,min(4,int(request.form.get('team_size','4')))); countdown=max(0,min(180,int(request.form.get('countdown_minutes','10')))); tid=request.form.get('id','').strip()
                if not title or fee<0 or prize<0 or slots<1 or not start or not end: raise ValueError('सभी जरूरी fields सही भरें।')
                if status not in ('Upcoming','Live','Completed'):status='Upcoming'
                if tid:
                    c.execute('UPDATE tournaments SET game=?,title=?,entry_fee=?,prize_pool=?,slots=?,start_time=?,end_time=?,status=?,room_id=?,room_password=?,youtube_url=?,image_url=?,map_name=?,mode=?,team_size=?,countdown_minutes=? WHERE id=?',(game,title,fee,prize,slots,start,end,status,room,pw,yt,img,map_name,mode,team_size,countdown,int(tid))); flash('Tournament update हो गया।')
                else:
                    c.execute('INSERT INTO tournaments(game,title,entry_fee,prize_pool,slots,players,start_time,end_time,status,room_id,room_password,youtube_url,image_url,map_name,mode,team_size,countdown_minutes) VALUES(?,?,?,?,?,0,?,?,?,?,?,?,?,?,?,?,?)',(game,title,fee,prize,slots,start,end,status,room,pw,yt,img,map_name,mode,team_size,countdown)); flash('नया tournament बन गया।')
                c.commit()
        except (ValueError,sqlite3.Error) as e: c.rollback();flash('Save नहीं हुआ: '+str(e))
        return redirect(url_for('tournaments'))
    edit=None
    if request.args.get('edit','').isdigit():edit=c.execute('SELECT * FROM tournaments WHERE id=?',(int(request.args['edit']),)).fetchone()
    val=lambda k,d='': (edit[k] if edit and k in edit.keys() and edit[k] is not None else d)
    gameopts=''.join(f'<option {"selected" if val("game","Free Fire")==g else ""}>{g}</option>' for g in GAMES)
    body=f'''<h1>Manage Tournaments</h1><p class="muted">Create or edit tournament details. Room ID/password appears only to verified players when the configured release countdown begins.</p><section class="card"><h2>{'Edit Tournament' if edit else 'Add Tournament'}</h2><form method="post"><input type="hidden" name="action" value="save"><input type="hidden" name="id" value="{val('id')}"><div class="formgrid"><div><label>Game</label><select name="game">{gameopts}</select></div><div><label>Tournament title</label><input name="title" required value="{val('title')}" placeholder="Free Fire Squad Battle"></div><div><label>Entry fee (₹)</label><input type="number" min="0" name="entry_fee" value="{val('entry_fee','5')}" required></div><div><label>Prize pool / reward (₹)</label><input type="number" min="0" name="prize_pool" value="{val('prize_pool','100')}" required></div><div><label>Total slots</label><input type="number" min="1" name="slots" value="{val('slots','48')}" required></div><div><label>Status</label><select name="status">{''.join(f'<option {"selected" if val("status","Upcoming")==s else ""}>{s}</option>' for s in ['Upcoming','Live','Completed'])}</select></div><div><label>Start time (local; e.g. 2026-10-12 19:50)</label><input name="start_time" value="{val('start_time')}" required placeholder="2026-10-12 19:50"></div><div><label>End time</label><input name="end_time" value="{val('end_time')}" required placeholder="2026-10-12 20:50"></div><div><label>Room ID</label><input name="room_id" value="{val('room_id')}" placeholder="Room ID"></div><div><label>Room password (release after start)</label><input name="room_password" value="{val('room_password')}" placeholder="Room password"></div><div><label>YouTube Live URL</label><input name="youtube_url" value="{val('youtube_url')}" placeholder="https://youtube.com/live/..."></div><div><label>Tournament image URL</label><input name="image_url" value="{val('image_url')}" placeholder="https://.../game-art.jpg"></div><div><label>Map</label><select name="map_name">{''.join(f'<option {"selected" if val("map_name","")==m else ""}>{m}</option>' for m in (["Bermuda","Purgatory","Kalahari","Alpine","Nexterra"] if val("game","Free Fire")=="Free Fire" else ["Erangel","Miramar","Sanhok","Vikendi","Livik","Rondo"]))}</select></div><div><label>Mode</label><select name="mode">{''.join(f'<option {"selected" if val("mode","Squad")==m else ""}>{m}</option>' for m in ["Solo","Duo","Squad"] )}</select></div><div><label>Team size (Squad default 4)</label><input type="number" name="team_size" min="1" max="4" value="{val('team_size','4')}"></div><div><label>Room countdown minutes</label><input type="number" name="countdown_minutes" min="0" max="180" value="{val('countdown_minutes','10')}"></div><div class="full"><button>{'Save Changes' if edit else '＋ Create Tournament'}</button> <a class="btn secondary" href="{url_for('tournaments')}">Clear</a></div></div></form></section><h2 style="margin-top:24px">All Tournaments</h2>'''
    rows=c.execute('SELECT t.*, (SELECT COUNT(*) FROM registrations r WHERE r.tournament_id=t.id) AS reg_count FROM tournaments t ORDER BY id DESC').fetchall()
    body+='<div class="tablewrap"><table><tr><th>Game / Title</th><th>Fee / Prize</th><th>Players</th><th>Time</th><th>Status</th><th>Actions</th></tr>'
    for t in rows:
        body+=f'''<tr><td><b>{t['game']}</b><br>{t['title']}<br><small>{t['image_url'] or 'No image URL'}</small></td><td>₹{t['entry_fee']} / ₹{t['prize_pool']}</td><td>{t['reg_count']}/{int(t['slots'])*max(1,int(t['team_size'] or 4))} players<br><small>{t['slots']} team slots</small></td><td>{t['start_time']}<br><small>Ends: {t['end_time']}</small></td><td><span class="pill">{t['status']}</span></td><td><div class="row"><a class="btn" href="{url_for('tournaments',edit=t['id'])}">Edit</a><form method="post" onsubmit="return confirm('Delete this tournament and its registrations?')"><input type="hidden" name="action" value="delete"><input type="hidden" name="id" value="{t['id']}"><button class="danger">Delete</button></form></div></td></tr>'''
    body+='</table></div>'
    return shell('Manage Tournaments','tournaments',body)

@app.route('/users')
def users():
    r=need_login()
    if r:return r
    rows=db().execute('SELECT u.*, (SELECT COUNT(*) FROM registrations r WHERE r.user_id=u.id) reg_count FROM users u ORDER BY u.id DESC').fetchall()
    body="<h1>Players / Users</h1><p class='muted'>Registered player details and game UID. <a class='btn' href='/ranks'>🏅 Manage Ranks &amp; Points</a></p><div class='tablewrap'><table><tr><th>Player</th><th>Email / Phone</th><th>Game / UID</th><th>Team</th><th>Joined</th><th>Registrations</th></tr>"
    for u in rows:body+=f"<tr><td><b>{u['username'] or 'Player'}</b><br><small>UID: {u['player_uid'] or '—'}</small></td><td>{u['email']}<br><small>{u['phone'] or '—'}</small></td><td>{u['game'] or '—'}<br><small>{u['game_uid'] or '—'}</small></td><td>{u['team_name'] or '—'}</td><td>{u['created_at']}</td><td>{u['reg_count']}</td></tr>"
    body+='</table></div>'
    return shell('Users','users',body)


@app.route('/ranks',methods=['GET','POST'])
def ranks():
    r=need_login()
    if r:return r
    c=db()
    if request.method=='POST':
        try:
            uid=int(request.form.get('user_id','0')); delta=int(request.form.get('delta','0')); reason=request.form.get('reason','Admin rank update').strip()[:200]
            if abs(delta)>10000 or not reason: raise ValueError('Invalid points or reason')
            user=c.execute('SELECT * FROM users WHERE id=?',(uid,)).fetchone()
            if not user: raise ValueError('Player not found')
            points=max(0,int(user['rank_points'] or 0)+delta)
            if points<200: rank='Bronze'
            elif points<400: rank='Silver'
            elif points<1000: rank='Gold'
            elif points<2500: rank='Diamond'
            elif points<3000: rank='Master'
            else: rank='Master Right'
            until=user['master_right_until'] or ''
            if rank=='Master Right' and (int(user['rank_points'] or 0)<3000):
                from datetime import timedelta
                until=(datetime.utcnow()+timedelta(days=30)).strftime('%Y-%m-%d %H:%M:%S')
            c.execute('UPDATE users SET rank_points=?,rank_name=?,master_right_until=? WHERE id=?',(points,rank,until,uid))
            c.execute('INSERT INTO rank_history(user_id,delta,reason) VALUES(?,?,?)',(uid,delta,reason)); c.execute('INSERT INTO admin_audit(admin_name,action,details) VALUES(?,?,?)',(session.get('admin_name','Admin'),'Rank points changed',f'user_id={uid}; delta={delta}; reason={reason}')); c.execute('INSERT INTO user_notifications(user_id,message) VALUES(?,?)',(uid,f'आपके points {delta:+d} बदले गए। नई rank: {rank} ({points} points).')); c.commit(); flash(f"{user['username'] or user['email']} की Rank {rank}, Points {points} अपडेट हुए।")
        except (ValueError,sqlite3.Error) as e:c.rollback();flash('Rank अपडेट नहीं हुआ: '+str(e))
        return redirect(url_for('ranks'))
    rows=c.execute('SELECT id,email,username,arena_uid,rank_points,rank_name,master_right_until FROM users ORDER BY rank_points DESC,id DESC').fetchall()
    body="<h1>🏅 Rank & Points Control</h1><p class='muted'>Bronze 0–199 · Silver 200–399 · Gold 400–999 · Diamond 1000–2499 · Master 2500–2999 · Master Right 3000+. Points change का reason history में save होगा।</p><div class='tablewrap'><table><tr><th>Player</th><th>Rank / Points</th><th>Add / Remove Points</th></tr>"
    for x in rows:
        body+=f"<tr><td><b>{x['username'] or 'Player'}</b><br><small>{x['email']} · {x['arena_uid'] or ('VA-'+str(10000+x['id']))}</small></td><td>{x['rank_name'] or 'Bronze'}<br>{x['rank_points'] or 0} points<br><small>Master Right until: {x['master_right_until'] or 'Not active'}</small></td><td><form method='post'><input type='hidden' name='user_id' value='{x['id']}'><label>Points (+/-)</label><input type='number' name='delta' min='-10000' max='10000' required placeholder='e.g. 20 or -10'><label>Reason</label><input name='reason' required maxlength='200' placeholder='Win / loss / correction'><button>Save Points</button></form></td></tr>"
    body+='</table></div>'
    return shell('Rank Control','ranks',body)

@app.route('/payments',methods=['GET','POST'])
def payments():
    r=need_login()
    if r:return r
    c=db()
    if request.method=='POST':
        rid=request.form.get('registration_id',''); action=request.form.get('action')
        try:
            row=c.execute('SELECT r.*,t.title FROM registrations r JOIN tournaments t ON t.id=r.tournament_id WHERE r.id=?',(int(rid),)).fetchone()
            if row:
                if action=='verify':
                    c.execute("UPDATE registrations SET payment_status='Verified',registration_status='Confirmed' WHERE id=?",(int(rid),)); refresh_tournament_slots(c,row['tournament_id']); c.execute('INSERT INTO user_notifications(user_id,message) SELECT user_id,? FROM registrations WHERE id=?',(f'Payment verified for {row["title"]}. Your slot is assigned.',int(rid))); flash('Payment को manually Verified mark किया। पहले UTR/payment statement मिलाएँ।')
                elif action=='reject':c.execute("UPDATE registrations SET payment_status='Rejected',registration_status='Rejected',slot_number=NULL WHERE id=?",(int(rid),)); refresh_tournament_slots(c,row['tournament_id']); c.execute('INSERT INTO user_notifications(user_id,message) SELECT user_id,? FROM registrations WHERE id=?',(f'Payment rejected for {row["title"]}. Contact support if this seems incorrect.',int(rid))); flash('Payment rejected mark हुआ।')
                c.commit()
        except (ValueError,sqlite3.Error):c.rollback();flash('Action पूरा नहीं हुआ।')
        return redirect(url_for('payments'))
    rows=c.execute('SELECT r.*,u.email,u.username,t.title,t.entry_fee,t.game FROM registrations r JOIN users u ON u.id=r.user_id JOIN tournaments t ON t.id=r.tournament_id ORDER BY r.id DESC').fetchall()
    body='<h1>Payments & UTR Review</h1><p class="muted">UTR का format payment proof नहीं है। अपने UPI/bank statement में वास्तविक credit मिलाने के बाद ही Verify दबाएँ।</p><div class="tablewrap"><table><tr><th>Player</th><th>Tournament</th><th>Amount</th><th>UTR</th><th>Status</th><th>Review</th></tr>'
    for x in rows:
        body+=f'''<tr><td>{x['username'] or 'Player'}<br><small>{x['email']}</small></td><td>{x['title']}<br><small>{x['game']}</small></td><td>₹{x['entry_fee']}</td><td>{x['utr'] or 'Not submitted'}</td><td><span class="pill">{x['payment_status']}</span></td><td><div class="row"><form method="post" onsubmit="return confirm('Only verify after matching actual bank/UPI credit. Continue?')"><input type="hidden" name="registration_id" value="{x['id']}"><input type="hidden" name="action" value="verify"><button>Verify</button></form><form method="post" onsubmit="return confirm('Reject this payment submission?')"><input type="hidden" name="registration_id" value="{x['id']}"><input type="hidden" name="action" value="reject"><button class="danger">Reject</button></form></div></td></tr>'''
    body+='</table></div>'
    return shell('Payments','payments',body)

@app.route('/results',methods=['GET','POST'])
def results():
    r=need_login()
    if r:return r
    c=db()
    if request.method=='POST':
        action=request.form.get('action','')
        if action=='add_scoreboard':
            try:
                tid=int(request.form.get('tournament_id','0'))
                tournament=c.execute('SELECT id,title FROM tournaments WHERE id=?',(tid,)).fetchone()
                if not tournament:
                    flash('पहले सही tournament चुनें।')
                    return redirect(url_for('results'))
                # Replace the saved scoreboard for this tournament, so corrections don't create duplicates.
                entries=[]
                for i in range(1,49):
                    name=request.form.get(f'player_name_{i}','').strip()[:100]
                    team=request.form.get(f'team_name_{i}','').strip()[:100]
                    kills_raw=request.form.get(f'kills_{i}','0').strip()
                    score_raw=request.form.get(f'score_{i}','0').strip()
                    team_position_raw=request.form.get(f'team_position_{i}','').strip()
                    if not name:
                        continue
                    try:
                        kills=max(0,min(9999,int(kills_raw or 0)))
                        score=max(0,min(999999,int(score_raw or 0)))
                        team_position=max(1,min(12,int(team_position_raw or i)))
                    except ValueError:
                        flash(f'Player {i} के Kills और Score में केवल संख्या लिखें।')
                        return redirect(url_for('results'))
                    entries.append((tid,name,team,kills,score,i,team_position))
                if not entries:
                    flash('कम से कम एक खिलाड़ी का नाम भरें।')
                    return redirect(url_for('results'))
                c.execute('DELETE FROM tournament_results WHERE tournament_id=?',(tid,))
                c.executemany('INSERT INTO tournament_results(tournament_id,player_name,team_name,kills,score,position,team_position) VALUES(?,?,?,?,?,?,?)',entries)
                award_entries=[{'player_name':e[1],'team_name':e[2],'kills':e[3],'score':e[4],'position':e[5],'team_position':e[6]} for e in entries]
                awarded=apply_result_points(c,tid,award_entries)
                c.execute('INSERT INTO admin_audit(admin_name,action,details) VALUES(?,?,?)',(session.get('admin_name','Admin'),'Tournament results published',f'{tournament["title"]}; entries={len(entries)}; award changes={awarded}'))
                c.commit()
                flash(f'{tournament["title"]}: {len(entries)} खिलाड़ियों का रिज़ल्ट सेव हुआ; {awarded} rank award entries लागू हुईं। नाम का registered profile से match होना जरूरी है।')
            except (ValueError,sqlite3.Error) as e:
                c.rollback(); flash('रिज़ल्ट सेव नहीं हुआ: '+str(e))
            return redirect(url_for('results'))
        try:
            rid=int(request.form.get('registration_id','0')); action=request.form.get('action',''); row=c.execute('SELECT r.*,t.prize_pool,t.title FROM registrations r JOIN tournaments t ON t.id=r.tournament_id WHERE r.id=?',(rid,)).fetchone()
            if not row:flash('Registration नहीं मिला।')
            elif action=='winner':
                if row['payment_status']!='Verified':flash('Winner घोषित करने से पहले payment/registration verify करें।')
                else:
                    c.execute("UPDATE registrations SET winner_status='Winner' WHERE id=?",(rid,)); notice=f"बधाई हो! आप {row['title']} के विजेता बने हैं। घोषित reward ₹{row['prize_pool']} है। Payout admin confirmation के अधीन है।"; c.execute("INSERT INTO admin_notifications(user_id,message) VALUES(?,?)",(row['user_id'],notice)); c.execute("INSERT INTO user_notifications(user_id,message) VALUES(?,?)",(row['user_id'],notice)); c.commit();flash('Winner set हुआ और in-app notification record बना। SMS/push अपने-आप नहीं भेजा जाता।')
            elif action=='payout':c.execute("UPDATE registrations SET payout_status='Paid' WHERE id=?",(rid,)); c.execute("INSERT INTO user_notifications(user_id,message) SELECT user_id,? FROM registrations WHERE id=?",(f'Prize payout for {row["title"]} marked Paid by admin. Please confirm receipt with support if needed.',rid)); c.commit();flash('Payout को Paid mark किया। वास्तविक transfer अलग से करना और verify करना होगा।')
        except (ValueError,sqlite3.Error) as e:c.rollback();flash('Update नहीं हुआ: '+str(e))
        return redirect(url_for('results'))
    tournaments=c.execute('SELECT id,title,game FROM tournaments ORDER BY id DESC').fetchall()
    saved=c.execute('SELECT tr.*,t.title,t.game FROM tournament_results tr JOIN tournaments t ON t.id=tr.tournament_id ORDER BY tr.tournament_id DESC,tr.position ASC').fetchall()
    rows=c.execute("SELECT r.*,u.email,u.username,t.title,t.prize_pool,t.game FROM registrations r JOIN users u ON u.id=r.user_id JOIN tournaments t ON t.id=r.tournament_id WHERE r.payment_status='Verified' ORDER BY r.id DESC").fetchall()
    opts=''.join(f'<option value="{t["id"]}">{t["game"]} — {t["title"]}</option>' for t in tournaments)
    body='''<div class="row between"><div><h1>Results & Rewards</h1><p class="muted">48 खिलाड़ियों तक के kills, score, team और team position भरें। सेव करने पर User Panel के Result/Leaderboard में दिखाई देगा।</p></div><a class="btn" href="#add-result">＋ Add Result</a></div>
    <section class="card" id="add-result"><h2>＋ Add Result / Scoreboard</h2><form method="post"><input type="hidden" name="action" value="add_scoreboard"><label>Tournament</label><select name="tournament_id" required>'''+opts+'''</select><p class="muted">पहली तीन positions पर 🥇🥈🥉 अपने-आप दिखेंगे। खाली खिलाड़ी छोड़ सकते हैं। दोबारा सेव करने पर उसी tournament का पुराना scoreboard बदल जाएगा।</p><div class="tablewrap"><table><tr><th>Player Row</th><th>Player Name</th><th>Team Name</th><th>Team Position</th><th>Kills</th><th>Score</th></tr>'''
    medals={1:'🥇 1st',2:'🥈 2nd',3:'🥉 3rd'}
    for i in range(1,49):
        pos=medals.get(i,f'{i}th')
        body+=f'''<tr><td><b>{pos}</b></td><td><input name="player_name_{i}" placeholder="Player {i}" maxlength="100"></td><td><input name="team_name_{i}" placeholder="Team"></td><td><input name="team_position_{i}" type="number" min="1" max="12" placeholder="Team rank"></td><td><input name="kills_{i}" type="number" min="0" max="9999" value="0"></td><td><input name="score_{i}" type="number" min="0" max="999999" value="0"></td></tr>'''
    body+='''</table></div><button type="submit">💾 Save Result</button></form></section>
    <h2>Published Scoreboards</h2><div class="tablewrap"><table><tr><th>Player Position</th><th>Player</th><th>Team</th><th>Tournament</th><th>Kills</th><th>Score</th></tr>'''
    for x in saved:
        medal=medals.get(x['position'],f"{x['position']}th")
        body+=f'''<tr><td><b>{medal}</b></td><td>{html.escape(x['player_name'])}</td><td>{html.escape(x['team_name'] or '—')}</td><td>{html.escape(x['title'])}<br><small>{html.escape(x['game'])}</small></td><td>{x['kills']}</td><td>{x['score']}</td></tr>'''
    if not saved: body+='<tr><td colspan="6" class="muted">अभी कोई scoreboard publish नहीं हुआ। ऊपर Add Result से जोड़ें।</td></tr>'
    body+='</table></div><h2>Verified Registration Winners & Payouts</h2><div class="tablewrap"><table><tr><th>Player</th><th>Tournament</th><th>Reward</th><th>Winner</th><th>Payout</th><th>Actions</th></tr>'
    for x in rows:body+=f'''<tr><td>{html.escape(x['username'] or 'Player')}<br><small>{html.escape(x['email'])}</small></td><td>{html.escape(x['title'])}<br><small>{html.escape(x['game'])}</small></td><td>₹{x['prize_pool']}</td><td>{html.escape(x['winner_status'] or 'Not set')}</td><td>{html.escape(x['payout_status'])}</td><td><div class="row"><form method="post"><input type="hidden" name="registration_id" value="{x['id']}"><input type="hidden" name="action" value="winner"><button>Set Winner</button></form><form method="post" onsubmit="return confirm('Mark payout paid only after transfer?')"><input type="hidden" name="registration_id" value="{x['id']}"><input type="hidden" name="action" value="payout"><button class="secondary">Mark Paid</button></form></div></td></tr>'''
    body+='</table></div>'
    return shell('Results','results',body)

@app.route('/announcements',methods=['GET','POST'])
def announcements():
    r=need_login()
    if r:return r
    c=db()
    if request.method=='POST':
        action=request.form.get('action','create')
        try:
            if action=='create':
                title=request.form.get('title','').strip()[:120]; message=request.form.get('message','').strip()[:3000]; image=request.form.get('image_url','').strip()[:1000]
                if not title or not message: flash('Title और message जरूरी हैं।')
                else:
                    c.execute('INSERT INTO announcements(title,message,image_url) VALUES(?,?,?)',(title,message,image)); c.execute('INSERT INTO admin_audit(admin_name,action,details) VALUES(?,?,?)',(session.get('admin_name','Admin'),'Announcement created',title)); c.commit(); flash('Announcement publish हो गया।')
            elif action=='toggle':
                aid=int(request.form.get('id','0')); c.execute('UPDATE announcements SET active=CASE active WHEN 1 THEN 0 ELSE 1 END WHERE id=?',(aid,)); c.execute('INSERT INTO admin_audit(admin_name,action,details) VALUES(?,?,?)',(session.get('admin_name','Admin'),'Announcement visibility changed',str(aid))); c.commit(); flash('Announcement status बदला।')
            elif action=='banner':
                title=request.form.get('title','').strip()[:120]; image=request.form.get('image_url','').strip()[:1000]; link=request.form.get('link_url','/tournaments').strip()[:1000]
                uploaded=request.files.get('banner_file')
                if uploaded and uploaded.filename:
                    ext=Path(uploaded.filename).suffix.lower()
                    if ext not in ALLOWED_IMAGE_EXTS: raise ValueError('केवल PNG, JPG, WEBP या GIF image upload करें।')
                    safe=secure_filename(uploaded.filename)
                    filename=f'banner_{int(time.time())}_{safe}'
                    uploaded.save(UPLOADS/filename); image='/uploads/'+filename
                if image: c.execute('INSERT INTO banners(title,image_url,link_url) VALUES(?,?,?)',(title,image,link)); c.commit(); flash('Banner add हुआ।')
                else: flash('Banner image URL या upload file जरूरी है।')
        except (ValueError,sqlite3.Error): c.rollback(); flash('Save नहीं हुआ।')
        return redirect(url_for('announcements'))
    rows=c.execute('SELECT * FROM announcements ORDER BY id DESC').fetchall(); bs=c.execute('SELECT * FROM banners ORDER BY id DESC').fetchall()
    body='''<h1>Announcements & Banners</h1><div class="two"><section class="card"><h2>Publish Announcement</h2><form method="post"><input type="hidden" name="action" value="create"><label>Title</label><input name="title" maxlength="120" required><label>Message</label><textarea name="message" maxlength="3000" required></textarea><label>Optional Image URL</label><input name="image_url"><button>Publish</button></form></section><section class="card"><h2>Add Home Banner</h2><form method="post" enctype="multipart/form-data"><input type="hidden" name="action" value="banner"><label>Title</label><input name="title"><label>Image URL (optional if uploading)</label><input name="image_url"><label>Upload image (PNG/JPG/WEBP/GIF)</label><input type="file" name="banner_file" accept="image/png,image/jpeg,image/webp,image/gif"><label>Click Link</label><input name="link_url" value="/tournaments"><button>Add Banner</button></form><p class="muted">URL banners are supported. For cross-service uploads use persistent shared storage.</p></section></div><h2>Announcements</h2><div class="tablewrap"><table><tr><th>Title</th><th>Message</th><th>Status</th><th>Action</th></tr>'''
    for x in rows: body+=f'<tr><td>{html.escape(x["title"])}</td><td>{html.escape(x["message"])}</td><td>{"Active" if x["active"] else "Hidden"}</td><td><form method="post"><input type="hidden" name="action" value="toggle"><input type="hidden" name="id" value="{x["id"]}"><button>Toggle</button></form></td></tr>'
    body+='</table></div><h2>Banners</h2><div class="tablewrap"><table><tr><th>Title</th><th>Image</th><th>Link</th></tr>'
    for b in bs: body+=f'<tr><td>{html.escape(b["title"] or "Banner")}</td><td><a href="{html.escape(b["image_url"])}" target="_blank" rel="noopener">Open image</a></td><td>{html.escape(b["link_url"] or "")}</td></tr>'
    body+='</table></div>'
    return shell('Announcements','announcements',body)

@app.route('/reports',methods=['GET','POST'])
def reports():
    r=need_login()
    if r:return r
    c=db()
    if request.method=='POST':
        rid=int(request.form.get('report_id','0')); status=request.form.get('status','Reviewed'); note=request.form.get('admin_note','').strip()[:1000]
        if status not in ('Open','Reviewed','Resolved','Rejected'): status='Reviewed'
        c.execute('UPDATE reports SET status=?,admin_note=? WHERE id=?',(status,note,rid)); c.execute('INSERT INTO admin_audit(admin_name,action,details) VALUES(?,?,?)',(session.get('admin_name','Admin'),'Report updated',f'{rid}: {status}')); c.commit(); flash('Report update हो गई।'); return redirect(url_for('reports'))
    rows=c.execute('SELECT r.*,u.username,u.email FROM reports r JOIN users u ON u.id=r.user_id ORDER BY r.id DESC').fetchall()
    body='<h1>Player Reports & Disputes</h1><div class="tablewrap"><table><tr><th>Player</th><th>Category / Details</th><th>Status</th><th>Update</th></tr>'
    for x in rows: body+=f'<tr><td>{html.escape(x["username"] or "Player")}<br><small>{html.escape(x["email"])}</small></td><td>{html.escape(x["category"])}<br>{html.escape(x["details"])}</td><td>{html.escape(x["status"])}</td><td><form method="post"><input type="hidden" name="report_id" value="{x["id"]}"><select name="status"><option>Open</option><option>Reviewed</option><option>Resolved</option><option>Rejected</option></select><textarea name="admin_note" placeholder="Admin note">{html.escape(x["admin_note"] or "")}</textarea><button>Save</button></form></td></tr>'
    body+='</table></div><h2>Admin Activity Log</h2><div class="tablewrap"><table><tr><th>Time</th><th>Admin</th><th>Action</th><th>Details</th></tr>'
    for x in c.execute('SELECT * FROM admin_audit ORDER BY id DESC LIMIT 100').fetchall(): body+=f'<tr><td>{x["created_at"]}</td><td>{html.escape(x["admin_name"] or "Admin")}</td><td>{html.escape(x["action"])}</td><td>{html.escape(x["details"] or "")}</td></tr>'
    body+='</table></div>'
    return shell('Reports & Audit','reports',body)

@app.route('/messages',methods=['GET','POST'])
def messages():
    r=need_login()
    if r:return r
    c=db()
    selected=request.args.get('user_id','').strip()
    if request.method=='POST':
        try:
            uid=int(request.form.get('user_id','0')); msg=request.form.get('message','').strip()[:2000]
            user=c.execute('SELECT id,username,email FROM users WHERE id=?',(uid,)).fetchone()
            if not user or not msg: flash('Player और message सही भरें।')
            else:
                c.execute("INSERT INTO support_messages(user_id,sender_role,sender_id,message) VALUES(?,'admin',?,?)",(uid,session['admin_id'],msg))
                c.execute('INSERT INTO user_notifications(user_id,message) VALUES(?,?)',(uid,'Admin Support ने आपके message का जवाब दिया है।'))
                c.execute('INSERT INTO admin_audit(admin_name,action,details) VALUES(?,?,?)',(session.get('admin_name','Admin'),'Replied to player support chat',f'user_id={uid}'))
                c.commit(); flash('जवाब खिलाड़ी को भेज दिया गया।'); return redirect(url_for('messages',user_id=uid))
        except (ValueError,sqlite3.Error) as e:
            c.rollback(); flash('Message नहीं भेजा गया: '+str(e))
        return redirect(url_for('messages',user_id=selected))
    people=c.execute("SELECT u.id,u.username,u.email,MAX(sm.created_at) last_message,SUM(CASE WHEN sm.sender_role='user' AND sm.seen=0 THEN 1 ELSE 0 END) unread,COUNT(sm.id) message_count FROM users u JOIN support_messages sm ON sm.user_id=u.id GROUP BY u.id,u.username,u.email ORDER BY MAX(sm.id) DESC").fetchall()
    body='<h1>Player Inbox · Admin Support Chat</h1><p class="muted">यहाँ players के messages पढ़ें और सीधे जवाब दें। यह in-app chat है; live push notification नहीं है।</p><div class="two"><section class="card"><h2>Conversations</h2>'
    for person in people:
        body+=f'<div class="card"><b>{html.escape(person["username"] or "Player")}</b><div class="muted">{html.escape(person["email"])} · {person["message_count"]} messages</div><div class="muted">Unread: {person["unread"] or 0}</div><a class="btn" href="{url_for("messages",user_id=person["id"])}">Open Chat</a></div>'
    if not people: body+='<p class="muted">अभी किसी खिलाड़ी ने Admin Chat नहीं किया।</p>'
    body+='</section><section class="card"><h2>Conversation</h2>'
    if selected.isdigit():
        uid=int(selected); user=c.execute('SELECT id,username,email FROM users WHERE id=?',(uid,)).fetchone()
        if user:
            c.execute("UPDATE support_messages SET seen=1 WHERE user_id=? AND sender_role='user'",(uid,)); c.commit()
            rows=c.execute('SELECT * FROM support_messages WHERE user_id=? ORDER BY id ASC LIMIT 200',(uid,)).fetchall()
            body+=f'<p><b>{html.escape(user["username"] or "Player")}</b><br><span class="muted">{html.escape(user["email"])}</span></p>'
            for m in rows:
                who='Player' if m['sender_role']=='user' else 'Admin'
                body+=f'<div class="card"><b>{who}</b><p>{html.escape(m["message"])}</p><small class="muted">{html.escape(m["created_at"])}</small></div>'
            body+=f'<form method="post"><input type="hidden" name="user_id" value="{uid}"><label>Reply to player</label><textarea name="message" maxlength="2000" required></textarea><button>Send Reply</button></form>'
        else: body+='<p class="muted">Player नहीं मिला।</p>'
    else: body+='<p class="muted">बाईं तरफ किसी conversation पर Open Chat दबाएँ।</p>'
    body+='</section></div>'
    return shell('Player Inbox','messages',body)

@app.route('/settings',methods=['GET','POST'])
def settings():
    r=need_login()
    if r:return r
    if request.method=='POST':
        old=request.form.get('old_password',''); new=request.form.get('new_password',''); confirm=request.form.get('confirm_password',''); row=db().execute('SELECT * FROM admin_accounts WHERE id=?',(session['admin_id'],)).fetchone()
        if not check_password_hash(row['password_hash'],old):flash('Current password सही नहीं है।')
        elif len(new)<10:flash('नया पासवर्ड कम से कम 10 characters का रखें।')
        elif new!=confirm:flash('नए पासवर्ड match नहीं हुए।')
        else:db().execute('UPDATE admin_accounts SET password_hash=? WHERE id=?',(generate_password_hash(new),session['admin_id']));db().commit();flash('Admin password बदल गया।')
        return redirect(url_for('settings'))
    body='''<h1>Settings & Security</h1><div class="two"><section class="card"><h2>Change Admin Password</h2><form method="post"><label>Current password</label><input type="password" name="old_password" required><label>New password (10+ characters)</label><input type="password" name="new_password" minlength="10" required><label>Confirm new password</label><input type="password" name="confirm_password" minlength="10" required><button>Update Password</button></form></section><section class="card"><h2>Shared Database</h2><p class="muted">Database file:</p><code>vortex_arena_users.db</code><p class="muted">इस Python file को user app के उसी folder में रखें। दोनों apps को एक ही SQLite database दिखेगा। पहले backup लें और public internet पर बिना production security के expose न करें।</p><p class="muted">First-run login: <b>admin</b> / <b>ChangeMe-123!</b>. तुरंत password बदलें।</p></section></div>'''
    return shell('Settings','settings',body)

init_db()
def open_browser():time.sleep(1.2);webbrowser.open('http://127.0.0.1:8083')
if __name__=='__main__':
    print('\nVORTEX ARENA ADMIN PANEL')
    print('Open: http://127.0.0.1:8083')
    print('First login: admin / ChangeMe-123!  (change password in Settings immediately)')
    print('Database:',DB)
    threading.Thread(target=open_browser,daemon=True).start()
    app.run(host='127.0.0.1',port=8083,debug=False)
