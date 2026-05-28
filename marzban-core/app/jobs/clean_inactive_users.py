import logging

from app import logger, scheduler
from app.db import GetDB, crud
from app.models.admin import Admin
from app.utils import report
from config import INACTIVE_USER_DELETE_DAYS

SYSTEM_ADMIN = Admin(username='system', is_sudo=True, telegram_id=None, discord_webhook=None)


def clean_inactive_users():
    if INACTIVE_USER_DELETE_DAYS <= 0:
        return

    with GetDB() as db:
        deleted_users = crud.autodelete_inactive_users(db, INACTIVE_USER_DELETE_DAYS)

        for user in deleted_users:
            report.user_deleted(user.username, SYSTEM_ADMIN,
                                user_admin=Admin.model_validate(user.admin) if user.admin else None
                                )
            logger.log(logging.INFO, "Inactive user %s deleted (inactive for > %d days)." % (user.username, INACTIVE_USER_DELETE_DAYS))


# Run every 24 hours
scheduler.add_job(clean_inactive_users, 'interval', coalesce=True, hours=24, max_instances=1)
