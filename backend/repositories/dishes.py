# /backend/repositories/dishes.py

from sqlalchemy.orm import Session, joinedload
import models
from schemas.dish import DishCreate, RecipeCreate
# ✅ FastAPI의 HTTPException을 import합니다.
from fastapi import HTTPException

class DishRepository:
    def __init__(self, db: Session):
        self.db = db

    def _get_or_create_ingredient(self, name: str) -> models.Ingredient:
        """재료가 없으면 새로 생성하여 반환합니다."""
        ingredient = self.db.query(models.Ingredient).filter(models.Ingredient.name == name).first()
        if not ingredient:
            ingredient = models.Ingredient(name=name)
            self.db.add(ingredient)
            self.db.flush() # commit 없이 id를 가져오기 위해 flush
        return ingredient

    def create_dish_with_recipes(self, dish_create: DishCreate) -> models.Dish:
        """Dish와 그에 속한 Recipe, RecipeIngredient를 트랜잭션으로 한 번에 생성합니다."""
        
        # ✅ --- 코드 추가 시작 ---
        # 요리를 생성하기 전, 같은 이름의 요리가 이미 존재하는지 확인합니다.
        existing_dish = self.db.query(models.Dish).filter(models.Dish.name == dish_create.name).first()
        if existing_dish:
            # 존재한다면, 500 에러 대신 "이미 존재하는 요리"라는 명확한 에러를 발생시킵니다.
            raise HTTPException(status_code=409, detail="이미 존재하는 요리입니다.")
        # ✅ --- 코드 추가 끝 ---

        try:
            # 1. Dish 모델 생성
            db_dish = models.Dish(
                name=dish_create.name,
                description=dish_create.description,
                cuisine_type=dish_create.cuisine_type,
                tags=dish_create.tags
            )
            self.db.add(db_dish)
            self.db.flush() # dish의 id를 먼저 확보

            # 2. Recipe 정보 처리
            for recipe_data in dish_create.recipes:
                db_recipe = models.Recipe(
                    dish_id=db_dish.id,
                    **recipe_data.model_dump(exclude={'ingredients'})
                )
                self.db.add(db_recipe)
                self.db.flush() # recipe의 id 확보

                # 3. RecipeIngredient 정보 처리
                for ing_info in recipe_data.ingredients:
                    db_ingredient = self._get_or_create_ingredient(ing_info.name)
                    db_recipe_ingredient = models.RecipeIngredient(
                        recipe_id=db_recipe.id,
                        ingredient_id=db_ingredient.id,
                        quantity_display=ing_info.quantity_display
                    )
                    self.db.add(db_recipe_ingredient)
            
            self.db.commit()
            self.db.refresh(db_dish)
            return db_dish

        except Exception as e:
            self.db.rollback()
            raise e

    def get_all_dishes(self) -> list[models.Dish]:
        """모든 Dish 정보를 레시피, 재료 정보와 함께 가져옵니다."""
        return self.db.query(models.Dish).options(
            joinedload(models.Dish.recipes)
            .joinedload(models.Recipe.ingredients)
            .joinedload(models.RecipeIngredient.ingredient)
        ).all()
        
    def add_recipe_to_dish(self, dish_id: int, recipe_data: RecipeCreate) -> models.Recipe:
        """기존 Dish에 새로운 Recipe를 추가합니다."""
        db_dish = self.db.query(models.Dish).filter(models.Dish.id == dish_id).first()
        if not db_dish:
            raise HTTPException(status_code=404, detail="요리를 찾을 수 없습니다.")
        
        try:
            # Recipe 모델 생성
            db_recipe = models.Recipe(
                dish_id=dish_id,
                **recipe_data.model_dump(exclude={'ingredients'})
            )
            self.db.add(db_recipe)
            self.db.flush()

            # RecipeIngredient 정보 처리
            for ing_info in recipe_data.ingredients:
                db_ingredient = self._get_or_create_ingredient(ing_info.name)
                db_recipe_ingredient = models.RecipeIngredient(
                    recipe_id=db_recipe.id,
                    ingredient_id=db_ingredient.id,
                    quantity_display=ing_info.quantity_display
                )
                self.db.add(db_recipe_ingredient)
            
            self.db.commit()
            self.db.refresh(db_recipe)
            return db_recipe

        except Exception as e:
            self.db.rollback()
            raise e