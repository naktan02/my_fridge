from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

# 'schemas' 모듈 전체를 가져오도록 수정합니다.
import schemas
from repositories.ingredients import IngredientRepository
from database import get_db

router = APIRouter()

# response_model을 새로 만든 UserIngredientResponse 스키마로 변경합니다.
@router.post("/me/ingredients", response_model=schemas.ingredient.UserIngredientResponse)
def add_my_ingredient(
    # 입력 스키마는 그대로 UserIngredientCreate를 사용합니다.
    ingredient_create: schemas.ingredient.UserIngredientCreate,
    db: Session = Depends(get_db)
):
    repo = IngredientRepository(db)
    user_id = 1  # TODO: 향후 JWT 인증을 통해 실제 사용자 ID를 가져올 부분

    try:
        # Repository의 메서드 호출 한 줄로 비즈니스 로직 처리
        db_user_ingredient = repo.add_ingredient_to_user(user_id=user_id, ingredient_data=ingredient_create)
        return db_user_ingredient
    except Exception as e:
        # Repository에서 발생한 에러를 그대로 전달
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

