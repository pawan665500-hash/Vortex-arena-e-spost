VORTEX ARENA UPDATE PACKAGE

Included:
- User Panel source: user_app.py
- Admin Panel source: admin_panel.py
- Single-service WSGI dispatcher: wsgi.py
- requirements.txt
- Deployment/readme files
- assets/Vortex_Arena_Tournament_Banner.png (sample tournament banner)

Important:
1. This ZIP is source code for upload/deployment; it does not update Render automatically.
2. Back up your current GitHub files and database before replacing files.
3. Deploy both panels through the same Render service using wsgi.py if they must share a local database/uploads directory. Separate Render services do not automatically share local SQLite files.
4. Set a strong VORTEX_SECRET_KEY in Render environment variables and change any default admin credentials before public use.
5. The banner image is a sample design. It contains sample tournament details; change the date, prize pool, entry fee, map and slots in an image editor before publishing, or upload a clean banner and enter the real details in Admin.
6. UTR must be manually verified against the actual payment record by Admin. Never unlock room details just because a UTR string was submitted.
7. Syntax validation only; this package has not been runtime-tested on Render. Test with a backup/staging deployment before replacing your live app.
8. No existing database should be deleted. Keep your current database backup before deployment.
