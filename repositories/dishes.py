from sqlalchemy.orm import Session
import models
from schemas import dish

class DishTypeRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_all(self):
        return self.db.query(models.DishType).all()

    def create(self, dish_type_create: dish.DishTypeCreate):
        db_dish_type = models.DishType(**dish_type_create.model_dump())
        self.db.add(db_dish_type)
        self.db.commit()
        self.db.refresh(db_dish_type)
        return db_dish_type