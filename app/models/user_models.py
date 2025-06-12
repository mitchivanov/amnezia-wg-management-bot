from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Index, UniqueConstraint, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class SubscriptionStatus(str, PyEnum):
    ACTIVE = "active"
    EXPIRED = "expired"
    NONE = "none"

# Создаем базовый класс для наших моделей
# Base = declarative_base()

# Модель тарифного плана
class SubscriptionPlan(Base):
    __tablename__ = 'subscription_plans'
    
    id = Column(Integer, primary_key=True)  # Уникальный идентификатор тарифного плана
    name = Column(String, nullable=False)  # Название тарифного плана
    location = Column(String, nullable=False) # Местоположение
    description = Column(String)  # Описание тарифного плана
    price = Column(Integer, nullable=False)  # Цена в копейках
    duration_days = Column(Integer, nullable=False)  # Длительность подписки в днях
    is_active = Column(Boolean, default=True)  # Активен ли тарифный план
    
    # Отношение с подписками пользователей
    subscriptions = relationship("UserSubscription", back_populates="plan")
    
    def __repr__(self):
        return f"<SubscriptionPlan(id={self.id}, name='{self.name}', price={self.price/100})>"

# Модель пользователя
class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)  # Уникальный идентификатор пользователя
    telegram_user_id = Column(String, nullable=False, unique=True)  # Telegram ID пользователя
    email = Column(String, nullable=False, unique=True)  # Email пользователя
    phone = Column(String, nullable=False, unique=True)  # Телефон пользователя
    # Отношение с подписками пользователя
    subscriptions = relationship("UserSubscription", back_populates="user")
    
    def __repr__(self):
        return f"<User(id={self.id}, telegram_user_id='{self.telegram_user_id}')>"

# Модель подписки пользователя
class UserSubscription(Base):
    __tablename__ = 'user_subscriptions'
    __table_args__ = (
        UniqueConstraint('user_id', 'plan_id', name='uq_user_plan'),
        Index('ix_user_subscription_status', 'status'),
        Index('ix_user_subscription_end_date', 'end_date'),
    )

    id = Column(Integer, primary_key=True)  # Уникальный идентификатор подписки
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)  # ID пользователя
    plan_id = Column(Integer, ForeignKey('subscription_plans.id'), nullable=False)  # ID тарифного плана
    start_date = Column(DateTime, nullable=False, default=lambda: datetime.now(datetime.UTC))  # Дата начала подписки
    end_date = Column(DateTime, nullable=False)  # Дата окончания подписки
    status = Column(Enum(SubscriptionStatus, name="subscription_status"), nullable=False, default=SubscriptionStatus.ACTIVE)  # Статус подписки
    reminder_sent = Column(Boolean, default=False)  # Было ли отправлено напоминание о скором окончании

    # Отношения
    user = relationship("User", back_populates="subscriptions")  # Связь с пользователем
    plan = relationship("SubscriptionPlan", back_populates="subscriptions")  # Связь с тарифным планом
    keys = relationship("UserSubscriptionKey", back_populates="subscription", cascade="all, delete-orphan")  # Связь с ключами

    def __repr__(self):
        return f"<UserSubscription(id={self.id}, user_id={self.user_id}, plan_id={self.plan_id}, status={self.status})>"

# Новая модель для хранения ключей подписки пользователя
class UserSubscriptionKey(Base):
    __tablename__ = 'user_subscription_keys'
    __table_args__ = (
        Index('ix_user_subscription_key_subscription_id', 'subscription_id'),
    )

    id = Column(Integer, primary_key=True)  # Уникальный идентификатор ключа
    subscription_id = Column(Integer, ForeignKey('user_subscriptions.id'), nullable=False)  # ID подписки
    key = Column(String, nullable=False)  # Значение ключа

    subscription = relationship("UserSubscription", back_populates="keys")  # Связь с подпиской

    def __repr__(self):
        return f"<UserSubscriptionKey(id={self.id}, subscription_id={self.subscription_id}, key={self.key})>"

# Модель для аудита изменений подписок и ключей
class AuditLog(Base):
    __tablename__ = 'audit_logs'

    id = Column(Integer, primary_key=True)  # Уникальный идентификатор записи аудита
    entity_type = Column(String, nullable=False)  # Тип сущности: 'subscription' или 'key'
    entity_id = Column(Integer, nullable=False)  # ID сущности
    action = Column(String, nullable=False)  # Действие: 'create', 'update', 'delete'
    timestamp = Column(DateTime, nullable=False, default=lambda: datetime.now(datetime.UTC))  # Время действия
    details = Column(String, nullable=True)  # Детали изменения (например, JSON или текст)

    def __repr__(self):
        return f"<AuditLog(id={self.id}, entity_type='{self.entity_type}', entity_id={self.entity_id}, action='{self.action}')>"

    # Примечание: При создании миграции убедитесь, что внешний ключ в user_subscription_keys
    # настроен с ON DELETE CASCADE на уровне базы данных для корректного каскадного удаления.
