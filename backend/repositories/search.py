# /backend/repositories/search.py (전체 교체)

import asyncio
from elasticsearch import AsyncElasticsearch
from elasticsearch.helpers import async_bulk
from typing import List, Dict, Any, Optional
from sentence_transformers import SentenceTransformer

from search_client import DISHES_INDEX_NAME

class SearchRepository:
    def __init__(self, es_client: AsyncElasticsearch):
        self.es_client = es_client

    async def search_dishes(
        self,
        query: Optional[str] = None,
        query_vector: Optional[List[float]] = None,
        user_ingredients: Optional[List[str]] = None,
        size: int = 10
    ) -> Dict[str, Any]:
        """
        키워드, 벡터, 재료 필터를 모두 사용하는 다중 채널 하이브리드 검색을 수행합니다.
        """
        if not query and not user_ingredients:
            return {"total": 0, "results": []}

        # 1. 재료 필터 조건 생성
        filter_clauses = []
        if user_ingredients:
            for ingredient in user_ingredients:
                filter_clauses.append({"term": {"ingredients": ingredient}})

        # 2. Elasticsearch 쿼리 본문(body) 구성
        es_body = {
            "size": size,
            "_source": ["dish_id", "recipe_id", "dish_name", "thumbnail_url"],
            "track_total_hits": True  # ✅ 개선: 정확한 total 값 추적
        }

        if query:
            # --- ✅ 개선: 3채널 하이브리드 검색을 위한 RRF 쿼리 ---
            es_body["rank"] = {
                "rrf": [
                    # 채널 1: 키워드 검색 (정확성 담당)
                    {
                        "query": { "match": { "dish_name": { "query": query, "boost": 2.0 }}},
                        "window_size": 50
                    },
                    # 채널 2: 핵심 정체성 벡터 검색 (요리명+재료)
                    {
                        "query": { "knn": { "field": "core_identity_embedding", "query_vector": query_vector, "k": 10, "num_candidates": 50 }},
                        "window_size": 50, "rank_constant": 20
                    },
                    # 채널 3: 맥락/설명 벡터 검색 (자연어)
                    {
                        "query": { "knn": { "field": "context_embedding", "query_vector": query_vector, "k": 10, "num_candidates": 50 }},
                        "window_size": 50, "rank_constant": 20
                    }
                ]
            }
            # 재료 필터는 bool 쿼리로 RRF와 결합
            if filter_clauses:
                es_body["query"] = {"bool": {"filter": filter_clauses}}

        else: # 키워드 검색 없이 재료 필터만 있는 경우
            es_body["query"] = {"bool": {"filter": filter_clauses}}


        # 3. Elasticsearch에 검색 실행
        response = await self.es_client.search(
            index=DISHES_INDEX_NAME,
            body=es_body
        )

        # 4. 결과 파싱 및 반환
        hits = response["hits"]["hits"]
        total = response["hits"]["total"]["value"]
        results = [{"score": hit["_score"], **hit["_source"]} for hit in hits]

        return {"total": total, "results": results}

    async def bulk_index_dishes(self, documents: List[Dict[str, Any]]):
        """여러 요리 문서를 Elasticsearch에 대량으로 색인합니다."""
        if await self.es_client.indices.exists(index=DISHES_INDEX_NAME):
            await self.es_client.delete_by_query(
                index=DISHES_INDEX_NAME, query={"match_all": {}}, refresh=True
            )
            print(f"Deleted all documents in index '{DISHES_INDEX_NAME}'.")

        success, failed = await async_bulk(self.es_client, documents, refresh=True)
        if failed:
            print(f"Failed to index {len(failed)} documents.")
        else:
            print(f"Successfully indexed {success} documents.")
        return {"success": success, "failed": len(failed)}