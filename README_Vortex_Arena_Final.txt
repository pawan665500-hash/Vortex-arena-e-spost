VORTEX ARENA — FULL FEATURE RELEASE PACKAGE
===========================================

PACKAGE FILES
-------------
- user_app.py: existing player panel, updated additively
- admin_panel.py: existing admin panel, updated additively
- requirements.txt: Flask dependency

NO-DELETE UPDATE POLICY
-----------------------
This release keeps the existing routes and uses CREATE TABLE IF NOT EXISTS plus ALTER TABLE
for additive database migrations. It does not issue DROP TABLE commands. Back up your database
before replacing files, as with any application update.

RUN LOCALLY
-----------
1. Install Python 3.12 or newer (the source uses Python 3.12 f-string syntax).
2. Run: python -m pip install -r requirements.txt
3. In terminal 1 run: python user_app.py
4. In terminal 2 run: python admin_panel.py
5. Open the URLs shown in the terminal. User panel uses port 8082; Admin uses port 8083.
6. Keep both apps and the database in the same folder for a local SQLite setup.
7. For a single Render service, use a proper WSGI deployment and configure its start command/PORT; separate Render services cannot share a local SQLite file automatically.

FIRST ADMIN LOGIN
-----------------
Username: admin
Password: ChangeMe-123!
Change it immediately in Admin > Settings. On first deployment, set VORTEX_ADMIN_USER and
VORTEX_ADMIN_PASSWORD before the database is created if you want different initial credentials.

FEATURES
--------
USER PANEL
- Existing signup/login, hashed passwords, persistent login session, profile, avatar upload.
- Permanent Vortex Arena Player ID, game profile, rank points, match performance and history.
- Home swipeable Banner Slider and announcements; tournament filters for Free, Upcoming and Live events.
- Tournament listings with game, map, mode, team size, fee, prize, timing and image.
- UPI payment intent and UTR submission; duplicate UTR check; registration status.
- My Matches, numbered team slots, countdown, and Room ID/password gated to verified users and
  configured release time.
- Results/scoreboard, player leaderboard, rank history, medals/achievements, monthly points and
  win-streak-related display where data is available.
- Squad Finder, team creation, Join Requests, leader accept/reject, basic team chat, Add Me requests,
  direct player messages/inbox and in-app notifications.
- NEW: direct in-app Admin Support Chat. Players can send support/dispute messages from the User
  Panel; Admin can open conversations, read messages and reply in Admin > Player Inbox.
- Reports/help, WhatsApp support, Discord invite and YouTube channel links.

ADMIN PANEL
- Dashboard and player management.
- Tournament create/edit/delete with Free Fire/BGMI map/mode/team-size options, banner URL,
  banner image upload, entry fee, prize, team slots, timing, room ID/password, countdown and stream URL.
- UTR review with manual Accept/Reject; verified registration slots are assigned in registration order.
- Results publishing, winner/payout status, rank/point control, point history, announcements,
  banners, reports/disputes, audit log and password change.
- NEW: Player Inbox for the direct Admin Support Chat, unread message counts, and reply notifications.

RANK / REWARD RULES
-------------------
Bronze 0–199; Silver 200–399; Gold 400–999; Diamond 1000–2499; Master 2500–2999;
Master Right 3000+.

Result points in this code are configured as winner +100, loss -10, highest-kill matched player +25 MVP.
The scoreboard uses player-name matching against registered username, Arena ID, player UID, game UID,
or email. Review the scoreboard and identity matching before publishing official rewards. Re-saving a
scoreboard attempts to reverse previous awards and apply corrected awards; test this on a backup first.

Master Right eligibility lasts 30 days after the account crosses 3000 points, and entry fee up to ₹10
can be waived while the eligibility date is active. Admin manual point changes are recorded in history.

CONTACTS CONFIGURED
-------------------
Contact number: 8796674832
UPI ID: 8796674832@fam
WhatsApp support: https://wa.me/9187966744832
Discord invite: https://discord.gg/pY9dvhaxs
YouTube: https://youtube.com/@smaltanime_00

IMPORTANT LIMITATIONS / DEPLOYMENT
---------------------------------
- This is a Flask web app, not a compiled Android APK. The ZIP contains the source code.
- Full live browser/runtime testing could not be completed in this build environment because Flask
  could not be installed here (package network access was unavailable). Both Python files pass
  py_compile syntax checks. A local SQLite logic test is included in the build verification, but this
  is not a substitute for installing requirements and testing every page end-to-end.
- Player chat, team chat and Admin Support Chat are database-backed page-based chats, not real-time
  WebSocket chat. Refresh the page to see new messages. In-app notifications are not SMS/push.
- UTR verification is manual; there is no bank/UPI API connection. Check actual transaction records.
- Prize payout status is an admin record; it does not transfer money automatically.
- 12 teams × 4 players is configured by setting 12 team slots and team size 4. Verified registrations
  receive numbered slots in verification order. This is not an automatic balanced team draft.
- Banner/avatar uploads use filesystem storage. A local/shared persistent upload directory is needed.
- Two separate Render services do not share local SQLite or uploaded files automatically. Use a
  genuinely shared persistent filesystem or migrate both panels to the same managed database and
  shared object storage. Set VORTEX_DB_PATH and VORTEX_UPLOADS_DIR consistently where applicable.
- Set the same strong, stable VORTEX_SECRET_KEY on deployments and use HTTPS in production.
- Back up vortex_arena_users.db before installing an update. Do not announce a public tournament until
  registration, payment review, room release, results and payout flow have been tested end-to-end.
