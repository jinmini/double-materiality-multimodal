# app/infrastructure/clients/cost_manager_client.py

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
    """API 사용량 기록 데이터 클래스"""
    date: str
    requests_count: int = 0
    tokens_used: int = 0
    estimated_cost: float = 0.0
    last_updated: str = None
    
    def __post_init__(self):
        if self.last_updated is None:
            self.last_updated = datetime.now().isoformat()

class CostManagerClient:
    """
    API 비용 및 사용량을 관리하는 클라이언트.
    파일 기반 데이터베이스를 사용하여 사용량을 추적합니다.
    """
    
    # Google Gemini 가격 정보 (2025년 1월 기준, 달러)
    # 도메인 로직과 무관한 외부 서비스의 가격 정보이므로 여기에 위치합니다.
    PRICING = {
        # ✅ Gemini 2.0 Flash (무료 등급 - 2025년 테스트용)
        "gemini-2.0-flash": {"input": 0.0, "output": 0.0},  # 무료 등급
        
        # Gemini 2.5 Flash (Preview)
        "gemini-2.5-flash": {"input": 0.075 / 1_000_000, "output": 0.3 / 1_000_000},
        "gemini-2.5-flash-8b": {"input": 0.0375 / 1_000_000, "output": 0.15 / 1_000_000},
        
        # Gemini 1.5 모델들 (기존 지원)
        "gemini-1.5-flash": {"input": 0.075 / 1_000_000, "output": 0.3 / 1_000_000},
        "gemini-1.5-flash-8b": {"input": 0.0375 / 1_000_000, "output": 0.15 / 1_000_000},
        "gemini-1.5-pro": {"input": 3.5 / 1_000_000, "output": 10.5 / 1_000_000},
        
        # 기존 모델 (호환성)
        "gemini-pro": {"input": 0.5 / 1_000_000, "output": 1.5 / 1_000_000}
    }
    
    def __init__(self, 
                 daily_request_limit: int,
                 daily_cost_limit: float,
                 usage_file: Path):
        
        self.daily_request_limit = daily_request_limit
        self.daily_cost_limit = daily_cost_limit
        self.usage_file = usage_file
        self._lock = Lock()  # 멀티스레드 환경에서의 파일 접근 동기화
        
        self.usage_data = self._load_usage_data()
        logger.info(
            f"CostManagerClient 초기화: 일일 한도 {daily_request_limit}회, ${daily_cost_limit:.2f}"
        )
    
    def _load_usage_data(self) -> Dict[str, APIUsage]:
        """JSON 파일에서 사용량 데이터를 로드합니다."""
        if not self.usage_file.exists():
            return {}
        
        with self._lock:
            try:
                with open(self.usage_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return {date_str: APIUsage(**usage_dict) for date_str, usage_dict in data.items()}
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"사용량 데이터 로드 실패: {e}")
                return {}
    
    def _save_usage_data(self):
        """사용량 데이터를 JSON 파일에 저장합니다."""
        try:
            # 🔥 임시 해결책: 파일 저장을 비동기적으로 처리 (블로킹 방지)
            data_to_save = {date_str: asdict(usage) for date_str, usage in self.usage_data.items()}
            
            # Lock 없이 직접 저장 시도 (빠른 처리)
            import tempfile
            import os
            
            # 임시 파일에 먼저 저장 후 원본으로 이동 (atomic operation)
            temp_file = str(self.usage_file) + ".tmp"
            
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(data_to_save, f, indent=2, ensure_ascii=False)
            
            # 원본 파일로 이동 (Windows에서 안전한 방법)
            if os.path.exists(self.usage_file):
                os.remove(self.usage_file)
            os.rename(temp_file, self.usage_file)
            
            logger.info(f"✅ 사용량 데이터 저장 완료: {self.usage_file}")
            
        except Exception as e:
            logger.warning(f"⚠️ 사용량 데이터 저장 실패 (계속 진행): {e}")
            # 🔥 중요: 예외가 발생해도 프로그램 흐름을 중단하지 않음
    
    def get_today_usage(self) -> APIUsage:
        """오늘 날짜의 사용량 객체를 가져오거나 생성합니다."""
        today_str = date.today().isoformat()
        if today_str not in self.usage_data:
            self.usage_data[today_str] = APIUsage(date=today_str)
        return self.usage_data[today_str]
    
    def check_limits(self) -> Tuple[bool, str]:
        """현재 사용량이 일일 한도를 초과하는지 확인합니다."""
        today_usage = self.get_today_usage()
        
        if today_usage.requests_count >= self.daily_request_limit:
            msg = f"일일 요청 한도 초과 ({today_usage.requests_count}/{self.daily_request_limit})"
            logger.warning(msg)
            return False, msg
        
        if today_usage.estimated_cost >= self.daily_cost_limit:
            msg = f"일일 비용 한도 초과 (${today_usage.estimated_cost:.4f}/${self.daily_cost_limit:.2f})"
            logger.warning(msg)
            return False, msg
            
        return True, "사용량 한도 내입니다."
    
    def estimate_cost(self, model: str, input_tokens: int = 0, output_tokens: int = 0) -> float:
        """API 호출 비용을 추정합니다."""
        pricing = self.PRICING.get(model, self.PRICING["gemini-1.5-flash"])
        if model not in self.PRICING:
            logger.warning(f"알 수 없는 모델: {model}, 기본 가격 적용")
        
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
    
    def record_api_call(self, model: str, input_tokens: int, output_tokens: int, actual_cost: Optional[float] = None):
        """API 호출 결과를 기록하고 사용량을 업데이트합니다."""
        try:
            cost = actual_cost if actual_cost is not None else self.estimate_cost(model, input_tokens, output_tokens)
            logger.info(f"🔍 비용 계산 완료: ${cost:.6f}")
            
            # Lock 획득 시도 (타임아웃 없지만 빠른 처리)
            acquired = self._lock.acquire(blocking=False)
            if not acquired:
                logger.warning("⚠️ Lock 획득 실패, 비동기 처리로 건너뛰기")
                return
            
            try:
                logger.info(f"🔍 사용량 업데이트 시작")
                today_usage = self.get_today_usage()
                today_usage.requests_count += 1
                today_usage.tokens_used += input_tokens + output_tokens
                today_usage.estimated_cost += cost
                today_usage.last_updated = datetime.now().isoformat()
                
                logger.info(f"🔍 파일 저장 시작")
                
                # 🔥 타임아웃 옵션: 파일 저장에 시간 제한 적용
                import signal
                import time
                
                def timeout_handler(signum, frame):
                    raise TimeoutError("파일 저장 타임아웃")
                
                try:
                    # 5초 타임아웃 설정 (Windows에서는 이 방법이 제한적일 수 있음)
                    old_handler = signal.signal(signal.SIGALRM, timeout_handler) if hasattr(signal, 'SIGALRM') else None
                    if hasattr(signal, 'alarm'):
                        signal.alarm(5)  # 5초 타임아웃
                    
                    save_start = time.time()
                    self._save_usage_data()
                    save_time = time.time() - save_start
                    
                    if hasattr(signal, 'alarm'):
                        signal.alarm(0)  # 타임아웃 해제
                    if old_handler:
                        signal.signal(signal.SIGALRM, old_handler)
                    
                    logger.info(f"🔍 파일 저장 완료 ({save_time:.2f}초)")
                    
                except (TimeoutError, Exception) as e:
                    if hasattr(signal, 'alarm'):
                        signal.alarm(0)  # 타임아웃 해제
                    logger.warning(f"⚠️ 파일 저장 실패/타임아웃 (무시하고 계속): {e}")
                
                logger.info(
                    f"API 호출 기록: {model}, 토큰: {input_tokens+output_tokens}, 비용: ${cost:.6f}, "
                    f"오늘 누적 요청: {today_usage.requests_count}, 누적 비용: ${today_usage.estimated_cost:.4f}"
                )
            finally:
                self._lock.release()
                
        except Exception as e:
            logger.error(f"❌ API 호출 기록 실패: {e}")
            logger.info("⚠️ 사용량 기록 실패했지만 계속 진행")
    
    def get_usage_summary(self, days: int = 7) -> Dict:
        """최근 사용량 요약을 반환합니다."""
        summary = {
            "today": asdict(self.get_today_usage()),
            "daily_limits": {
                "requests": self.daily_request_limit,
                "cost": self.daily_cost_limit
            },
            "recent_days": [
                asdict(self.usage_data[d_str])
                for i in range(days)
                if (d_str := (date.today() - timedelta(days=i)).isoformat()) in self.usage_data
            ]
        }
        return summary
    
    def reset_daily_usage(self, target_date_str: Optional[str] = None):
        """특정 날짜의 사용량을 리셋합니다 (테스트용)."""
        if target_date_str is None:
            target_date_str = date.today().isoformat()
        
        with self._lock:
            if target_date_str in self.usage_data:
                del self.usage_data[target_date_str]
                self._save_usage_data()
                logger.info(f"사용량 리셋 완료: {target_date_str}") 