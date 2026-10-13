VORTEX ARENA — RENDER DEPLOY PACKAGE

Files:
- user_app.py: User Panel
- admin_panel.py: Admin Panel
- wsgi.py: starts both panels in one web service
- requirements.txt: Python dependencies

Render settings:
- New > Web Service > connect this GitHub repository
- Runtime/Language: Python 3
- Build Command: pip install -r requirements.txt
- Start Command: gunicorn wsgi:application

Environment Variables (Render > service > Environment):
- VORTEX_SECRET_KEY = use a long random secret, not a public password
- VORTEX_ADMIN_USER = choose your own admin username
- VORTEX_ADMIN_PASSWORD = choose a strong unique admin password (10+ characters)

URLs after deploy:
- User Panel: https://YOUR-SERVICE.onrender.com/
- Admin Panel: https://YOUR-SERVICE.onrender.com/admin

IMPORTANT:
1. Do not upload any existing .db database file, passwords, or private payment records to GitHub.
2. SQLite on Render's default filesystem is not persistent. This package is for a basic combined deployment test; before real users/payments, configure persistent storage or migrate the app to PostgreSQL and verify the database path/schema. Render free services may not include persistent disk storage.
3. Change UPI ID and YouTube URL in user_app.py if needed before deployment.
4. This combined entrypoint was assembled from the supplied files; test login, registration, tournament creation, UTR review, and result flows before sharing publicly.
