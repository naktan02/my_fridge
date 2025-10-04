from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
import asyncio
import models
from schemas.dish import Dish, DishCreate, Recipe, RecipeCreate, SearchRequest, GroupedSearchResponse
from repositories.dishes import DishRepository
from database import get_db
from auth.dependencies import get_current_user, is_admin
import json
# 검색 관련
from search_client import get_es_client, DISHES_INDEX_NAME
from repositories.search import SearchRepository
from elasticsearch import AsyncElasticsearch

router = APIRouter(tags=["Dishes"])

def get_repo(db: Session = Depends(get_db)) -> DishRepository:
    return DishRepository(db=db)

def get_search_repo(es: AsyncElasticsearch = Depends(get_es_client)) -> SearchRepository:
    return SearchRepository(es_client=es)



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
@router.post("/search/grouped", response_model=GroupedSearchResponse, tags=["Dishes"])
async def search_grouped_dishes(
    search_request: SearchRequest,
    search_repo: SearchRepository = Depends(get_search_repo),
    # 이 API는 이제 로그인이 필수입니다.
    current_user: models.User = Depends(get_current_user)
):
    """
    **통합 검색 API (로그인 필수)**
    - Request Body로 받은 `ingredients` 목록을 사용하여 요리를 검색합니다.
    """
    # Body에 재료가 없으면(필수 필드이므로 그럴 일은 없지만) 빈 결과를 반환
    if not search_request.ingredients:
        return {"total": 0, "results": []}

    # 앱이 보내준 재료 목록을 사용하여 Elasticsearch 검색 수행
    res = await search_repo.search_grouped_dishes(
        query=search_request.q,
        user_ingredients=search_request.ingredients,
        size=search_request.size,
        topk_per_dish=search_request.topk,
        ing_mode=search_request.ing_mode,
        ing_ratio=search_request.ing_ratio
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
