VORTEX ARENA - PHONE + BANNER + TOURNAMENT UPDATE

Files:
- user_app.py
- admin_panel.py

Changes in this update:
1. Corrected WhatsApp Support phone to 8796674832 (one 4, not double 4).
   WhatsApp link: https://wa.me/918796674832
2. Added Admin > Banners page.
   - Add banner title/name.
   - Upload a PNG/JPG/JPEG/WEBP/GIF banner (up to the app's 4 MB request limit) or enter an image URL.
   - Set an optional click destination.
   - Hide/show or delete saved banners.
   - Active banners are read by the User Home page from the shared SQLite table.
3. Tournament form supports banner image upload or URL. Existing edit and delete actions remain.
4. Deleting a tournament also deletes its registrations and result rows, so the deleted tournament does not continue to appear from those linked records.
5. Existing tables are retained; this update does not DROP existing database tables.

Important deployment notes:
- Keep user_app.py and admin_panel.py in the same directory if you want their SQLite DB files to be shared. Both use vortex_arena_users.db beside the scripts.
- Uploaded images are stored in vortex_uploads beside the scripts. On ephemeral hosting storage, uploaded images may be lost after redeploy/restart unless persistent disk storage is configured.
- This ZIP contains Python source, not an APK.
- Python syntax checks passed. Full Flask/browser/runtime test was not performed in this environment.
- Change default admin credentials and set a strong stable VORTEX_SECRET_KEY before public deployment.
