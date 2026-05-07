from .shared import router
from . import auth, dashboard, users, analytics, crisis, resources, letters, audit, notifications, automation

# Explicitly ensure all modules are loaded so routes are registered to 'router'
__all__ = ["router"]
