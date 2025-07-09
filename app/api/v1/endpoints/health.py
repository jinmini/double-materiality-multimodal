# app/api/v1/endpoints/health.py

import logging
from fastapi import APIRouter, Depends

from app.services.document_processing_service import DocumentProcessingService
from app.dependencies.services import get_document_processing_service
from app.schemas.responses import HealthCheckResponse, UsageSummaryResponse

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get(
    "/",
    response_model=HealthCheckResponse,
    summary="헬스 체크",
    description="API 서버의 상태와 사용량을 확인합니다.",
    responses={
        200: {
            "description": "헬스 체크 성공",
            "model": HealthCheckResponse
        }
    }
)
async def health_check(
    service: DocumentProcessingService = Depends(get_document_processing_service)
) -> HealthCheckResponse:
    """
    API 서버의 전반적인 상태를 확인합니다.
    
    **확인 항목:**
    - 서비스 상태
    - 일일 사용량 / 제한
    - 추정 비용 / 비용 제한
    - Gemini API 연결 상태
    """
    logger.info("헬스 체크 요청")
    
    health_data = service.get_health_status()
    logger.info("헬스 체크 완료")
    
    return HealthCheckResponse(**health_data)

@router.get(
    "/usage",
    response_model=UsageSummaryResponse,
    summary="사용량 조회",
    description="API 사용량과 비용 정보를 상세히 조회합니다.",
    responses={
        200: {
            "description": "사용량 조회 성공",
            "model": UsageSummaryResponse
        }
    }
)
async def get_usage_summary(
    service: DocumentProcessingService = Depends(get_document_processing_service)
) -> UsageSummaryResponse:
    """
    API 사용량에 대한 상세한 정보를 제공합니다.
    
    **포함 정보:**
    - 오늘 사용량 (요청 수, 토큰 수, 비용)
    - 일일 제한 설정
    - 총 누적 사용량
    """
    logger.info("사용량 조회 요청")
    
    usage_data = service.get_usage_summary()
    logger.info("사용량 조회 완료")
    
    return UsageSummaryResponse(**usage_data)
