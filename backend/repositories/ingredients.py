# /backend/repositories/ingredients.py (수정할 필요 없음 - 현재 상태)

from sqlalchemy.orm import Session
import models
from schemas import ingredient
from fastapi import FastAPI, HTTPException

class IngredientRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_or_create(self, name: str) -> models.Ingredient:
        """재료를 찾고, 없으면 메모리에만 추가합니다 (커밋 없음)."""
        db_ingredient = self.db.query(models.Ingredient).filter(models.Ingredient.name == name).first()
        if not db_ingredient:
            db_ingredient = models.Ingredient(name=name)
            self.db.add(db_ingredient)
            self.db.flush() # DB에 임시 반영하여 id를 얻지만, 트랜잭션은 커밋하지 않음
        return db_ingredient

    def add_ingredient_to_user(
        self, user_id: int, ingredient_data: ingredient.UserIngredientCreate
    ) -> models.UserIngredient:
        """
        '사용자에게 재료 추가' 비즈니스 로직을 하나의 트랜잭션으로 처리.
        """
        try:
            # 1. 재료 가져오거나 생성
            db_ingredient = self.get_or_create(name=ingredient_data.ingredient_name)

            # 2. 사용자 재료 모델 생성
            db_user_ingredient = models.UserIngredient(
                user_id=user_id,
                ingredient_id=db_ingredient.id,
                expiration_date=ingredient_data.expiration_date
            )
            self.db.add(db_user_ingredient)
            self.db.commit() # 모든 작업이 성공하면 여기서 한 번만 커밋
            self.db.refresh(db_user_ingredient)
            return db_user_ingredient
        except Exception as e:
            self.db.rollback() # 오류 발생 시 모든 변경사항 롤백
            raise e
            
    def create_master_ingredient(self, ingredient_data: ingredient.MasterIngredientCreate) -> models.Ingredient:
        """
        '재료 사전'에 새로운 재료를 추가하는 관리자용 메서드.
        """
        existing_ingredient = self.db.query(models.Ingredient).filter(models.Ingredient.name == ingredient_data.name).first()
        if existing_ingredient:
            raise HTTPException(status_code=409, detail="이미 존재하는 재료입니다.")

        try:
            db_ingredient = models.Ingredient(
                name=ingredient_data.name,
                category=ingredient_data.category,
                storage_type=ingredient_data.storage_type
            )
            self.db.add(db_ingredient)
            self.db.commit()
            self.db.refresh(db_ingredient)
            return db_ingredient
        except Exception as e:
            self.db.rollback()
            raise e