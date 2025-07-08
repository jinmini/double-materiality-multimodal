"""
Google Gemini API 연동 서비스
CTO 조언에 따른 안전한 API 사용 패턴 구현 (OpenAI → Gemini 전환)
"""

import os
import logging
from google import genai
from typing import List, Dict, Any, Optional, Tuple
import json
import time
from datetime import datetime

from config import settings
from cost_manager import get_cost_manager

logger = logging.getLogger(__name__)

class GeminiService:
    """Google Gemini API 서비스 클래스"""
    
    def __init__(self):
        self.client = None
        self.cost_manager = get_cost_manager()
        self._initialize_client()
    
    def _initialize_client(self):
        """Gemini 클라이언트 초기화"""
        api_key = os.getenv("GEMINI_API_KEY")
        
        if not api_key:
            logger.warning("GEMINI_API_KEY가 설정되지 않았습니다. Gemini 기능이 비활성화됩니다.")
            return
        
        try:
            # Google GenAI SDK 클라이언트 초기화
            self.client = genai.Client(api_key=api_key)
            logger.info("Gemini 클라이언트 초기화 완료")
        except Exception as e:
            logger.error(f"Gemini 클라이언트 초기화 실패: {e}")
    
    def is_available(self) -> bool:
        """Gemini API 사용 가능 여부 확인"""
        return self.client is not None
    
    def estimate_tokens(self, text: str) -> int:
        """텍스트의 토큰 수 추정 (대략적)"""
        # Gemini는 문자 기반으로 토큰을 계산 (더 정확한 추정)
        # 일반적으로 영어는 4자당 1토큰, 한글은 1.5자당 1토큰
        korean_chars = len([c for c in text if ord(c) >= 0xAC00 and ord(c) <= 0xD7A3])
        other_chars = len(text) - korean_chars
        
        estimated_tokens = int((korean_chars / 1.5) + (other_chars / 4))
        return max(estimated_tokens, len(text.split()) // 2)  # 최소 추정치
    
    def create_materiality_prompt(self, text_content: str) -> str:
        """중대성 이슈 추출을 위한 프롬프트 생성"""
        prompt = f"""
당신은 ESG(환경, 사회, 지배구조) 중대성 평가 전문가입니다. 
다음 지속가능경영보고서 텍스트에서 중대성 이슈를 찾아 JSON 형식으로 정확하게 추출해주세요.

**추출 지침:**
1. 중대성 평가, 이슈 풀, 핵심 이슈, 우선순위 등과 관련된 내용만 식별
2. 각 이슈를 환경(E), 사회(S), 지배구조(G) 중 하나로 분류
3. 중요도/우선순위 정보가 있다면 추출
4. 이해관계자 정보가 있다면 포함

**JSON 출력 형식 (반드시 이 형식을 준수):**
```json
{{
  "materiality_issues": [
    {{
      "issue_name": "구체적인 이슈명",
      "category": "E",
      "priority": "높음",
      "description": "이슈에 대한 설명",
      "stakeholders": ["투자자", "고객"],
      "confidence": 0.9
    }}
  ]
}}
```

**분석할 텍스트:**
{text_content[:4000]}

중요: 반드시 유효한 JSON만 반환하고, 설명문이나 추가 텍스트는 포함하지 마세요.
"""
        return prompt
    
    async def extract_issues_from_text(self, text_content: str) -> Tuple[bool, Dict[str, Any]]:
        """텍스트에서 중대성 이슈 추출"""
        if not self.is_available():
            return False, {"error": "Gemini API가 설정되지 않았습니다."}
        
        # 사전 비용 확인
        prompt = self.create_materiality_prompt(text_content)
        estimated_tokens = self.estimate_tokens(prompt)
        
        can_proceed, message = self.cost_manager.pre_request_check(
            settings.GEMINI_MODEL, estimated_tokens
        )
        
        if not can_proceed:
            logger.warning(f"Gemini API 요청 거부: {message}")
            return False, {"error": message}
        
        try:
            logger.info(f"Gemini API 요청 시작 (예상 토큰: {estimated_tokens})")
            start_time = time.time()
            
            # Gemini API 호출
            response = self.client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=prompt,
                config={
                    "max_output_tokens": settings.GEMINI_MAX_TOKENS,
                    "temperature": 0.1,  # 일관성 있는 결과
                    "candidate_count": 1,
                    "stop_sequences": ["```"]  # JSON 코드 블록 종료
                }
            )
            
            # 응답 처리
            response_time = time.time() - start_time
            
            if not response.candidates:
                return False, {"error": "Gemini API에서 응답을 생성하지 못했습니다."}
            
            content = response.candidates[0].content.parts[0].text.strip()
            
            # JSON 코드 블록에서 추출
            if "```json" in content:
                json_start = content.find("```json") + 7
                json_end = content.find("```", json_start)
                if json_end != -1:
                    content = content[json_start:json_end].strip()
            elif "```" in content:
                # 일반 코드 블록 처리
                json_start = content.find("```") + 3
                json_end = content.find("```", json_start)
                if json_end != -1:
                    content = content[json_start:json_end].strip()
            
            # 토큰 사용량 기록 (Gemini는 usage 정보 제공 방식이 다름)
            # 대략적인 토큰 계산
            input_tokens = estimated_tokens
            output_tokens = self.estimate_tokens(content)
            
            self.cost_manager.record_api_call(
                settings.GEMINI_MODEL, input_tokens, output_tokens
            )
            
            logger.info(f"Gemini API 완료: {response_time:.2f}초, 예상 토큰: {input_tokens + output_tokens}")
            
            # JSON 파싱
            try:
                result = json.loads(content)
                return True, {
                    "success": True,
                    "data": result,
                    "metadata": {
                        "model": settings.GEMINI_MODEL,
                        "tokens_used": input_tokens + output_tokens,
                        "response_time": response_time,
                        "processed_at": datetime.now().isoformat()
                    }
                }
            except json.JSONDecodeError as e:
                logger.error(f"JSON 파싱 실패: {e}")
                logger.debug(f"응답 내용: {content}")
                
                # JSON 수정 시도
                fixed_content = self._fix_json_format(content)
                if fixed_content:
                    try:
                        result = json.loads(fixed_content)
                        logger.info("JSON 자동 수정 성공")
                        return True, {
                            "success": True,
                            "data": result,
                            "metadata": {
                                "model": settings.GEMINI_MODEL,
                                "tokens_used": input_tokens + output_tokens,
                                "response_time": response_time,
                                "processed_at": datetime.now().isoformat(),
                                "json_fixed": True
                            }
                        }
                    except:
                        pass
                
                return False, {
                    "error": "API 응답을 JSON으로 파싱할 수 없습니다.",
                    "raw_response": content[:500]
                }
                
        except Exception as e:
            logger.error(f"Gemini API 호출 중 오류: {e}")
            return False, {"error": f"처리 중 오류 발생: {str(e)}"}
    
    def _fix_json_format(self, content: str) -> Optional[str]:
        """잘못된 JSON 형식을 자동으로 수정 시도"""
        try:
            # 일반적인 JSON 오류 수정
            content = content.strip()
            
            # 불완전한 JSON 완성 시도
            if not content.endswith('}'):
                # 중괄호 부족한 경우
                open_braces = content.count('{')
                close_braces = content.count('}')
                content += '}' * (open_braces - close_braces)
            
            # 불필요한 문자 제거
            if content.startswith('```'):
                content = content[3:]
            if content.endswith('```'):
                content = content[:-3]
            
            return content.strip()
            
        except:
            return None
    
    def merge_extraction_results(self, 
                                unstructured_issues: List[Dict], 
                                gemini_result: Dict) -> List[Dict]:
        """Unstructured와 Gemini 결과를 병합"""
        merged_issues = []
        
        # Unstructured 결과 추가
        for issue in unstructured_issues:
            issue["extraction_method"] = "unstructured"
            merged_issues.append(issue)
        
        # Gemini 결과 추가 (중복 제거)
        if gemini_result.get("success") and gemini_result.get("data"):
            gemini_issues = gemini_result["data"].get("materiality_issues", [])
            
            for gemini_issue in gemini_issues:
                # 간단한 중복 체크 (이슈명 기준)
                is_duplicate = any(
                    self._is_similar_issue(issue, gemini_issue) 
                    for issue in merged_issues
                )
                
                if not is_duplicate:
                    gemini_issue["extraction_method"] = "gemini"
                    gemini_issue["issue_id"] = len(merged_issues) + 1
                    merged_issues.append(gemini_issue)
        
        # 신뢰도순 정렬
        merged_issues.sort(key=lambda x: x.get("confidence", 0), reverse=True)
        
        return merged_issues[:25]  # 최대 25개 반환
    
    def _is_similar_issue(self, issue1: Dict, issue2: Dict) -> bool:
        """두 이슈가 유사한지 확인 (개선된 구현)"""
        name1 = issue1.get("issue_name", "") or issue1.get("content", "")
        name2 = issue2.get("issue_name", "") or issue2.get("content", "")
        
        # 간단한 키워드 기반 유사도 체크
        words1 = set(name1.lower().split())
        words2 = set(name2.lower().split())
        
        if len(words1) == 0 or len(words2) == 0:
            return False
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        # Jaccard 유사도 사용
        similarity = len(intersection) / len(union) if len(union) > 0 else 0
        
        return similarity > 0.3  # 30% 이상 유사하면 중복으로 간주

# 전역 서비스 인스턴스
gemini_service = None

def get_gemini_service() -> GeminiService:
    """전역 Gemini 서비스 인스턴스 반환"""
    global gemini_service
    if gemini_service is None:
        gemini_service = GeminiService()
    return gemini_service 