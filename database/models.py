from sqlalchemy import Column, Integer, String, Boolean, BigInteger, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'

    user_id = Column(BigInteger, primary_key=True)
    username = Column(String, nullable=True)
    email = Column(String, nullable=True)
    referrer_id = Column(BigInteger, nullable=True)
    marzban_username = Column(String, nullable=True)
    is_trial_used = Column(Boolean, default=False)
    is_banned = Column(Boolean, default=False)
    accepted_tos = Column(Boolean, default=False)
    subscription_end = Column(DateTime, nullable=True)

    subscriptions = relationship("Subscription", back_populates="user", cascade="all, delete-orphan", lazy="selectin")

class Subscription(Base):
    __tablename__ = 'subscriptions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey('users.user_id'))
    marzban_username = Column(String, unique=True)
    name = Column(String, default="Подписка")

    user = relationship("User", back_populates="subscriptions")


class PromoCode(Base):
    __tablename__ = 'promo_codes'

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String, unique=True, nullable=False)
    days = Column(Integer, nullable=False)         # Сколько дней добавляет
    max_uses = Column(Integer, default=1)           # Максимум активаций (0 = безлимит)
    current_uses = Column(Integer, default=0)       # Текущее кол-во использований
    is_active = Column(Boolean, default=True)
    created_by = Column(BigInteger, nullable=True)  # admin user_id
    created_at = Column(DateTime, nullable=True)


class PromoCodeUsage(Base):
    __tablename__ = 'promo_code_usages'

    id = Column(Integer, primary_key=True, autoincrement=True)
    promo_id = Column(Integer, ForeignKey('promo_codes.id'))
    user_id = Column(BigInteger, ForeignKey('users.user_id'))
    used_at = Column(DateTime, nullable=True)


class FortuneWheelSpin(Base):
    """Отслеживание прокруток колеса фортуны по рефераловым майлстоунам."""
    __tablename__ = 'fortune_spins'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey('users.user_id'))
    milestone = Column(Integer, nullable=False)    # 3, 5, 10, 15, 20, 25, 30
    prize_days = Column(Integer, nullable=False)   # Сколько дней выиграл
    spun_at = Column(DateTime, nullable=True)


class GiftCertificate(Base):
    """Подарочные сертификаты VPN."""
    __tablename__ = 'gift_certificates'

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String, unique=True, nullable=False)
    days = Column(Integer, nullable=False)
    created_by = Column(BigInteger, ForeignKey('users.user_id'))
    redeemed_by = Column(BigInteger, nullable=True)
    is_used = Column(Boolean, default=False)
    created_at = Column(DateTime, nullable=True)
    redeemed_at = Column(DateTime, nullable=True)

