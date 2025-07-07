from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

import schemas
from repositories.dishes import DishTypeRepository
from database import get_db

router = APIRouter()

def get_repo(db: Session = Depends(get_db)) -> DishTypeRepository:
    return DishTypeRepository(db=db)

@router.post("", response_model=schemas.DishType)
def create_dish_type(
    dish_create: schemas.DishTypeCreate, # 이 변수 이름은 그대로 둡니다.
    repo: DishTypeRepository = Depends(get_repo)
):
    # repo.create() 를 호출할 때 사용하는 키워드를 수정합니다.
    # dish_create=  ->  dish_type_create=
    return repo.create(dish_type_create=dish_create) # 이 부분을 수정하세요.

@router.get("", response_model=List[schemas.DishType])
def get_all_dish_types(repo: DishTypeRepository = Depends(get_repo)):
    return repo.get_all()