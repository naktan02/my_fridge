from datetime import date
from typing import Optional
from pydantic import BaseModel

# 기본 재료 스키마
class IngredientBase(BaseModel):
    name: str

class IngredientCreate(IngredientBase):
    pass

class Ingredient(IngredientBase):
    id: int

    class Config:
        from_attributes = True

# 사용자가 소유한 재료 스키마
class UserIngredientBase(BaseModel):
    ingredient_name: str
    expiration_date: Optional[date] = None

class UserIngredientCreate(UserIngredientBase):
    pass

class UserIngredient(UserIngredientBase):
    id: int
    ingredient: Ingredient # 관계를 표시

    class Config:
        from_attributes = True