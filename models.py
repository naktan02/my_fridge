from sqlalchemy import Column, Integer, String, Date, ForeignKey,Text
from sqlalchemy.orm import relationship
from database import Base

# ✅ 추가된 부분: 사용자 모델
# 모든 재료의 소유자를 지정하기 위해 User 모델이 필요합니다.
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)

    # User가 어떤 재료들을 가지고 있는지 알려주는 관계 설정
    ingredients = relationship("UserIngredient", back_populates="owner")


class DishType(Base):
    __tablename__ = "dish_types"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)


class Ingredient(Base):
    __tablename__ = "ingredients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)


class UserIngredient(Base):
    __tablename__ = "user_ingredients"

    id = Column(Integer, primary_key=True, index=True)
    
    # ✅ 추가된 부분: user_id 컬럼과 외래 키
    # 이 재료가 어떤 User의 것인지 알려줍니다.
    user_id = Column(Integer, ForeignKey("users.id"))
    
    ingredient_id = Column(Integer, ForeignKey("ingredients.id"))
    expiration_date = Column(Date)
    
    # ✅ 추가된 부분: 관계 설정
    # ORM이 User 모델과 UserIngredient 모델을 쉽게 연결하도록 돕습니다.
    owner = relationship("User", back_populates="ingredients")
    ingredient = relationship("Ingredient")