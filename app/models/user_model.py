from sqlalchemy import Column, Integer, String, DateTime, func, Boolean
from database import Base
from sqlalchemy.orm import relationship


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String,unique=True,nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)


    refresh_tokens = relationship("RefreshToken", back_populates="user")
    user_files = relationship("UserFile", back_populates="user")
    temp_files = relationship("TempFile", back_populates="user")
    user_actions = relationship("UserActions", back_populates="user")