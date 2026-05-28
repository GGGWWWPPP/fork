from typing import List
from sqlalchemy.orm import Session
from app.db.models import User, UserHWID


def get_user_hwids(db: Session, user_id: int) -> List[UserHWID]:
    return db.query(UserHWID).filter(UserHWID.user_id == user_id).all()


def get_user_hwid_by_value(db: Session, user_id: int, hwid_value: str) -> UserHWID:
    return db.query(UserHWID).filter(UserHWID.user_id == user_id, UserHWID.hwid_value == hwid_value).first()


def add_user_hwid(db: Session, user_id: int, hwid_value: str) -> UserHWID:
    db_hwid = UserHWID(user_id=user_id, hwid_value=hwid_value)
    db.add(db_hwid)
    db.commit()
    db.refresh(db_hwid)
    return db_hwid


def reset_user_hwids(db: Session, user_id: int):
    db.query(UserHWID).filter(UserHWID.user_id == user_id).delete()
    db.commit()
