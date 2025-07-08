"""
API 비용 관리 및 사용량 추적 모듈
CTO 조언에 따른 비용 폭탄 방지 시스템
"""

import json
import logging
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Dict, Optional, Tuple
from dataclasses import dataclass, asdict
from threading import Lock

logger = logging.getLogger(__name__)

@dataclass
class APIUsage:
    """API 사용량 기록"""
    date: str
    requests_count: int = 0
    tokens_used: int = 0
    estimated_cost: float = 0.0
    last_updated: str = None
    
    def __post_init__(self):
        if self.last_updated is None:
            self.last_updated = datetime.now().isoformat()

class CostManager:
    """API 비용 및 사용량 관리자"""
    
    # Google Gemini 가격 정보 (2024년 기준, 달러)
    PRICING = {
        "gemini-1.5-flash": {
            "input": 0.075 / 1000000,   # per token ($0.075 per 1M tokens)
            "output": 0.3 / 1000000     # per token ($0.3 per 1M tokens)
        },
        "gemini-1.5-pro": {
            "input": 3.5 / 1000000,     # per token ($3.5 per 1M tokens)
            "output": 10.5 / 1000000    # per token ($10.5 per 1M tokens)
        },
        "gemini-pro": {
            "input": 0.5 / 1000000,     # per token (Legacy model)
            "output": 1.5 / 1000000     # per token
        }
    }
    
    def __init__(self, 
                 daily_request_limit: int = 20,
                 daily_cost_limit: float = 5.0,  # 달러
                 usage_file: str = "api_usage.json"):
        
        self.daily_request_limit = daily_request_limit
        self.daily_cost_limit = daily_cost_limit
        self.usage_file = Path(usage_file)
        self._lock = Lock()
        
        # 사용량 데이터 로드
        self.usage_data = self._load_usage_data()
        
        logger.info(f"CostManager 초기화: 일일 한도 {daily_request_limit}회, ${daily_cost_limit}")
    
    def _load_usage_data(self) -> Dict[str, APIUsage]:
        """사용량 데이터 로드"""
        if not self.usage_file.exists():
            return {}
        
        try:
            with open(self.usage_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # APIUsage 객체로 변환
            usage_data = {}
            for date_str, usage_dict in data.items():
                usage_data[date_str] = APIUsage(**usage_dict)
            
            return usage_data
            
        except Exception as e:
            logger.error(f"사용량 데이터 로드 실패: {e}")
            return {}
    
    def _save_usage_data(self):
        """사용량 데이터 저장"""
        try:
            # APIUsage 객체를 딕셔너리로 변환
            data = {}
            for date_str, usage in self.usage_data.items():
                data[date_str] = asdict(usage)
            
            with open(self.usage_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logger.error(f"사용량 데이터 저장 실패: {e}")
    
    def get_today_usage(self) -> APIUsage:
        """오늘 사용량 조회"""
        today = date.today().isoformat()
        
        if today not in self.usage_data:
            self.usage_data[today] = APIUsage(date=today)
        
        return self.usage_data[today]
    
    def check_limits(self) -> Tuple[bool, str]:
        """사용량 한도 확인"""
        with self._lock:
            today_usage = self.get_today_usage()
            
            # 요청 횟수 한도 확인
            if today_usage.requests_count >= self.daily_request_limit:
                return False, f"일일 요청 한도 초과 ({today_usage.requests_count}/{self.daily_request_limit})"
            
            # 비용 한도 확인
            if today_usage.estimated_cost >= self.daily_cost_limit:
                return False, f"일일 비용 한도 초과 (${today_usage.estimated_cost:.4f}/${self.daily_cost_limit})"
            
            return True, "OK"
    
    def estimate_cost(self, model: str, input_tokens: int = 0, output_tokens: int = 0) -> float:
        """API 호출 비용 추정"""
        if model not in self.PRICING:
            logger.warning(f"알 수 없는 모델: {model}, 기본 가격 적용")
            model = "gemini-1.5-flash"
        
        pricing = self.PRICING[model]
        cost = (input_tokens * pricing["input"]) + (output_tokens * pricing["output"])
        
        return cost
    
    def pre_request_check(self, model: str, estimated_input_tokens: int) -> Tuple[bool, str]:
        """API 요청 전 사전 확인"""
        # 현재 한도 확인
        can_proceed, message = self.check_limits()
        if not can_proceed:
            return False, message
        
        # 예상 비용 확인
        estimated_cost = self.estimate_cost(model, estimated_input_tokens, 0)
        today_usage = self.get_today_usage()
        
        if (today_usage.estimated_cost + estimated_cost) > self.daily_cost_limit:
            return False, f"예상 비용이 일일 한도를 초과합니다 (${estimated_cost:.4f} 추가 시 ${today_usage.estimated_cost + estimated_cost:.4f}/${self.daily_cost_limit})"
        
        return True, "OK"
    
    def record_api_call(self, 
                       model: str, 
                       input_tokens: int, 
                       output_tokens: int,
                       actual_cost: Optional[float] = None):
        """API 호출 기록"""
        with self._lock:
            today_usage = self.get_today_usage()
            
            # 비용 계산
            if actual_cost is None:
                cost = self.estimate_cost(model, input_tokens, output_tokens)
            else:
                cost = actual_cost
            
            # 사용량 업데이트
            today_usage.requests_count += 1
            today_usage.tokens_used += input_tokens + output_tokens
            today_usage.estimated_cost += cost
            today_usage.last_updated = datetime.now().isoformat()
            
            # 저장
            self._save_usage_data()
            
            logger.info(f"API 호출 기록: {model}, 토큰: {input_tokens + output_tokens}, 비용: ${cost:.4f}")
    
    def get_usage_summary(self, days: int = 7) -> Dict:
        """사용량 요약 조회"""
        summary = {
            "today": asdict(self.get_today_usage()),
            "daily_limits": {
                "requests": self.daily_request_limit,
                "cost": self.daily_cost_limit
            },
            "recent_days": []
        }
        
        # 최근 일주일 데이터
        for i in range(days):
            date_obj = date.today() - timedelta(days=i)
            date_str = date_obj.isoformat()
            
            if date_str in self.usage_data:
                day_data = asdict(self.usage_data[date_str])
                day_data["date"] = date_str
                summary["recent_days"].append(day_data)
        
        return summary
    
    def reset_daily_usage(self, target_date: Optional[str] = None):
        """일일 사용량 리셋 (테스트용)"""
        if target_date is None:
            target_date = date.today().isoformat()
        
        with self._lock:
            if target_date in self.usage_data:
                del self.usage_data[target_date]
                self._save_usage_data()
                logger.info(f"사용량 리셋: {target_date}")

# 전역 비용 관리자 인스턴스
cost_manager = None

def get_cost_manager() -> CostManager:
    """전역 비용 관리자 인스턴스 반환"""
    global cost_manager
    if cost_manager is None:
        cost_manager = CostManager()
    return cost_manager

# 편의 함수들
def check_api_limits() -> Tuple[bool, str]:
    """API 한도 확인"""
    return get_cost_manager().check_limits()

def record_api_call_simple(model: str, input_tokens: int, output_tokens: int):
    """AI API 호출 기록 (간단 버전)"""
    get_cost_manager().record_api_call(model, input_tokens, output_tokens)

def get_usage_info() -> Dict:
    """사용량 정보 조회"""
    return get_cost_manager().get_usage_summary() 