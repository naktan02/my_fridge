import sys
import os
import json
import csv
from abc import ABC, abstractmethod
from sqlalchemy.orm import Session
from database import SessionLocal
from models import Dish, Recipe, RecipeIngredient, Ingredient

# --------------------------------------------------------------------------
# ⚙️ 설정 (Configuration)
# --------------------------------------------------------------------------
# ❗ 중요: 이 부분에 실제 Windows 사용자 이름을 정확하게 입력해주세요.
WINDOWS_USER_NAME = "PC"  # <--- 여기를 수정하세요!
BASE_DATA_PATH = f"/mnt/c/Users/{WINDOWS_USER_NAME}/Desktop/my_fridge_data"
RECIPE_DIR_PATH = os.path.join(BASE_DATA_PATH, "레시피모음")
DESCRIPTION_DIR_PATH = os.path.join(BASE_DATA_PATH, "요리설명")
INGREDIENTS_FILE_PATH = os.path.join(BASE_DATA_PATH, "재료/ingredients.json")

# --------------------------------------------------------------------------
# 🏛️ 임포터 기본 설계 (Base Importer Design)
# --------------------------------------------------------------------------
class BaseImporter(ABC):
    """
    모든 임포터가 상속받는 기본 클래스입니다.
    DB 세션 관리를 공통으로 처리합니다.
    """
    def __init__(self):
        self.db: Session = SessionLocal()
        print(f"[{self.__class__.__name__}] 데이터베이스 연결을 시작합니다.")

    @abstractmethod
    def run(self):
        """데이터를 임포트하는 메인 로직을 구현해야 합니다."""
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        print(f"[{self.__class__.__name__}] 데이터베이스 연결을 닫습니다.")
        self.db.close()

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
            exists = self.db.query(Ingredient).filter(Ingredient.name == ing_data["name"]).first()
            if not exists:
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
    """CSV와 JSON 파일을 읽어 Dish, Recipe, RecipeIngredient 테이블을 채웁니다."""

    def _get_or_create_ingredient(self, name: str) -> Ingredient:
        """재료가 없으면 새로 생성하고, 있으면 가져옵니다."""
        ingredient = self.db.query(Ingredient).filter(Ingredient.name == name).first()
        if ingredient:
            return ingredient
        
        print(f"  ✨ 새로운 재료 '{name}'을(를) DB에 자동 추가합니다. (category 정보는 마스터 재료 파일에 추가해주세요)")
        new_ingredient = Ingredient(name=name)
        self.db.add(new_ingredient)
        self.db.flush()
        return new_ingredient

    def run(self):
        # 1. 요리 설명 데이터 로드
        descriptions = {}
        for filename in os.listdir(DESCRIPTION_DIR_PATH):
            if filename.endswith(".json"):
                with open(os.path.join(DESCRIPTION_DIR_PATH, filename), "r", encoding="utf-8") as f:
                    descriptions.update(json.load(f))
        print(f"✅ {len(descriptions)}개의 요리 설명 로드 완료.")

        # 2. 레시피 CSV 파일 처리
        for filename in os.listdir(RECIPE_DIR_PATH):
            if not filename.endswith(".csv"):
                continue
            
            print(f"\n--- '{filename}' 파일 처리 시작 ---")
            with open(os.path.join(RECIPE_DIR_PATH, filename), "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        dish_name = row["dish_name"]
                        if not dish_name: continue

                        if self.db.query(Dish).filter(Dish.name == dish_name).first():
                            print(f"이미 등록된 요리: '{dish_name}' (SKIP)")
                            continue

                        recipe_data = json.loads(row["data"])

                        new_dish = Dish(name=dish_name, semantic_description=descriptions.get(dish_name))
                        self.db.add(new_dish)
                        self.db.flush()

                        new_recipe = Recipe(
                            dish_id=new_dish.id,
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
                            
                            recipe_ingredient = RecipeIngredient(
                                recipe_id=new_recipe.id,
                                ingredient_id=ingredient.id,
                                quantity_display=ing_data.get("quantity")
                            )
                            self.db.add(recipe_ingredient)
                        
                        self.db.commit()
                        print(f"'{dish_name}' 추가 완료.")

                    except Exception as e:
                        print(f"  - ❌ 에러 발생: {e}")
                        self.db.rollback()
        
        print("\n🎉 모든 레시피 파일 처리가 완료되었습니다.")

# --------------------------------------------------------------------------
# 🚀 실행기 (Runner)
# --------------------------------------------------------------------------
def print_usage():
    print("\n사용법: python manage.py [command]")
    print("\nCommands:")
    print("  import_ingredients : 마스터 재료 데이터를 DB에 저장합니다.")
    print("  import_recipes     : 레시피와 요리 데이터를 DB에 저장합니다.")
    print("  import_all         : 재료와 레시피를 순서대로 모두 저장합니다.")

def main():
    if len(sys.argv) < 2:
        print_usage()
        return

    command = sys.argv[1]

    if command == "import_ingredients":
        with IngredientImporter() as importer:
            importer.run()

    elif command == "import_recipes":
        with RecipeImporter() as importer:
            importer.run()
            
    elif command == "import_all":
        print("--- 재료 임포트 작업을 시작합니다 ---")
        with IngredientImporter() as importer:
            importer.run()
        print("\n--- 레시피 임포트 작업을 시작합니다 ---")
        with RecipeImporter() as importer:
            importer.run()
        
    else:
        print(f"\n알 수 없는 명령어입니다: {command}")
        print_usage()

if __name__ == "__main__":
    main()