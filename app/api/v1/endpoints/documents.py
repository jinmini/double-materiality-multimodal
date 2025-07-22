# app/api/v1/endpoints/documents.py

import logging
import os
import uuid
from pathlib import Path
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

from app.services.document_processing_service import DocumentProcessingService
from app.dependencies.services import get_document_processing_service
from app.schemas.responses import (
    DocumentProcessingResponse, 
    SuccessResponse,
    ErrorResponse
)

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post(
    "/upload-fast",
    summary="빠른 문서 업로드 및 중대성 이슈 추출",
    description="PDF 파일을 빠르게 처리하여 ESG 중대성 이슈를 추출합니다 (최적화 버전).",
    responses={
        200: {"description": "문서 처리 성공"},
        400: {"description": "잘못된 파일 형식"},
        422: {"description": "파일 처리 실패"},
        500: {"description": "서버 내부 오류"}
    }
)
async def upload_document_fast(
    file: UploadFile = File(..., description="업로드할 PDF 파일"),
    service: DocumentProcessingService = Depends(get_document_processing_service)
):
    """
    최적화된 ESG 문서 처리 - 빠른 처리를 위한 경량화 버전
    
    **특징:**
    - FAST 전략 우선 사용
    - 무거운 처리 옵션 비활성화
    - 5분 이내 처리 목표
    """
    logger.info(f"🔵 빠른 문서 업로드 요청: {file.filename}")
    
    file_id = str(uuid.uuid4())
    temp_file_path = f"temp_uploads/{file_id}.pdf"
    
    try:
        # 파일 저장
        logger.info(f"🔵 파일 저장 시작: {temp_file_path}")
        with open(temp_file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        logger.info(f"🔵 파일 저장 완료 - 크기: {len(content)} bytes")
        
        # 최적화된 처리 호출
        logger.info(f"🔵 최적화된 문서 처리 시작")
        result = await service.process_document(temp_file_path)
        
        logger.info(f"🔵 문서 처리 완료: {file.filename}")
        return JSONResponse(content=result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 오류 발생: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # 임시 파일 삭제
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
            logger.info(f"🔵 임시 파일 삭제 완료: {temp_file_path}")

@router.post(
    "/upload-vision",
    response_model=DocumentProcessingResponse,
    summary="Gemini Vision API 기반 문서 처리",
    description="PDF 파일을 Gemini Vision API로 처리하여 표/매트릭스 구조의 중대성 이슈를 추출합니다.",
    responses={
        200: {
            "description": "Vision API 처리 성공",
            "model": DocumentProcessingResponse
        },
        400: {
            "description": "잘못된 파일 형식",
            "model": ErrorResponse
        },
        413: {
            "description": "파일 크기 초과",
            "model": ErrorResponse
        },
        500: {
            "description": "서버 오류",
            "model": ErrorResponse
        }
    },
    operation_id="upload_document_vision"
)
async def upload_document_vision(
    file: UploadFile = File(..., description="업로드할 PDF 파일"),
    service: DocumentProcessingService = Depends(get_document_processing_service)
):
    """
    🔍 Gemini Vision API 기반 문서 처리
    
    특징:
    - 표, 매트릭스, 차트 구조 인식 가능
    - 이미지 기반 PDF 처리 최적화
    - 높은 정확도의 중대성 이슈 추출
    """
    logger.info(f"🔍 Vision API 문서 업로드 요청: {file.filename}")
    
    file_id = str(uuid.uuid4())
    temp_file_path = f"temp_uploads/{file_id}.pdf"
    
    try:
        # 파일 저장
        logger.info(f"🔍 파일 저장 시작: {temp_file_path}")
        with open(temp_file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        logger.info(f"🔍 파일 저장 완료 - 크기: {len(content)} bytes")
        
        # Vision API 처리 호출
        logger.info(f"🔍 Gemini Vision API 문서 처리 시작")
        result = await service.process_document_with_vision(temp_file_path)
        
        logger.info(f"🔍 Vision API 처리 완료: {file.filename}")
        return JSONResponse(content=result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Vision API 오류 발생: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # 임시 파일 삭제
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
            logger.info(f"🔍 임시 파일 삭제 완료: {temp_file_path}")

@router.post(
    "/upload",
    response_model=DocumentProcessingResponse,
    summary="문서 업로드 및 중대성 이슈 추출",
    description="PDF 파일을 업로드하여 ESG 중대성 이슈를 자동으로 추출합니다.",
    responses={
        200: {
            "description": "문서 처리 성공",
            "model": DocumentProcessingResponse
        },
        400: {
            "description": "잘못된 파일 형식",
            "model": ErrorResponse
        },
        413: {
            "description": "파일 크기 초과",
            "model": ErrorResponse
        },
        422: {
            "description": "파일 처리 실패",
            "model": ErrorResponse
        },
        429: {
            "description": "API 사용량 제한 초과",
            "model": ErrorResponse
        },
        500: {
            "description": "서버 내부 오류",
            "model": ErrorResponse
        }
    }
)
async def upload_document(
    file: UploadFile = File(..., description="업로드할 PDF 파일"),
    service: DocumentProcessingService = Depends(get_document_processing_service)
) -> DocumentProcessingResponse:
    """
    ESG 지속가능경영보고서 PDF 파일을 업로드하여 중대성 이슈를 추출합니다.
    
    **지원 파일 형식**: PDF
    **최대 파일 크기**: 50MB
    **추출 방법**: Unstructured + Gemini AI (선택적)
    
    **처리 과정:**
    1. 파일 검증 (크기, 형식)
    2. API 사용량 제한 확인
    3. PDF 텍스트 추출
    4. 중대성 이슈 식별
    5. ESG 카테고리 분류
    6. 신뢰도 점수 계산
    """
    logger.info(f"문서 업로드 요청: {file.filename}")
    
    try:
        result = await service.process_uploaded_file(file)
        logger.info(f"문서 처리 완료: {file.filename}")
        return DocumentProcessingResponse(**result)
    
    except HTTPException:
        # FastAPI HTTPException은 그대로 전파
        raise
    except Exception as e:
        logger.error(f"예상치 못한 오류: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"서버 내부 오류가 발생했습니다: {str(e)}"
        )

@router.post(
    "/reset-usage",
    response_model=SuccessResponse,
    summary="일일 사용량 리셋",
    description="개발/테스트 목적으로 오늘의 API 사용량을 리셋합니다.",
    responses={
        200: {
            "description": "사용량 리셋 성공",
            "model": SuccessResponse
        }
    }
)
async def reset_daily_usage(
    service: DocumentProcessingService = Depends(get_document_processing_service)
) -> SuccessResponse:
    """
    오늘의 API 사용량을 리셋합니다.
    
    **주의**: 이 기능은 개발 및 테스트 목적으로만 사용하세요.
    프로덕션 환경에서는 제거하거나 관리자 권한으로 제한해야 합니다.
    """
    logger.info("일일 사용량 리셋 요청")
    
    try:
        result = service.reset_daily_usage()
        logger.info("일일 사용량 리셋 완료")
        return SuccessResponse(**result)
    
    except Exception as e:
        logger.error(f"사용량 리셋 실패: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"사용량 리셋 중 오류가 발생했습니다: {str(e)}"
        )

class MaterialityIssue(BaseModel):
    issue_id: int
    issue_name: str
    esg_category: str  # "E", "S", "G"
    stakeholder_interest: str  # "높음", "보통", "낮음"
    business_impact: str  # "높음", "보통", "낮음" 
    priority_level: str  # "핵심", "일반", "모니터링"
    description: str
    confidence_score: float
    page_references: List[int]

class MaterialityAssessmentResponse(BaseModel):
    total_issues_found: int
    core_issues: List[MaterialityIssue]  # 상위 3-4개
    standard_issues: List[MaterialityIssue]  # 일반 이슈들
    monitoring_issues: List[MaterialityIssue]  # 모니터링 대상
    processing_summary: dict

@router.post(
    "/materiality-assessment", 
    response_model=MaterialityAssessmentResponse,
    summary="ESG 중대성 평가 이슈 추출",
    description="ESG 보고서에서 표준화된 중대성 이슈들을 정확하게 추출합니다."
)
async def extract_materiality_issues(
    file: UploadFile = File(...),
    service: DocumentProcessingService = Depends(get_document_processing_service)
) -> MaterialityAssessmentResponse:
    """SaaS 플랫폼용 중대성 평가 API"""
    # 빠르고 정확한 처리 로직
