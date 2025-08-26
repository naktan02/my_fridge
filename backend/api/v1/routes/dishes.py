from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

# 'schemas' 모듈 전체를 가져오도록 수정합니다.
import schemas
from repositories.dishes import DishTypeRepository
from database import get_db

router = APIRouter()

def get_repo(db: Session = Depends(get_db)) -> DishTypeRepository:
    return DishTypeRepository(db=db)

# response_model을 명확하게 schemas.dish.DishType으로 지정합니다.
@router.post("", response_model=schemas.dish.DishType)
def create_dish_type(
    dish_create: schemas.dish.DishTypeCreate, 
    repo: DishTypeRepository = Depends(get_repo)
):
    return repo.create(dish_type_create=dish_create) 

# response_model을 명확하게 List[schemas.dish.DishType]으로 지정합니다.
@router.get("", response_model=List[schemas.dish.DishType])
def get_all_dish_types(repo: DishTypeRepository = Depends(get_repo)):
    return repo.get_all()
