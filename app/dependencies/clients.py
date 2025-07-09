# app/dependencies/clients.py

from functools import lru_cache
from app.core.config import settings
from app.infrastructure.clients.cost_manager_client import CostManagerClient
from app.infrastructure.clients.gemini_client import GeminiClient

# @lru_cache를 사용하여 함수가 처음 호출될 때만 객체를 생성하고,
# 이후에는 캐시된 객체를 반환합니다 (싱글턴 패턴).

@lru_cache
def get_cost_manager_client() -> CostManagerClient:
    """CostManagerClient의 싱글턴 인스턴스를 반환합니다."""
    return CostManagerClient(
        daily_request_limit=settings.DAILY_API_LIMIT,
        daily_cost_limit=settings.DAILY_COST_LIMIT,
        usage_file=settings.UPLOAD_DIR / "api_usage.json"  # 설정에서 경로를 가져옴
    )

@lru_cache
def get_gemini_client() -> GeminiClient:
    """GeminiClient의 싱글턴 인스턴스를 반환합니다."""
    return GeminiClient(
        api_key=settings.GEMINI_API_KEY,
        cost_manager=get_cost_manager_client()  # CostManagerClient를 주입
    ) 