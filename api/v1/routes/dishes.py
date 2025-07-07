from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from schemas import dish
from repositories.dishes import DishTypeRepository
from database import get_db

router = APIRouter()

def get_repo(db: Session = Depends(get_db)) -> DishTypeRepository:
    return DishTypeRepository(db=db)

@router.post("", response_model=dish.DishType)
def create_dish_type(
    dish_create: dish.DishTypeCreate, 
    repo: DishTypeRepository = Depends(get_repo)
):
    return repo.create(dish_type_create=dish_create) 

@router.get("", response_model=List[dish.DishType])
def get_all_dish_types(repo: DishTypeRepository = Depends(get_repo)):
    return repo.get_all()