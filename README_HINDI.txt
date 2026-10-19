VORTEX ARENA — ADMIN + USER PANEL

Files: user_app.py, admin_panel.py, requirements.txt
Install: pip install -r requirements.txt
Run user: python user_app.py
Run admin: python admin_panel.py

Both panels must use the same VORTEX_DB_PATH and persistent database file. Keep a backup of your existing database before deployment. Do not delete the old database.

Admin Shop & Spin Manager: after admin login open /shop-manager to add/toggle/delete spin rewards and add/toggle shop items. Existing tournament, challenges, POPS, live, results, notifications routes are retained in the supplied panel source.

Important: Test on a copy/staging deployment first. This ZIP was syntax-checked only; full Flask/runtime integration and shared-database deployment have not been verified here.


UPDATE v3 (additive changes):
- Admin + User panel files both included; existing routes and tables retained.
- Admin Shop & Lucky Spin Manager can add rewards and show/hide them; Hide does not delete a reward record.
- First spin is free once per account; later spins cost 50 Coins or 10 Diamonds.
- Exchange rate: 10 Diamonds = 20 Coins and 20 Coins = 10 Diamonds.
- Keep the existing database file and back it up before deployment.
- This package passed Python syntax compilation; it has not been fully runtime-tested against your live Render database.
