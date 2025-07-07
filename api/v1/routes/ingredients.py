# api/v1/routes/ingredients.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import schemas
from repositories.ingredients import IngredientRepository
from database import get_db

router = APIRouter()

def get_repo(db: Session = Depends(get_db)) -> IngredientRepository:
    return IngredientRepository(db=db)

@router.post("/me/ingredients", response_model=schemas.UserIngredient)
def add_my_ingredient(
    ingredient_create: schemas.UserIngredientCreate,
    repo: IngredientRepository = Depends(get_repo)
):
    user_id = 1
    return repo.add_user_ingredient(user_id=user_id, ingredient_create=ingredient_create)