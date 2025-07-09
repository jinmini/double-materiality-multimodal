# app/schemas/responses.py

from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field

class FileInfoResponse(BaseModel):
    """파일 정보 응답 모델"""
    filename: str = Field(..., description="업로드된 파일명")
    file_id: str = Field(..., description="파일의 고유 ID")
    processed_at: datetime = Field(..., description="처리 완료 시간")

class DocumentAnalysisResponse(BaseModel):
    """문서 분석 결과 응답 모델"""
    total_elements: int = Field(..., description="추출된 총 요소 수")
    page_count: int = Field(..., description="페이지 수")
    titles_found: int = Field(..., description="발견된 제목 수")
    tables_found: int = Field(..., description="발견된 테이블 수")

class MaterialityIssueResponse(BaseModel):
    """중대성 이슈 응답 모델"""
    issue_id: int = Field(..., description="이슈 ID")
    category: str = Field(..., description="ESG 카테고리")
    content: str = Field(..., description="이슈 내용")
    page_number: Optional[int] = Field(None, description="페이지 번호")
    element_type: str = Field(..., description="요소 타입")
    confidence: float = Field(..., description="신뢰도 점수")

class ExtractionConfidenceResponse(BaseModel):
    """추출 신뢰도 응답 모델"""
    score: float = Field(..., description="신뢰도 점수 (0-1)")
    level: str = Field(..., description="신뢰도 수준")
    issues_found: int = Field(..., description="발견된 이슈 수")
    has_tables: bool = Field(..., description="테이블 포함 여부")

class DocumentProcessingResponse(BaseModel):
    """문서 처리 전체 응답 모델"""
    file_info: FileInfoResponse
    document_analysis: DocumentAnalysisResponse
    materiality_issues: List[MaterialityIssueResponse]
    esg_content_summary: Dict[str, int] = Field(..., description="ESG 카테고리별 콘텐츠 수")
    extraction_method: str = Field(..., description="추출 방법 (unstructured_only/hybrid)")
    extraction_confidence: ExtractionConfidenceResponse
    gemini_metadata: Optional[Dict[str, Any]] = Field(None, description="Gemini API 메타데이터")

class HealthCheckResponse(BaseModel):
    """헬스 체크 응답 모델"""
    status: str = Field(..., description="서비스 상태")
    timestamp: datetime = Field(..., description="확인 시간")
    daily_usage: int = Field(..., description="오늘 사용량")
    daily_limit: int = Field(..., description="일일 제한")
    estimated_cost: str = Field(..., description="추정 비용")
    cost_limit: str = Field(..., description="비용 제한")
    gemini_available: bool = Field(..., description="Gemini API 사용 가능 여부")

class UsageSummaryResponse(BaseModel):
    """사용량 요약 응답 모델"""
    today: Dict[str, Any] = Field(..., description="오늘 사용량")
    daily_limits: Dict[str, Any] = Field(..., description="일일 제한")
    total_usage: Dict[str, Any] = Field(..., description="총 사용량")

class ErrorResponse(BaseModel):
    """에러 응답 모델"""
    detail: str = Field(..., description="에러 메시지")
    error_code: Optional[str] = Field(None, description="에러 코드")
    timestamp: datetime = Field(default_factory=datetime.now, description="에러 발생 시간")

class SuccessResponse(BaseModel):
    """성공 응답 모델"""
    message: str = Field(..., description="성공 메시지")
    timestamp: datetime = Field(default_factory=datetime.now, description="응답 시간") 