from fastapi import APIRouter
from app.api.v1.endpoints import documents, health

api_router = APIRouter()

# 문서 처리 관련 엔드포인트
api_router.include_router(
    documents.router, 
    prefix="/documents", 
    tags=["Documents"],
    responses={
        400: {"description": "잘못된 요청"},
        429: {"description": "API 사용량 제한 초과"},
        500: {"description": "서버 내부 오류"}
    }
)

# 헬스 체크 및 모니터링 엔드포인트
api_router.include_router(
    health.router, 
    prefix="/health", 
    tags=["Health & Monitoring"],
    responses={
        500: {"description": "서버 내부 오류"}
    }
)

