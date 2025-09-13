from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
import asyncio
import models
from schemas.dish import Dish, DishCreate, Recipe, RecipeCreate
from repositories.dishes import DishRepository
from database import get_db
from auth.dependencies import get_current_user, is_admin

# 검색 관련
from search_client import get_es_client, DISHES_INDEX_NAME
from repositories.search import SearchRepository
from elasticsearch import AsyncElasticsearch

router = APIRouter(tags=["Dishes"])

def get_repo(db: Session = Depends(get_db)) -> DishRepository:
    return DishRepository(db=db)

def get_search_repo(es: AsyncElasticsearch = Depends(get_es_client)) -> SearchRepository:
    return SearchRepository(es_client=es)

# === 관리자용: 전체 재색인 ===
@router.post("/admin/search/reindex", status_code=202)
async def reindex_dishes_for_search(
    background_tasks: BackgroundTasks,
    dish_repo: DishRepository = Depends(get_repo),
    search_repo: SearchRepository = Depends(get_search_repo),
    admin_user: models.User = Depends(is_admin)
):
    """
    PostgreSQL의 모든 dish/recipe를 ES에 '텍스트 전용' 문서로 재색인.
    - 임베딩/썸네일 제거
    - description 포함
    - 문서 1개 = (dish_id, recipe_id) 조합
    """
    async def background_reindexing():
        print("Starting background reindexing...")
        BATCH_SIZE = 200
        offset = 0
        total = 0
        # 최초 1회 전체 삭제(운영 전환 시엔 버전 인덱스+별칭 스왑 권장)
        await search_repo.reset_index()

        while True:
            dishes_batch = dish_repo.get_all_dishes(skip=offset, limit=BATCH_SIZE)
            if not dishes_batch:
                break

            actions = []
            for dish in dishes_batch:
                for recipe in dish.recipes:
                    ingredient_names = [item.ingredient.name for item in recipe.ingredients]
                    description = (
                        getattr(recipe, "description", None)
                        or getattr(dish, "semantic_description", None)
                        or ""
                    )
                    actions.append({
                        "_index": DISHES_INDEX_NAME,
                        "_id": f"{dish.id}_{recipe.id}",
                        "_source": {
                            "dish_id": dish.id,
                            "recipe_id": recipe.id,
                            "dish_name": dish.name,
                            "recipe_title": getattr(recipe, "title", "") or "",
                            "ingredients": ingredient_names,
                            "description": description
                        }
                    })

            if actions:
                await search_repo.bulk_index_dishes(actions, refresh=False)
                total += len(actions)
                print(f"Indexed batch: {len(actions)} (total {total})")

            offset += BATCH_SIZE
            await asyncio.sleep(0.2)

        # 마지막에 수동 refresh
        es = get_es_client()
        await es.indices.refresh(index=DISHES_INDEX_NAME)
        print(f"Background reindexing finished. Total {total} documents.")

    background_tasks.add_task(background_reindexing)
    return {"message": "재색인 작업이 백그라운드에서 시작되었습니다."}

# === CRUD 예시들 (필요 시 유지) ===
@router.post("", response_model=Dish, status_code=201)
def create_dish(
    dish_create: DishCreate,
    repo: DishRepository = Depends(get_repo),
    admin_user: models.User = Depends(is_admin)
):
    return repo.create_dish_with_recipes(dish_create=dish_create)

@router.get("", response_model=List[Dish])
def get_all_dishes(repo: DishRepository = Depends(get_repo)):
    return repo.get_all_dishes()

@router.post("/{dish_id}/recipes", response_model=Recipe, status_code=201)
def add_recipe_to_dish(
    dish_id: int,
    recipe_create: RecipeCreate,
    repo: DishRepository = Depends(get_repo),
    admin_user: models.User = Depends(is_admin)
):
    return repo.add_recipe_to_dish(dish_id=dish_id, recipe_data=recipe_create)

# === 사용자용: dish 카드 목록(그룹화 + 각 dish의 상위 K 레시피 id) ===
@router.get("/search/grouped")
async def search_grouped_dishes(
    q: Optional[str] = None,
    ingredients: Optional[str] = None,   # "김치,돼지고기,두부"
    size: int = 20,                       # dish 카드 개수
    topk: int = 3,                        # 그룹당 recipe 상위 K
    ing_mode: str = "RATIO",              # "ALL"|"ANY"|"RATIO"
    ing_ratio: float = 0.6,
    search_repo: SearchRepository = Depends(get_search_repo),
):
    user_ingredients_list = None
    if ingredients:
        user_ingredients_list = [s.strip() for s in ingredients.split(",") if s.strip()]

    res = await search_repo.search_grouped_dishes(
        query=q,
        user_ingredients=user_ingredients_list,
        size=size,
        topk_per_dish=topk,
        ing_mode=ing_mode,
        ing_ratio=ing_ratio
    )
    return res

# (참고) 프런트가 dish 카드를 클릭했을 때, res.results[*].recipe_ids[] 를
# 그대로 다른 API(예: POST /api/v1/recipes/by-ids)에 넘기고,
# 서버는 UNNEST WITH ORDINALITY로 순서 보존 SELECT 하여 상세를 응답하면 된다.

@router.post("/recipes/by-ids", response_model=List[Recipe])
def get_recipes_by_ids(
    recipe_ids: List[int],
    repo: DishRepository = Depends(get_repo),
    current_user: models.User = Depends(get_current_user)
):
    """
    검색 결과에서 선택된 dish의 recipe_ids를 받아 상세 정보 반환
    - 순서 보존을 위해 UNNEST WITH ORDINALITY 사용
    """
    if not recipe_ids:
        return []
    
    return repo.get_recipes_by_ids_ordered(recipe_ids)
