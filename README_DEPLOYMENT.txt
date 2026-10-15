RENDER DEPLOYMENT (PHONE-FRIENDLY)

1. Download and extract the ZIP on your phone.
2. Back up your existing GitHub repository files before replacing anything.
3. Upload these files to the repository root:
   - user_app.py
   - admin_panel.py
   - wsgi.py
   - requirements.txt
4. In the existing Render Web Service:
   - Build Command: pip install -r requirements.txt
   - Start Command: gunicorn wsgi:application
5. Set Environment Variables:
   - VORTEX_SECRET_KEY = a long random secret string
   - VORTEX_ADMIN_USER = your chosen admin username (optional for first setup)
   - VORTEX_ADMIN_PASSWORD = a unique temporary password (optional for first setup)
6. Deploy and open /admin for Admin Panel; / for User Panel.
7. Test creating one tournament, uploading a banner, opening Games/Matches, sending a User-to-Admin chat message, and replying from Admin Chat.
8. Before using real payments, verify the payment provider and review the actual UPI/bank transaction. UTR format alone does not prove payment.

Database note: user_app.py and admin_panel.py use the same VORTEX_DB_PATH. If you configure a custom path, it must point to the same file for both apps. Persistent disk is needed on Render for SQLite uploads/data to survive restarts. Never commit the .db file, secrets, or private payment records to GitHub.
