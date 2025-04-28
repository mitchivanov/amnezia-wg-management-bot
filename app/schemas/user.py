from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

class UserBase(BaseModel):
    """Базовая схема пользователя с общими полями"""
    telegram_id: int = Field(..., description="Telegram ID пользователя")
    is_promo_user: bool = Field(default=False, description="Флаг промо-пользователя")

class UserCreate(UserBase):
    """Схема для создания пользователя"""
    pass

class SubscriptionInfo(BaseModel):
    """Информация о подписке пользователя"""
    status: str = Field(..., description="Статус подписки")
    start_date: Optional[datetime] = Field(None, description="Дата начала подписки")
    expiry_date: Optional[datetime] = Field(None, description="Дата окончания подписки")
    payment_id: Optional[str] = Field(None, description="ID платежа")
    is_active: bool = Field(..., description="Активна ли подписка")
    days_left: int = Field(0, description="Дней до окончания подписки")

class UserResponse(UserBase):
    """Полная информация о пользователе для ответов API"""
    subscription_status: str
    subscription_start_date: Optional[datetime] = None
    subscription_expiry_date: Optional[datetime] = None
    payment_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    @property
    def subscription(self) -> SubscriptionInfo:
        """Представление информации о подписке в удобном формате"""
        is_active = (
            self.subscription_status == "active" and 
            self.subscription_expiry_date and 
            self.subscription_expiry_date > datetime.utcnow()
        )
        
        days_left = 0
        if is_active:
            delta = self.subscription_expiry_date - datetime.utcnow()
            days_left = max(0, delta.days)
            
        return SubscriptionInfo(
            status=self.subscription_status,
            start_date=self.subscription_start_date,
            expiry_date=self.subscription_expiry_date,
            payment_id=self.payment_id,
            is_active=is_active,
            days_left=days_left
        )
    
    class Config:
        orm_mode = True

class UserUpdate(BaseModel):
    """Схема для обновления данных пользователя"""
    is_promo_user: Optional[bool] = None

class SubscriptionCreate(BaseModel):
    """Схема для создания/активации подписки"""
    days: int = Field(..., description="Количество дней подписки")
    payment_id: Optional[str] = Field(None, description="ID платежа")

class SubscriptionUpdate(BaseModel):
    """Схема для обновления подписки"""
    days_to_add: Optional[int] = Field(None, description="Дней для добавления к подписке")
    payment_id: Optional[str] = Field(None, description="Новый ID платежа") 