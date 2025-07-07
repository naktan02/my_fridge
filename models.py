from sqlalchemy import Column, Integer, String, Text, Date, ForeignKey
from database import Base

class DishType(Base):
    __tablename__ = 'dish_types'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text)

class Ingredient(Base):
    __tablename__ = 'ingredients'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False) # 예: '돼지고기', '양파'

class UserIngredient(Base):
    __tablename__ = 'user_ingredients'
    id = Column(Integer, primary_key=True, index=True)
    # user_id = Column(Integer, ...) # 나중에 사용자 인증 기능 추가 시 활성화
    ingredient_id = Column(Integer, ForeignKey('ingredients.id'))
    expiration_date = Column(Date, nullable=True) # 유통기한