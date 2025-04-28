from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from models.user_models import User, SubscriptionStatus

class UserRepository:
    def __init__(self, db_session: Session):
        self.db = db_session
    
    # Create
    def create_user(self, telegram_id: int, is_promo: bool = False) -> Optional[User]:
        try:
            user = User(
                telegram_id=telegram_id,
                is_promo_user=is_promo,
                subscription_status=SubscriptionStatus.NONE.value
            )
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
            return user
        except SQLAlchemyError:
            self.db.rollback()
            return None
    
    # Read
    def get_user_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        return self.db.query(User).filter(User.telegram_id == telegram_id).first()
    
    def get_all_users(self) -> List[User]:
        return self.db.query(User).all()
    
    def get_active_subscribers(self) -> List[User]:
        now = datetime.utcnow()
        return (self.db.query(User)
                .filter(User.subscription_status == SubscriptionStatus.ACTIVE.value)
                .filter(User.subscription_expiry_date > now)
                .all())

    def get_expired_subscribers(self) -> List[User]:
        now = datetime.utcnow()
        return (self.db.query(User)
                .filter(User.subscription_status == SubscriptionStatus.ACTIVE.value)
                .filter(User.subscription_expiry_date <= now)
                .all())
    
    def get_promo_users(self) -> List[User]:
        return self.db.query(User).filter(User.is_promo_user == True).all()
    
    # Update
    def set_promo_status(self, telegram_id: int, is_promo: bool) -> Optional[User]:
        try:
            user = self.get_user_by_telegram_id(telegram_id)
            if not user:
                return None
                
            user.is_promo_user = is_promo
            
            self.db.commit()
            self.db.refresh(user)
            return user
        except SQLAlchemyError:
            self.db.rollback()
            return None
    
    def activate_subscription(
        self, 
        telegram_id: int, 
        expiry_date: datetime,
        payment_id: Optional[str] = None
    ) -> Optional[User]:
        try:
            user = self.get_user_by_telegram_id(telegram_id)
            if not user:
                return None
                
            user.subscription_status = SubscriptionStatus.ACTIVE.value
            user.subscription_start_date = datetime.utcnow()
            user.subscription_expiry_date = expiry_date
            if payment_id:
                user.payment_id = payment_id
            
            self.db.commit()
            self.db.refresh(user)
            return user
        except SQLAlchemyError:
            self.db.rollback()
            return None
    
    def deactivate_subscription(self, telegram_id: int) -> Optional[User]:
        try:
            user = self.get_user_by_telegram_id(telegram_id)
            if not user:
                return None
                
            user.subscription_status = SubscriptionStatus.EXPIRED.value
            
            self.db.commit()
            self.db.refresh(user)
            return user
        except SQLAlchemyError:
            self.db.rollback()
            return None
    
    # Delete
    def delete_user(self, telegram_id: int) -> bool:
        try:
            user = self.get_user_by_telegram_id(telegram_id)
            if not user:
                return False
                
            self.db.delete(user)
            self.db.commit()
            return True
        except SQLAlchemyError:
            self.db.rollback()
            return False
    
    # Utility methods
    def check_subscription_status(self, telegram_id: int) -> SubscriptionStatus:
        user = self.get_user_by_telegram_id(telegram_id)
        if not user:
            return SubscriptionStatus.NONE
            
        if user.subscription_status == SubscriptionStatus.ACTIVE.value:
            if user.subscription_expiry_date and user.subscription_expiry_date <= datetime.utcnow():
                # Auto-update expired subscriptions
                user.subscription_status = SubscriptionStatus.EXPIRED.value
                self.db.commit()
                return SubscriptionStatus.EXPIRED
                
            return SubscriptionStatus.ACTIVE
            
        return SubscriptionStatus(user.subscription_status)
    
    def extend_subscription(
        self, 
        telegram_id: int, 
        days: int,
        payment_id: Optional[str] = None
    ) -> Optional[User]:
        try:
            user = self.get_user_by_telegram_id(telegram_id)
            if not user:
                return None
            
            now = datetime.utcnow()
            
            # Если подписка активна, продлеваем от текущей даты окончания
            if user.has_active_subscription:
                new_expiry = user.subscription_expiry_date
            else:
                # Если подписка неактивна, начинаем с текущего момента
                user.subscription_start_date = now
                new_expiry = now
            
            # Добавляем дни
            from datetime import timedelta
            user.subscription_expiry_date = new_expiry + timedelta(days=days)
            user.subscription_status = SubscriptionStatus.ACTIVE.value
            
            if payment_id:
                user.payment_id = payment_id
            
            self.db.commit()
            self.db.refresh(user)
            return user
        except SQLAlchemyError:
            self.db.rollback()
            return None
