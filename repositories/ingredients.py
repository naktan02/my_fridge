# repositories/ingredients.py
from sqlalchemy.orm import Session
import models
from schemas import ingredient

class IngredientRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_or_create(self, name: str) -> models.Ingredient:
        """재료를 찾고, 없으면 메모리에만 추가합니다 (커밋 없음)."""
        db_ingredient = self.db.query(models.Ingredient).filter(models.Ingredient.name == name).first()
        if not db_ingredient:
            db_ingredient = models.Ingredient(name=name)
            self.db.add(db_ingredient)
            # self.db.commit()  <- 이 줄을 제거하거나 주석 처리
            # self.db.refresh(db_ingredient) <- 커밋 전에는 refresh 할 수 없으므로 제거
        return db_ingredient

    def add_user_ingredient(self, user_id: int, ingredient_create: ingredient.UserIngredientCreate) -> models.UserIngredient:
        """사용자의 냉장고에 재료를 추가합니다."""
        db_ingredient = self.get_or_create(name=ingredient_create.ingredient_name)
        db_user_ingredient = models.UserIngredient(
            ingredient_id=db_ingredient.id,
            expiration_date=ingredient_create.expiration_date
        )
        self.db.add(db_user_ingredient)
        self.db.commit()
        self.db.refresh(db_user_ingredient)
        return db_user_ingredient