from pydantic import BaseModel

class DishTypeBase(BaseModel):
    name: str

class DishTypeCreate(DishTypeBase):
    pass

class DishType(DishTypeBase):
    id: int

    class Config:
        from_attributes = True