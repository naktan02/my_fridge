# /backend/models.py (최종 수정안)

from sqlalchemy import (
    Column, Integer, String, Date, ForeignKey, Boolean, Text, DateTime,
    func
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import ARRAY
from database import Base

# --- 중간 테이블 (M:N 관계) ---
class RecipeIngredient(Base):
    __tablename__ = "recipe_ingredients"
    recipe_id = Column(Integer, ForeignKey("recipes.id"), primary_key=True)
    ingredient_id = Column(Integer, ForeignKey("ingredients.id"), primary_key=True)
    quantity_display = Column(String) # e.g., "300g", "1/2개"

    ingredient = relationship("Ingredient")

# --- 메인 테이블 ---
class User(Base):
    # ... (is_admin을 제외한 개인정보 관련 필드만 유지)
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    
    ingredients = relationship("UserIngredient", back_populates="owner")


class Ingredient(Base):
    __tablename__ = "ingredients"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    category = Column(String, nullable=True)
    storage_type = Column(String, nullable=True)

class Dish(Base):
    __tablename__ = "dishes"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    cuisine_type = Column(String, nullable=True) # 한식, 중식, 양식 등
    semantic_description = Column(Text, nullable=True)
    thumbnail_url = Column(String, nullable=True)
    tags = Column(ARRAY(String), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    
    recipes = relationship("Recipe", back_populates="dish")

class Recipe(Base):
    __tablename__ = "recipes"
    id = Column(Integer, primary_key=True, index=True)
    dish_id = Column(Integer, ForeignKey("dishes.id"), nullable=False)
    author = Column(String, nullable=True)
    difficulty = Column(Integer)
    serving_size = Column(String)
    cooking_time = Column(Integer) # 분 단위
    instructions = Column(Text, nullable=False)
    youtube_url = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    dish = relationship("Dish", back_populates="recipes")
    ingredients = relationship("RecipeIngredient", back_populates="recipe")

# Recipe와 RecipeIngredient 관계 설정 보완
RecipeIngredient.recipe = relationship("Recipe", back_populates="ingredients")


class UserIngredient(Base):
    __tablename__ = "user_ingredients"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    ingredient_id = Column(Integer, ForeignKey("ingredients.id"), nullable=False)
    expiration_date = Column(Date)
    
    owner = relationship("User", back_populates="ingredients")
    ingredient = relationship("Ingredient")