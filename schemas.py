from pydantic import BaseModel
from typing import Optional
from datetime import date

class DishTypeBase(BaseModel):
    name: str
    description: Optional[str] = None

class DishTypeCreate(DishTypeBase):
    pass

class DishType(DishTypeBase):
    id: int

    class Config:
        from_attributes = True

class UserIngredientBase(BaseModel):
    ingredient_name: str
    expiration_date: Optional[date] = None

class UserIngredientCreate(UserIngredientBase):
    pass

class UserIngredient(UserIngredientBase):
    id: int
    ingredient_id: int

    class Config:
        from_attributes = True