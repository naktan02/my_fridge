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

    # 내부 헬퍼: 재료 필터 (ALL / ANY / RATIO 지원)
    def _ingredient_filter(
        self,
        user_ingredients: Optional[List[str]],
        mode: str = "ALL",   # 기본값: 전부 포함(AND)
        ratio: float = 0.6    # RATIO 모드에서 최소 일치 비율
    ) -> Optional[Dict[str, Any]]:
        if not user_ingredients:
            return None

        # 입력 정규화(공백/대소문자 이슈 방지 – 색인도 동일 정책 권장)
        terms = [ing.strip() for ing in user_ingredients if ing and ing.strip()]
        if not terms:
            return None

        if mode == "ALL":
            # 모든 재료가 포함되어야 함 (AND)
            return {"bool": {"filter": [{"term": {"ingredients": ing}} for ing in terms]}}

        if mode == "ANY":
            # 하나라도 포함되면 통과 (OR)
            return {
                "bool": {
                    "should": [{"term": {"ingredients": ing}} for ing in terms],
                    "minimum_should_match": 1
                }
            }

        if mode == "RATIO":
            # 비율 기반 부분 일치
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

    async def search_dishes(
        self,
        query: Optional[str] = None,
        query_vector: Optional[List[float]] = None,
        user_ingredients: Optional[List[str]] = None,
        size: int = 10
    ) -> Dict[str, Any]:
        """
        키워드(BM25), 벡터(kNN), 재료 필터를 조합한 하이브리드 검색.
        - ES 8.x RRF 문법: retriever.rrf.retrievers[*] (standard/knn)
        - query_vector가 없으면 BM25만 수행(안전한 강등)
        """
        if not query and not user_ingredients:
            return {"total": 0, "results": []}

        body: Dict[str, Any] = {
            "size": size,
            "_source": ["dish_id", "recipe_id", "dish_name", "thumbnail_url"],
            "track_total_hits": True
        }

        # 1) 재료 필터(기본 ALL). 필요하면 아래 mode를 "ANY" / "RATIO"로 바꿔 써라.
        ingredient_query = self._ingredient_filter(user_ingredients, mode="ALL", ratio=0.6)
        if ingredient_query:
            body["query"] = ingredient_query

        # 2) RRF 하이브리드(쿼리가 있을 때만)
        if query:
            retrievers: List[Dict[str, Any]] = [
                # 표준 BM25 채널 (dish_name 우선, boost 2.0)
                {"standard": {"query": {"match": {"dish_name": {"query": query, "boost": 2.0}}}}}
            ]

            # 쿼리 임베딩이 있을 때만 kNN 채널 추가
            if query_vector is not None:
                retrievers.extend([
                    {
                        "knn": {
                            "field": "core_identity_embedding",
                            "query_vector": query_vector,
                            "k": 10,
                            "num_candidates": 50
                        }
                    },
                    {
                        "knn": {
                            "field": "context_embedding",
                            "query_vector": query_vector,
                            "k": 10,
                            "num_candidates": 50
                        }
                    },
                ])

            body["retriever"] = {
                "rrf": {
                    "retrievers": retrievers,
                    "rank_window_size": 50,
                    "rank_constant": 20
                }
            }

        # 3) 검색 실행
        resp = await self.es_client.search(index=DISHES_INDEX_NAME, body=body)

        # 4) 결과 파싱
        hits = resp.get("hits", {}).get("hits", [])
        total = resp.get("hits", {}).get("total", {}).get("value", 0)
        results = [{"score": h.get("_score"), **(h.get("_source") or {})} for h in hits]
        return {"total": total, "results": results}

    async def bulk_index_dishes(self, documents: List[Dict[str, Any]]):
        """
        여러 요리 문서를 대량 색인.
        documents 예시:
          {"_index": DISHES_INDEX_NAME, "_id": "dish_recipe", "_source": {...}} 형태 권장
        """
        if await self.es_client.indices.exists(index=DISHES_INDEX_NAME):
            await self.es_client.delete_by_query(
                index=DISHES_INDEX_NAME, query={"match_all": {}}, refresh=True
            )
            logger.info("Deleted all documents in index '%s'.", DISHES_INDEX_NAME)

        success, failed = await async_bulk(self.es_client, documents, refresh=True)

        if failed:
            logger.error("Failed to index %d documents.", len(failed))
        else:
            logger.info("Successfully indexed %s documents.", success)

        return {"success": success, "failed": len(failed)}
