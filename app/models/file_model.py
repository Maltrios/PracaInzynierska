from database import Base
from sqlalchemy import Column, Integer, String, DateTime, func, BIGINT, ForeignKey


class UserFile(Base):
    __tablename__= "user_files"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    filename = Column(String, nullable=False)
    storage_path = Column(String, nullable=False)
    size_bytes = Column(BIGINT)
    expires_at = Column(DateTime(timezone=True))
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
