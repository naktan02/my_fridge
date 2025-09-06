# /backend/repositories/search.py (신규 생성)

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
        embedding_model: SentenceTransformer,
        query: Optional[str] = None,
        user_ingredients: Optional[List[str]] = None,
        size: int = 10
    ) -> Dict[str, Any]:
        """
        자연어 쿼리와 재료 필터를 사용하여 요리를 검색합니다 (하이브리드 검색).
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
            "_source": ["dish_id", "recipe_id", "dish_name", "thumbnail_url"]
        }

        if query:
            # --- ✅ 하이브리드 검색을 위한 쿼리 재구성 ---
            query_vector = embedding_model.encode(query).tolist()
            
            es_body["query"] = {
                "bool": {
                    # 재료 필터는 여기에 적용
                    "filter": filter_clauses
                }
            }
            
            # RRF를 사용하여 키워드 검색과 벡터 검색 결과를 결합
            es_body["rank"] = {
                "rrf": [
                    {
                        "query": {
                            "match": {
                                "dish_name": {
                                    "query": query,
                                    "boost": 1.0 # 키워드 검색 가중치
                                }
                            }
                        },
                        "window_size": 50
                    },
                    {
                        "query": {
                            "knn": {
                                "field": "recipe_embedding",
                                "query_vector": query_vector,
                                "k": 10,
                                "num_candidates": 50
                            }
                        },
                        "window_size": 50,
                        "rank_constant": 20
                    }
                ]
            }
        else:
            # 쿼리가 없고 재료 필터만 있는 경우
            es_body["query"] = {
                "bool": {
                    "filter": filter_clauses
                }
            }

        # 3. Elasticsearch에 검색 실행
        response = await self.es_client.search(
            index=DISHES_INDEX_NAME,
            body=es_body
        )
        
        # ... (결과 파싱 부분은 기존과 동일)
        hits = response["hits"]["hits"]
        total = response["hits"]["total"]["value"]
        results = [
            {
                "score": hit["_score"],
                **hit["_source"]
            } for hit in hits
        ]
        
        return {"total": total, "results": results}
    
    async def bulk_index_dishes(self, documents: List[Dict[str, Any]]):
        """
        여러 요리 문서를 Elasticsearch에 대량으로 색인합니다.
        문서 형식: {"_index": "인덱스명", "_id": "문서ID", "_source": {문서내용}}
        """
        
        # 1. 기존 인덱스의 모든 문서를 삭제합니다. (멱등성을 위해)
        # 만약 기존 데이터를 유지하고 싶다면 이 부분을 주석 처리하거나 로직을 변경해야 합니다.
        if await self.es_client.indices.exists(index=DISHES_INDEX_NAME):
            await self.es_client.delete_by_query(
                index=DISHES_INDEX_NAME,
                query={"match_all": {}},
                refresh=True
            )
            print(f"Deleted all documents in index '{DISHES_INDEX_NAME}'.")

        # 2. 새로운 문서들을 대량으로 삽입합니다.
        success, failed = await async_bulk(self.es_client, documents, refresh=True)
        
        if failed:
            print(f"Failed to index {len(failed)} documents.")
        else:
            print(f"Successfully indexed {success} documents.")
            
        return {"success": success, "failed": len(failed)}