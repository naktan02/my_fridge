from sqlalchemy.orm import Session
import models
import schemas

class DishTypeRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_all(self):
        return self.db.query(models.DishType).all()

    def create(self, dish_type_create: schemas.DishTypeCreate):
        db_dish_type = models.DishType(**dish_type_create.model_dump())
        self.db.add(db_dish_type)
        self.db.commit()
        self.db.refresh(db_dish_type)
        return db_dish_type

    def get_or_create_ingredient(self, name: str) -> models.Ingredient:
        """이름으로 재료를 찾고, 없으면 새로 생성합니다."""
        db_ingredient = self.db.query(models.Ingredient).filter(models.Ingredient.name == name).first()
        if not db_ingredient:
            db_ingredient = models.Ingredient(name=name)
            self.db.add(db_ingredient)
            self.db.commit()
            self.db.refresh(db_ingredient)
        return db_ingredient

    def add_user_ingredient(self, user_id: int, ingredient_create: schemas.UserIngredientCreate) -> models.UserIngredient:
        """사용자의 냉장고에 재료를 추가합니다."""
        # 1. 재료 마스터 테이블에서 재료 가져오기/생성하기
        db_ingredient = self.get_or_create_ingredient(name=ingredient_create.ingredient_name)

        # 2. 사용자 재료 테이블에 추가하기
        db_user_ingredient = models.UserIngredient(
            # user_id=user_id, # 나중에 실제 사용자 ID로 교체
            ingredient_id=db_ingredient.id,
            expiration_date=ingredient_create.expiration_date
        )
        self.db.add(db_user_ingredient)
        self.db.commit()
        self.db.refresh(db_user_ingredient)
        return db_user_ingredient