import sys
import os
import json
import csv
from abc import ABC, abstractmethod
from sqlalchemy.orm import Session
from database import SessionLocal
from models import Dish, Recipe, RecipeIngredient, Ingredient, UserIngredient # UserIngredient 추가

# --------------------------------------------------------------------------
# ⚙️ 설정 (Configuration)
# --------------------------------------------------------------------------
BASE_DATA_PATH = "/data" 
RECIPE_DIR_PATH = os.path.join(BASE_DATA_PATH, "레시피 모음")
DESCRIPTION_DIR_PATH = os.path.join(BASE_DATA_PATH, "요리 설명")
INGREDIENTS_FILE_PATH = os.path.join(BASE_DATA_PATH, "재료/ingredients.json")

# --------------------------------------------------------------------------
# 🏛️ 임포터 기본 설계 (Base Importer Design)
# --------------------------------------------------------------------------
class BaseImporter(ABC):
    def __init__(self):
        self.db: Session = SessionLocal()
        print(f"[{self.__class__.__name__}] 데이터베이스 연결을 시작합니다.")

    @abstractmethod
    def run(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        print(f"[{self.__class__.__name__}] 데이터베이스 연결을 닫습니다.")
        self.db.close()

# --------------------------------------------------------------------------
# 🗑️ 데이터 리셋터 (Data Resetter) - 신규 추가
# --------------------------------------------------------------------------
class DataResetter(BaseImporter):
    """
    모든 요리, 레시피, 재료 관련 데이터를 DB에서 삭제합니다. (User 정보는 유지)
    """
    def run(self):
        print("--- 모든 데이터 삭제를 시작합니다 ---")
        
        # 외래 키 제약조건 위반을 피하기 위해 의존성이 있는 테이블부터 삭제
        self.db.query(RecipeIngredient).delete(synchronize_session=False)
        print("  - RecipeIngredients 테이블 데이터 삭제 완료.")
        
        self.db.query(UserIngredient).delete(synchronize_session=False)
        print("  - UserIngredients 테이블 데이터 삭제 완료.")

        self.db.query(Recipe).delete(synchronize_session=False)
        print("  - Recipes 테이블 데이터 삭제 완료.")

        self.db.query(Dish).delete(synchronize_session=False)
        print("  - Dishes 테이블 데이터 삭제 완료.")
        
        self.db.query(Ingredient).delete(synchronize_session=False)
        print("  - Ingredients 테이블 데이터 삭제 완료.")

        self.db.commit()
        print("✅ 모든 데이터가 성공적으로 삭제되었습니다.")


# --------------------------------------------------------------------------
# 🍽️ 요리 임포터 (Dish Importer)
# --------------------------------------------------------------------------
class DishImporter(BaseImporter):
    """'요리 설명' JSON 파일을 읽어 Dish 테이블을 채우거나 설명을 업데이트합니다."""
    def run(self):
        descriptions = {}
        try:
            for filename in os.listdir(DESCRIPTION_DIR_PATH):
                if filename.endswith(".json"):
                    with open(os.path.join(DESCRIPTION_DIR_PATH, filename), "r", encoding="utf-8") as f:
                        descriptions.update(json.load(f))
        except FileNotFoundError:
            print(f"❌ '요리 설명' 폴더를 찾을 수 없습니다: {DESCRIPTION_DIR_PATH}")
            return
            
        print(f"--- 총 {len(descriptions)}개의 요리 설명을 기준으로 Dish 생성 또는 업데이트 시작 ---")
        new_count = 0
        update_count = 0
        for dish_name, description in descriptions.items():
            db_dish = self.db.query(Dish).filter(Dish.name == dish_name).first()

            if db_dish:
                if not db_dish.semantic_description and description:
                    print(f"  - '{dish_name}'의 비어있는 설명을 추가합니다.")
                    db_dish.semantic_description = description
                    update_count += 1
            else:
                self.db.add(Dish(name=dish_name, semantic_description=description))
                new_count += 1
        
        self.db.commit()
        print(f"✅ {new_count}개의 새로운 Dish를 추가하고, {update_count}개의 Dish 설명을 업데이트했습니다.")

# --------------------------------------------------------------------------
# 🌿 재료 임포터 (Ingredient Importer)
# --------------------------------------------------------------------------
class IngredientImporter(BaseImporter):
    """'재료/ingredients.json' 파일을 읽어 Ingredient 테이블을 채웁니다."""
    def run(self):
        try:
            with open(INGREDIENTS_FILE_PATH, "r", encoding="utf-8") as f:
                ingredients_data = json.load(f)
        except FileNotFoundError:
            print(f"❌ 파일을 찾을 수 없습니다: {INGREDIENTS_FILE_PATH}")
            return
        
        print(f"--- 총 {len(ingredients_data)}개의 마스터 재료 DB 저장 시작 ---")
        count = 0
        for ing_data in ingredients_data:
            if not self.db.query(Ingredient).filter(Ingredient.name == ing_data["name"]).first():
                new_ingredient = Ingredient(
                    name=ing_data["name"],
                    category=ing_data.get("category"),
                    storage_type=ing_data.get("storage_type")
                )
                self.db.add(new_ingredient)
                count += 1
        
        self.db.commit()
        print(f"✅ {count}개의 새로운 재료를 DB에 추가했습니다.")

# --------------------------------------------------------------------------
# 🍲 레시피 임포터 (Recipe Importer)
# --------------------------------------------------------------------------
class RecipeImporter(BaseImporter):
    """CSV 파일을 읽어 Recipe와 RecipeIngredient를 추가하고, 필요시 Dish도 생성합니다."""

    def _get_or_create_ingredient(self, name: str) -> Ingredient:
        ingredient = self.db.query(Ingredient).filter(Ingredient.name == name).first()
        if ingredient: return ingredient
        print(f"  ✨ 새로운 재료 '{name}'을(를) DB에 자동 추가합니다.")
        new_ingredient = Ingredient(name=name)
        self.db.add(new_ingredient)
        self.db.flush()
        return new_ingredient
        
    def _get_or_create_dish(self, name: str) -> Dish:
        dish = self.db.query(Dish).filter(Dish.name == name).first()
        if dish:
            return dish
        print(f"  ✨ Dish 테이블에 '{name}'이(가) 없어 새로 추가합니다. (설명은 나중에 채워주세요)")
        new_dish = Dish(name=name, semantic_description=None)
        self.db.add(new_dish)
        self.db.flush()
        return new_dish

    def run(self):
        print("\n--- 레시피 CSV 파일 처리 시작 ---")
        try:
            recipe_files = os.listdir(RECIPE_DIR_PATH)
        except FileNotFoundError:
            print(f"❌ '레시피 모음' 폴더를 찾을 수 없습니다: {RECIPE_DIR_PATH}")
            return

        for filename in recipe_files:
            if not filename.endswith(".csv"): continue
            
            print(f"\n--- '{filename}' 파일 처리 ---")
            with open(os.path.join(RECIPE_DIR_PATH, filename), "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        dish_category = row.get("category")
                        recipe_name = row.get("name")
                        
                        if not dish_category or not recipe_name:
                            print("  - ⚠️ 'category' 또는 'name' 열이 없어 건너뜁니다.")
                            continue
                        
                        db_dish = self._get_or_create_dish(dish_category)

                        recipe_data = json.loads(row["data"])
                        new_recipe = Recipe(
                            dish_id=db_dish.id,
                            name=recipe_name,
                            title=recipe_data.get("title", ""),
                            instructions=recipe_data.get("recipe", []),
                            youtube_url=recipe_data.get("url"),
                            thumbnail_url=recipe_data.get("image_url")
                        )
                        self.db.add(new_recipe)
                        self.db.flush()

                        for ing_data in recipe_data.get("ingredients", []):
                            ing_name = ing_data.get("name")
                            if not ing_name: continue
                            ingredient = self._get_or_create_ingredient(ing_name)
                            
                            self.db.add(RecipeIngredient(
                                recipe_id=new_recipe.id,
                                ingredient_id=ingredient.id,
                                quantity_display=ing_data.get("quantity")
                            ))
                        
                        self.db.commit()
                        print(f"  - '{db_dish.name}'에 '{recipe_name}' 레시피 추가 완료.")

                    except Exception as e:
                        print(f"  - ❌ 에러 발생: {e}")
                        self.db.rollback()
        
        print("\n🎉 모든 레시피 파일 처리가 완료되었습니다.")

# --------------------------------------------------------------------------
# 🚀 실행기 (Runner)
# --------------------------------------------------------------------------
def print_usage():
    print("\n사용법: docker-compose exec api uv run python import_data.py [command]")
    print("\nCommands:")
    print("  import_dishes      : '요리 설명' JSON 파일로 Dish 테이블을 채웁니다.")
    print("  import_ingredients : 마스터 재료 데이터를 DB에 저장합니다.")
    print("  import_recipes     : 레시피 CSV 파일로 Recipe 테이블을 채웁니다.")
    print("  import_all         : 요리, 재료, 레시피를 순서대로 모두 저장합니다.")
    print("  reset_data         : 요리/레시피/재료 관련 데이터를 모두 삭제합니다.")

def main():
    if len(sys.argv) < 2:
        print_usage()
        return

    command = sys.argv[1]

    if command == "reset_data":
        with DataResetter() as importer:
            importer.run()
    elif command == "import_dishes":
        with DishImporter() as importer:
            importer.run()
    elif command == "import_ingredients":
        with IngredientImporter() as importer:
            importer.run()
    elif command == "import_recipes":
        with RecipeImporter() as importer:
            importer.run()
    elif command == "import_all":
        print("--- (1/3) Dish 임포트 작업을 시작합니다 ---")
        with DishImporter() as importer:
            importer.run()
        print("\n--- (2/3) Ingredient 임포트 작업을 시작합니다 ---")
        with IngredientImporter() as importer:
            importer.run()
        print("\n--- (3/3) Recipe 임포트 작업을 시작합니다 ---")
        with RecipeImporter() as importer:
            importer.run()
    else:
        print(f"\n알 수 없는 명령어입니다: {command}")
        print_usage()

if __name__ == "__main__":
    main()