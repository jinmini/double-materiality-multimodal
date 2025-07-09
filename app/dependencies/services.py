# app/dependencies/services.py

from functools import lru_cache
from app.services.document_processing_service import DocumentProcessingService
from app.dependencies.clients import get_cost_manager_client, get_gemini_client

@lru_cache
def get_document_processing_service() -> DocumentProcessingService:
    """DocumentProcessingService의 싱글턴 인스턴스를 반환합니다."""
    return DocumentProcessingService(
        cost_manager=get_cost_manager_client(),
        gemini_client=get_gemini_client()
    ) 