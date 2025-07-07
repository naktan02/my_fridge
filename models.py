from sqlalchemy import Column, Integer, String, Text
from database import Base

class DishType(Base):
    __tablename__ = 'dish_types'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text)