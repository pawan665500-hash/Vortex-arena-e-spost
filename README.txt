VORTEX ARENA — UPDATED FILES

Included:
- user_app.py: normalizes common UTR copy/paste artifacts (spaces, hyphens, quote characters) and removes the arbitrary rule requiring five distinct characters. Duplicate references are still rejected. Format checks do NOT verify bank payment.
- admin_panel.py: adds a tournament banner photo chooser while retaining the image URL field and the other admin features. Uploaded art is served from /uploads/ and is used by the User Panel.

Install:
1. Download/extract the ZIP.
2. Replace the existing user_app.py and admin_panel.py in your GitHub repository with these files. If wsgi.py imports different module names, keep the filenames it expects or update those imports.
3. Commit the replacements to GitHub and wait for Render deployment to finish.
4. Test with a non-sensitive test image and confirm it appears in the User Panel.

Important deployment caveats:
- The admin and user files use a local SQLite database next to each file. Separate Render services do not share local SQLite databases or uploaded image folders. Both panels must be wired into the same service/shared storage, or use a shared external database and image hosting.
- Render ephemeral files may disappear on restart/redeploy. For durable uploads, configure a persistent disk mounted to the upload folder or use external image hosting. If admin and user are separate services, this local upload route alone cannot serve the photo to both.
- Do not commit your database, passwords, or secret keys to GitHub. Set a strong VORTEX_ADMIN_PASSWORD and stable VORTEX_SECRET_KEY in Render. Change the admin password immediately.
