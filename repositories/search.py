# /backend/repositories/search.py
import logging
from typing import List, Dict, Any, Optional
from elasticsearch import AsyncElasticsearch
from elasticsearch.helpers import async_bulk

from search_client import DISHES_INDEX_NAME

logger = logging.getLogger(__name__)

class SearchRepository:
    def __init__(self, es_client: AsyncElasticsearch):
        self.es_client = es_client

    # === 내부 헬퍼: 재료 필터 (ALL / ANY / RATIO 지원) ===
    def _ingredient_filter(
        self,
        user_ingredients: Optional[List[str]],
        mode: str = "RATIO",
        ratio: float = 0.6
    ) -> Optional[Dict[str, Any]]:
        if not user_ingredients:
            return None
        terms = [ing.strip() for ing in user_ingredients if ing and ing.strip()]
        if not terms:
            return None

        if mode == "ALL":
            return {"bool": {"filter": [{"term": {"ingredients": ing}} for ing in terms]}}

        if mode == "ANY":
            return {"bool": {"should": [{"term": {"ingredients": ing}} for ing in terms],
                             "minimum_should_match": 1}}

        if mode == "RATIO":
            return {
                "terms_set": {
                    "ingredients": {
                        "terms": terms,
                        "minimum_should_match_script": {
                            "source": "Math.ceil(params.num_terms * params.ratio)",
                            "params": {"ratio": ratio}
                        }
                    }
                }
            }
        return None

    # === dish_id로 그룹화하여 그룹당 상위 K개의 recipe_id를 가져오는 검색 ===
    async def search_grouped_dishes(
        self,
        query: Optional[str],
        user_ingredients: Optional[List[str]],
        *,
        size: int = 20,      # dish 카드 개수
        topk_per_dish: int = 3,
        ing_mode: str = "RATIO",
        ing_ratio: float = 0.6
    ) -> Dict[str, Any]:
        """
        - ES에서 dish_id 기준 collapse + inner_hits 로 그룹 단위 상위 K 레시피를 함께 반환.
        - 텍스트 검색: dish_name/recipe_title/ingredients.tok/description (nori)
        - 재료 필터: ingredients(keyword) terms_set 등
        """
        if not query and not user_ingredients:
            return {"total": 0, "results": []}

        body: Dict[str, Any] = {
            "size": size,
            "_source": ["dish_id", "dish_name"],
            "track_total_hits": True
        }

        bool_q: Dict[str, Any] = {"filter": []}

        # 1) 재료 필터
        ing_filter = self._ingredient_filter(user_ingredients, mode=ing_mode, ratio=ing_ratio)
        if ing_filter:
            bool_q["filter"].append(ing_filter)

        # 2) 텍스트 검색(있을 때만)
        if query:
            text_q = {
                "dis_max": {
                    "queries": [{
                        "multi_match": {
                            "query": query,
                            "fields": [
                                "dish_name^4",
                                "recipe_title^2.5",
                                "recipe_name^2.5",
                                "ingredients.tok^2",
                                "description^1.6"
                            ],
                            "type": "best_fields",
                            "tie_breaker": 0.2
                        }
                    }],
                    "tie_breaker": 0.3
                }
            }
            bool_q["must"] = [text_q]

        if bool_q.get("filter") or bool_q.get("must"):
            body["query"] = {"bool": bool_q}

        # 3) 그룹화: dish_id collapse + inner_hits(top-K recipe_id)
        body["collapse"] = {
            "field": "dish_id",
            "inner_hits": {
                "name": "top_recipes",
                "size": topk_per_dish,
                "sort": [{"_score": "desc"}],
                "_source": ["recipe_id"]
            }
        }

        # 4) 실행 & 파싱
        resp = await self.es_client.search(index=DISHES_INDEX_NAME, body=body)
        hits = resp.get("hits", {}).get("hits", [])
        total = resp.get("hits", {}).get("total", {}).get("value", 0)

        results = []
        for h in hits:
            src = h.get("_source") or {}
            inner = h.get("inner_hits", {}).get("top_recipes", {}).get("hits", {}).get("hits", [])
            recipe_ids = [r.get("_source", {}).get("recipe_id") for r in inner if r.get("_source")]
            results.append({
                "dish_id": src.get("dish_id"),
                "dish_name": src.get("dish_name"),
                "recipe_ids": recipe_ids
            })

        return {"total": total, "results": results}

    # === 대량 색인 ===
    async def reset_index(self):
        if await self.es_client.indices.exists(index=DISHES_INDEX_NAME):
            await self.es_client.delete_by_query(
                index=DISHES_INDEX_NAME, query={"match_all": {}}, refresh=True
            )
            logger.info("Deleted all documents in index '%s'.", DISHES_INDEX_NAME)

    async def bulk_index_dishes(self, documents: List[Dict[str, Any]], *, refresh: bool = True):
        """
        documents: [{"_index": ..., "_id": "...", "_source": {...}}, ...]
        """
        actions = []
        for doc in documents:
            if "_source" in doc:
                actions.append(doc)
            else:
                # 호환성: meta와 source가 합쳐진 형태일 경우 정규화
                idx = doc.get("_index", DISHES_INDEX_NAME)
                _id = doc.get("_id")
                src = {k: v for k, v in doc.items() if not k.startswith("_")}
                actions.append({"_index": idx, "_id": _id, "_source": src})

        success, failed = await async_bulk(self.es_client, actions, refresh=refresh)
        if failed:
            logger.error("Failed to index %d documents.", len(failed))
        else:
            logger.info("Successfully indexed %s documents.", success)
        return {"success": success, "failed": len(failed)}
