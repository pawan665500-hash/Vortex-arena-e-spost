VORTEX ARENA UPDATED VERSION — ADMIN + USER PANELS

Files:
- user_app.py: User Panel (default http://127.0.0.1:8082)
- admin_panel.py: Admin Panel (default http://127.0.0.1:8083)

NEW ADDITIONS:
- Shop page: /shop (login required)
- Admin Shop Manager: /shop-manager (admin login required)
- Item types include Player Card, Avatar Frame, Profile Banner, Rank Badge, Theme, Bundles and cosmetics.
- Admin can set image URL/upload, price, currency (Points/Coins/Diamonds), duration and stock.
- Inventory and equip Player Card action.
- Lucky Spin costs 500 Coins; rewards are weighted random and the shop page shows the calculated relative probabilities.
- Up to five active banners are displayed in Shop; manage banners from existing Admin > Banners.
- Additive SQLite schema changes only; existing tables/data are not deleted by these additions.

IMPORTANT:
1. Keep both Python files in the SAME folder so both panels use the same vortex_arena_users.db and vortex_uploads folder.
2. Install Flask on the device/server: python -m pip install flask
3. Run user_app.py and admin_panel.py in separate terminals/processes.
4. Default admin login (if no admin account already exists): admin / ChangeMe-123! Change it immediately in Admin Settings.
5. This package passed Python syntax compilation. Runtime route testing was unavailable in the build environment because Flask is not installed and network access to install it was unavailable. Please test in your Python/Render environment before using with real balances.
6. Coins and Diamonds are separate balances; this update does not sell Diamonds for real money or verify payments.
