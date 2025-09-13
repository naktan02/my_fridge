# /backend/repositories/dishes.py

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select, distinct
import models
from schemas.dish import DishCreate, RecipeCreate
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
            self.db.flush()
        return ingredient

    def create_dish_with_recipes(self, dish_create: DishCreate) -> models.Dish:
        """Dish와 그에 속한 Recipe, RecipeIngredient를 트랜잭션으로 한 번에 생성합니다."""
        
        existing_dish = self.db.query(models.Dish).filter(models.Dish.name == dish_create.name).first()
        if existing_dish:
            raise HTTPException(status_code=409, detail="이미 존재하는 요리입니다.")

        try:
            # 1. Dish 모델 생성
            db_dish = models.Dish(
                name=dish_create.name,
                description=dish_create.description,
                cuisine_type=dish_create.cuisine_type,
                tags=dish_create.tags
            )
            self.db.add(db_dish)
            self.db.flush()

            # 2. Recipe 정보 처리
            for recipe_data in dish_create.recipes:
                db_recipe = models.Recipe(
                    dish_id=db_dish.id,
                    **recipe_data.model_dump(exclude={'ingredients'})
                )
                self.db.add(db_recipe)
                self.db.flush()

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

            # commit 후 id가 부여된 db_dish 객체를 이용해 관계가 모두 포함된 객체를 다시 조회합니다.
            created_dish = self.db.query(models.Dish).options(
                joinedload(models.Dish.recipes)
                .joinedload(models.Recipe.ingredients)
                .joinedload(models.RecipeIngredient.ingredient)
            ).filter(models.Dish.id == db_dish.id).one()
            
            return created_dish

        except Exception as e:
            self.db.rollback()
            raise e

    def get_all_dishes(self, skip: int = 0, limit: int = 100) -> list[models.Dish]:
        """
        ✅ 수정: Eager Loading과 Pagination을 적용하여 모든 Dish 정보를 가져옵니다.
        """
        return self.db.query(models.Dish).options(
            # ✅ 개선: N+1 문제를 해결하기 위해 연관된 모든 데이터를 한 번의 쿼리로 가져옵니다.
            joinedload(models.Dish.recipes)
            .joinedload(models.Recipe.ingredients)
            .joinedload(models.RecipeIngredient.ingredient)
        ).offset(skip).limit(limit).all()
        
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

            # commit 후 id가 부여된 db_recipe 객체를 이용해 관계가 모두 포함된 객체를 다시 조회합니다.
            created_recipe = self.db.query(models.Recipe).options(
                joinedload(models.Recipe.ingredients)
                .joinedload(models.RecipeIngredient.ingredient)
            ).filter(models.Recipe.id == db_recipe.id).one()

            return created_recipe

        except Exception as e:
            self.db.rollback()
            raise e
        
    def get_dishes_by_user_ingredients(self, user_id: int) -> list[models.Dish]:
        """
        특정 사용자가 보유한 재료를 하나 이상 포함하는 모든 요리 목록을 반환합니다.
        """
        # 1. 사용자가 보유한 모든 재료의 ID를 가져옵니다.
        user_ingredient_ids_query = select(models.UserIngredient.ingredient_id).where(
            models.UserIngredient.user_id == user_id
        )
        user_ingredient_ids = self.db.execute(user_ingredient_ids_query).scalars().all()

        if not user_ingredient_ids:
            return [] # 보유 재료가 없으면 빈 리스트 반환

        # 2. 해당 재료 ID를 포함하는 레시피가 있는 모든 Dish의 ID를 중복 없이 찾습니다.
        dish_ids_query = (
            select(distinct(models.Dish.id))
            .join(models.Dish.recipes)
            .join(models.Recipe.ingredients)
            .where(models.RecipeIngredient.ingredient_id.in_(user_ingredient_ids))
        )
        dish_ids = self.db.execute(dish_ids_query).scalars().all()
        
        if not dish_ids:
            return []

        # 3. 찾은 Dish ID에 해당하는 Dish 객체들을 모든 관계와 함께 조회하여 반환합니다.
        return self.db.query(models.Dish).options(
            joinedload(models.Dish.recipes)
            .joinedload(models.Recipe.ingredients)
            .joinedload(models.RecipeIngredient.ingredient)
        ).filter(models.Dish.id.in_(dish_ids)).all()