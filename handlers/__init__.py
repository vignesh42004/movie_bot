from handlers.admin import register_admin_handlers
from handlers.user import register_user_handlers
from handlers.callbacks import register_callback_handlers

def register_all_handlers(app):
    """Register all handlers"""
    register_admin_handlers(app)
    register_user_handlers(app)
    register_callback_handlers(app)