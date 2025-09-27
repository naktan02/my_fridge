# manage.py (최종 수정본)
import sys
import os
import json
import csv
import asyncio
from abc import ABC, abstractmethod
from sqlalchemy.orm import Session
from elasticsearch import AsyncElasticsearch 

# --- 프로젝트 모듈 임포트 ---
# 이 스크립트가 프로젝트 루트에 있으므로, 바로 임포트 가능합니다.
from database import SessionLocal
import models
from repositories.dishes import DishRepository
from repositories.search import SearchRepository
from search_client import create_dishes_index, DISHES_INDEX_NAME, get_es_client, lifespan as es_lifespan

# --------------------------------------------------------------------------
# ⚙️ 설정 (Configuration)
# --------------------------------------------------------------------------
BASE_DATA_PATH = "/data" 
RECIPE_DIR_PATH = os.path.join(BASE_DATA_PATH, "레시피 모음")
DESCRIPTION_DIR_PATH = os.path.join(BASE_DATA_PATH, "요리 설명")
INGREDIENTS_FILE_PATH = os.path.join(BASE_DATA_PATH, "재료/ingredients.json")

# --------------------------------------------------------------------------
# 🏛️ 베이스 관리자 클래스
# --------------------------------------------------------------------------
class BaseManager(ABC):
    """DB 연결 등 공통 로직을 처리하는 기본 클래스"""
    def __init__(self):
        self.db: Session = SessionLocal()
        print(f"[{self.__class__.__name__}] 데이터베이스 연결을 시작합니다.")

    @abstractmethod
    async def run(self, command: str):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        print(f"[{self.__class__.__name__}] 데이터베이스 연결을 닫습니다.")
        self.db.close()

# --------------------------------------------------------------------------
# 🗃️ 데이터베이스 관리자 (Database Manager)
# --------------------------------------------------------------------------
class DBManager(BaseManager):
    """데이터베이스 데이터 리셋 및 임포트를 담당합니다."""

    async def _reset_data(self):
        print("--- 모든 데이터 삭제를 시작합니다 (User 정보는 유지) ---")
        self.db.query(models.RecipeIngredient).delete(synchronize_session=False)
        self.db.query(models.UserIngredient).delete(synchronize_session=False)
        self.db.query(models.Recipe).delete(synchronize_session=False)
        self.db.query(models.Dish).delete(synchronize_session=False)
        self.db.query(models.Ingredient).delete(synchronize_session=False)
        self.db.commit()
        print("✅ 모든 데이터가 성공적으로 삭제되었습니다.")

    async def _import_dishes(self):
        print("--- '요리 설명' 데이터 임포트를 시작합니다 ---")
        descriptions = {}
        try:
            for filename in os.listdir(DESCRIPTION_DIR_PATH):
                if filename.endswith(".json"):
                    with open(os.path.join(DESCRIPTION_DIR_PATH, filename), "r", encoding="utf-8") as f:
                        descriptions.update(json.load(f))
        except FileNotFoundError:
            print(f"❌ '요리 설명' 폴더를 찾을 수 없습니다: {DESCRIPTION_DIR_PATH}")
            return
            
        new_count, update_count = 0, 0
        for dish_name, description in descriptions.items():
            db_dish = self.db.query(models.Dish).filter(models.Dish.name == dish_name).first()
            if db_dish:
                if not db_dish.semantic_description and description:
                    db_dish.semantic_description = description
                    update_count += 1
            else:
                self.db.add(models.Dish(name=dish_name, semantic_description=description))
                new_count += 1
        self.db.commit()
        print(f"✅ {new_count}개의 새로운 Dish를 추가하고, {update_count}개의 Dish 설명을 업데이트했습니다.")

    async def _import_ingredients(self):
        print("--- '마스터 재료' 데이터 임포트를 시작합니다 ---")
        try:
            with open(INGREDIENTS_FILE_PATH, "r", encoding="utf-8") as f:
                ingredients_data = json.load(f)
        except FileNotFoundError:
            print(f"❌ 파일을 찾을 수 없습니다: {INGREDIENTS_FILE_PATH}")
            return
        
        count = 0
        for ing_data in ingredients_data:
            if not self.db.query(models.Ingredient).filter(models.Ingredient.name == ing_data["name"]).first():
                self.db.add(models.Ingredient(
                    name=ing_data["name"],
                    category=ing_data.get("category"),
                    storage_type=ing_data.get("storage_type")
                ))
                count += 1
        self.db.commit()
        print(f"✅ {count}개의 새로운 재료를 DB에 추가했습니다.")

    async def _import_recipes(self):
        print("--- '레시피' 데이터 임포트를 시작합니다 ---")
        
        def _get_or_create_ingredient(name: str) -> models.Ingredient:
            # ... (기존 로직과 동일)
            ingredient = self.db.query(models.Ingredient).filter(models.Ingredient.name == name).first()
            if ingredient: return ingredient
            new_ingredient = models.Ingredient(name=name)
            self.db.add(new_ingredient)
            self.db.flush(); return new_ingredient
            
        def _get_or_create_dish(name: str) -> models.Dish:
            # ... (기존 로직과 동일)
            dish = self.db.query(models.Dish).filter(models.Dish.name == name).first()
            if dish: return dish
            new_dish = models.Dish(name=name, semantic_description=None)
            self.db.add(new_dish)
            self.db.flush(); return new_dish

        try:
            recipe_files = os.listdir(RECIPE_DIR_PATH)
        except FileNotFoundError:
            print(f"❌ '레시피 모음' 폴더를 찾을 수 없습니다: {RECIPE_DIR_PATH}"); return

        for filename in recipe_files:
            if not filename.endswith(".csv"): continue
            print(f"\n--- '{filename}' 파일 처리 중 ---")
            with open(os.path.join(RECIPE_DIR_PATH, filename), "r", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    try:
                        dish_category, recipe_name = row.get("category"), row.get("name")
                        if not dish_category or not recipe_name: continue
                        
                        db_dish = _get_or_create_dish(dish_category)
                        recipe_data = json.loads(row["data"])
                        
                        new_recipe = models.Recipe(
                            dish_id=db_dish.id, name=recipe_name,
                            title=recipe_data.get("title", ""),
                            instructions=recipe_data.get("recipe", []),
                            youtube_url=recipe_data.get("url"),
                            thumbnail_url=recipe_data.get("image_url")
                        )
                        self.db.add(new_recipe); self.db.flush()

                        for ing_data in recipe_data.get("ingredients", []):
                            ing_name = ing_data.get("name")
                            if not ing_name: continue
                            ingredient = _get_or_create_ingredient(ing_name)
                            self.db.add(models.RecipeIngredient(
                                recipe_id=new_recipe.id,
                                ingredient_id=ingredient.id,
                                quantity_display=ing_data.get("quantity")
                            ))
                        self.db.commit()
                    except Exception as e:
                        print(f"  - ❌ 에러 발생: {e}"); self.db.rollback()
        print("\n🎉 모든 레시피 파일 처리가 완료되었습니다.")


    async def run(self, command: str):
        if command == "reset":
            await self._reset_data()
        elif command == "import_all":
            await self._import_dishes()
            await self._import_ingredients()
            await self._import_recipes()
        else:
            print(f"알 수 없는 DB 관련 명령어입니다: {command}")

# --------------------------------------------------------------------------
# 🔍 엘라스틱서치 관리자 (Elasticsearch Manager)
# --------------------------------------------------------------------------
class ESManager(BaseManager):
    """Elasticsearch 인덱스 생성 및 재색인을 담당합니다."""
    def __init__(self):
        super().__init__()
        self.es_client: AsyncElasticsearch = None

    async def __aenter__(self):
        self.es_lifespan_context = es_lifespan(app=None)
        await self.es_lifespan_context.__aenter__()
        self.es_client = get_es_client()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.es_lifespan_context.__aexit__(exc_type, exc_val, exc_tb)
        await super().__aexit__(exc_type, exc_val, exc_tb)

    async def _create_index(self):
        print("--- Elasticsearch 인덱스 생성을 시작합니다 ---")
        await create_dishes_index(self.es_client)
        print("✅ 인덱스 생성 완료.")

    async def _reindex_data(self):
        print("--- Elasticsearch 데이터 재색인을 시작합니다 ---")
        dish_repo = DishRepository(self.db)
        search_repo = SearchRepository(self.es_client)
        
        await search_repo.reset_index()

        offset, total = 0, 0
        BATCH_SIZE = 200
        while True:
            dishes_batch = dish_repo.get_all_dishes(skip=offset, limit=BATCH_SIZE)
            if not dishes_batch: break

            actions = []
            for dish in dishes_batch:
                for recipe in dish.recipes:
                    ingredient_names = [item.ingredient.name for item in recipe.ingredients]
                    instructions_text = ' '.join(recipe.instructions) if isinstance(recipe.instructions, list) else str(recipe.instructions)
                    description = instructions_text or getattr(dish, "semantic_description", "")
                    
                    actions.append({
                        "_index": DISHES_INDEX_NAME,
                        "_id": f"{dish.id}_{recipe.id}",
                        "_source": {
                            "dish_id": dish.id, "recipe_id": recipe.id,
                            "dish_name": dish.name,
                            "recipe_title": getattr(recipe, "title", "") or "",
                            "recipe_name": getattr(recipe, "name", "") or "",
                            "ingredients": ingredient_names,
                            "description": description
                        }
                    })
            
            if actions:
                await search_repo.bulk_index_dishes(actions, refresh=False)
                total += len(actions)
                print(f"  - 색인된 문서: {len(actions)} (총 {total}개)")

            offset += BATCH_SIZE
            await asyncio.sleep(0.1)

        await self.es_client.indices.refresh(index=DISHES_INDEX_NAME)
        print(f"✅ 재색인 완료. 총 {total}개의 문서가 처리되었습니다.")

    async def run(self, command: str):
        if command == "create_index":
            await self._create_index()
        elif command == "reindex":
            await self._reindex_data()
        else:
            print(f"알 수 없는 ES 관련 명령어입니다: {command}")

# --------------------------------------------------------------------------
# 🚀 실행기 (Runner)
# --------------------------------------------------------------------------
def print_usage():
    print("\n사용법: docker-compose exec api uv run python manage.py [group] [command]")
    print("\nGroups & Commands:")
    print("  db reset         : 요리/레시피/재료 관련 DB 데이터를 모두 삭제합니다.")
    print("  db import_all    : 모든 데이터를 DB로 가져옵니다.")
    print("  es create_index  : Elasticsearch에 'dishes' 인덱스를 생성합니다.")
    print("  es reindex       : DB의 모든 요리/레시피 데이터를 Elasticsearch에 재색인합니다.")

async def main():
    if len(sys.argv) < 3:
        print_usage()
        return

    group, command = sys.argv[1], sys.argv[2]

    if group == "db":
        async with DBManager() as manager:
            await manager.run(command)
    elif group == "es":
        async with ESManager() as manager:
            await manager.run(command)
    else:
        print(f"알 수 없는 명령어 그룹입니다: {group}")
        print_usage()

if __name__ == "__main__":
    asyncio.run(main())