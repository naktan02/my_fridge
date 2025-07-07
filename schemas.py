from pydantic import BaseModel
from typing import Optional

class DishTypeBase(BaseModel):
    name: str
    description: Optional[str] = None

class DishTypeCreate(DishTypeBase):
    pass

class DishType(DishTypeBase):
    id: int

    class Config:
        from_attributes = True