"""Single Render web service: User Panel at / and Admin Panel at /admin."""
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from user_app import app as user_app
from admin_panel import app as admin_app

application = DispatcherMiddleware(user_app, {
    "/admin": admin_app,
})
