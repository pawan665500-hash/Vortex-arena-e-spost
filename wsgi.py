"""Combined WSGI entry point for Vortex Arena User + Admin panels on Render."""
import os
from werkzeug.middleware.dispatcher import DispatcherMiddleware
import user_app
import admin_panel

# Use one stable secret in Render Environment Variables.
secret = os.environ.get("VORTEX_SECRET_KEY")
if not secret:
    # Helpful for local testing only. On Render, set VORTEX_SECRET_KEY explicitly.
    secret = "local-only-change-this-secret-before-deploying"
user_app.app.secret_key = secret
admin_panel.app.secret_key = secret

# Keep the two Flask session cookies separate.
admin_panel.app.config["SESSION_COOKIE_NAME"] = "vortex_admin_session"

# Create/upgrade the shared SQLite schema, then seed the sample tournaments.
user_app.init_db()
admin_panel.init_db()

# User panel is at /; admin panel is mounted under /admin.
application = DispatcherMiddleware(user_app.app, {"/admin": admin_panel.app})
