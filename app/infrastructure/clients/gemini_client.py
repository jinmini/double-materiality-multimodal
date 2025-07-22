# app/infrastructure/clients/gemini_client.py

import os
import logging
import asyncio
import google.generativeai as genai  # 올바른 google-generativeai 라이브러리
from typing import List, Dict, Any, Optional, Tuple
import json
import time
from datetime import datetime

# 의존성 주입을 위해 CostManagerClient를 임포트합니다.
from app.infrastructure.clients.cost_manager_client import CostManagerClient

logger = logging.getLogger(__name__)

class GeminiClient:
    """
    Google Gemini API 클라이언트 (google-generativeai 라이브러리 사용)
    """
    
    def __init__(self, api_key: Optional[str], cost_manager: CostManagerClient):
        self.api_key = api_key
        self.cost_manager = cost_manager  # 의존성 주입
        self.client = self._initialize_client()

    def _initialize_client(self) -> Optional[bool]:
        """Gemini 클라이언트를 초기화합니다."""
        if not self.api_key:
            logger.warning("GEMINI_API_KEY가 설정되지 않았습니다. Gemini 기능이 비활성화됩니다.")
            return None
        try:
            # google-generativeai 라이브러리의 표준 초기화 방법
            genai.configure(api_key=self.api_key)
            logger.info("GeminiClient 초기화 완료 (google-generativeai 라이브러리)")
            return True
        except Exception as e:
            logger.error(f"Gemini 클라이언트 초기화 실패: {e}")
            return None
    
    def is_available(self) -> bool:
        """Gemini API 사용 가능 여부를 확인합니다."""
        return self.client is not None
    
    def estimate_tokens(self, text: str) -> int:
        """텍스트의 토큰 수 추정 (Gemini 2.5 개선된 추정)"""
        # Gemini 2.5는 더 효율적인 토큰화를 사용
        # 한글: 1.2자당 1토큰, 영어: 3.5자당 1토큰 (개선된 비율)
        korean_chars = len([c for c in text if ord(c) >= 0xAC00 and ord(c) <= 0xD7A3])
        other_chars = len(text) - korean_chars
        
        estimated_tokens = int((korean_chars / 1.2) + (other_chars / 3.5))
        return max(estimated_tokens, len(text.split()) // 3)  # 최소 추정치 개선
    
    def _create_materiality_prompt(self, text_content: str) -> str:
        """중대성 이슈 추출을 위한 프롬프트 생성 (Gemini 2.5 최적화)"""
        prompt = f"""
당신은 ESG(환경, 사회, 지배구조) 중대성 평가 전문가입니다. 
다음 지속가능경영보고서 텍스트에서 중대성 이슈를 찾아 JSON 형식으로 정확하게 추출해주세요.

**사고 과정 (Thinking):**
1. 먼저 텍스트에서 중대성 평가 관련 섹션을 식별
2. 각 이슈의 ESG 분류 근거를 분석  
3. 우선순위 및 중요도 정보 확인
4. 이해관계자와의 연관성 파악

**추출 지침:**
1. 중대성 평가, 이슈 풀, 핵심 이슈, 우선순위 등과 관련된 내용만 식별
2. 각 이슈를 환경(E), 사회(S), 지배구조(G) 중 하나로 분류
3. 중요도/우선순위 정보가 있다면 추출
4. 이해관계자 정보가 있다면 포함
5. 신뢰도는 텍스트에서 명시적으로 언급된 정도에 따라 설정

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
      "confidence": 0.9,
      "source_context": "텍스트에서 발견된 맥락 정보"
    }}
  ],
  "analysis_summary": {{
    "total_issues_found": 0,
    "high_confidence_issues": 0,
    "esg_distribution": {{"E": 0, "S": 0, "G": 0}}
  }}
}}
```

**분석할 텍스트:**
{text_content[:4000]}

중요: 반드시 유효한 JSON만 반환하고, 설명문이나 추가 텍스트는 포함하지 마세요.
"""
        return prompt

    async def extract_issues_from_text(
        self, text_content: str, model: str, max_output_tokens: int
    ) -> Tuple[bool, Dict[str, Any]]:
        """텍스트에서 중대성 이슈를 추출합니다. (google-generativeai 라이브러리 사용)"""
        if not self.is_available():
            return False, {"error": "Gemini API가 설정되지 않았습니다."}
        
        prompt = self._create_materiality_prompt(text_content)
        estimated_tokens = self.estimate_tokens(prompt)
        
        # 사전 비용 확인
        can_proceed, message = self.cost_manager.pre_request_check(model, estimated_tokens)
        if not can_proceed:
            logger.warning(f"Gemini API 요청 거부 (사전 확인): {message}")
            return False, {"error": message}
        
        try:
            logger.info(f"Gemini API 요청 시작 (모델: {model}, 예상 토큰: {estimated_tokens})")
            start_time = time.time()
            
            # google-generativeai 라이브러리 표준 사용법
            model_instance = genai.GenerativeModel(model)
            
            # Gemini 2.5에서 개선된 생성 설정
            generation_config = genai.types.GenerationConfig(
                max_output_tokens=max_output_tokens,
                temperature=0.1,  # 일관성 있는 결과
                candidate_count=1,
                response_mime_type="application/json"  # JSON 응답 강제
            )
            
            response = model_instance.generate_content(
                prompt,
                generation_config=generation_config
            )
            
            response_time = time.time() - start_time
            
            if not response.candidates or not response.text:
                return False, {"error": "Gemini API에서 응답을 생성하지 못했습니다."}
            
            content = response.text.strip()
            
            # 토큰 사용량 추정 (실제 usage_metadata가 있다면 사용)
            input_tokens = estimated_tokens
            output_tokens = self.estimate_tokens(content)
            
            # response.usage_metadata가 있다면 실제 값 사용
            if hasattr(response, 'usage_metadata') and response.usage_metadata:
                if hasattr(response.usage_metadata, 'prompt_token_count'):
                    input_tokens = response.usage_metadata.prompt_token_count
                if hasattr(response.usage_metadata, 'candidates_token_count'):
                    output_tokens = response.usage_metadata.candidates_token_count

            # 비용 기록
            self.cost_manager.record_api_call(model, input_tokens, output_tokens)
            
            logger.info(f"Gemini API 완료: {response_time:.2f}초, 토큰(in/out): {input_tokens}/{output_tokens}")
            
            # JSON 파싱
            try:
                result = json.loads(content)
                return True, {
                    "success": True,
                    "data": result,
                    "metadata": {
                        "model": model,
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                        "total_tokens": input_tokens + output_tokens,
                        "response_time_ms": int(response_time * 1000),
                        "estimated_cost": self.cost_manager.estimate_cost(model, input_tokens, output_tokens),
                        "processed_at": datetime.now().isoformat(),
                        "gemini_version": "2.5",
                        "sdk_version": "google-generativeai"
                    }
                }
            except json.JSONDecodeError as e:
                logger.error(f"JSON 파싱 실패: {e}")
                logger.debug(f"응답 내용: {content[:500]}")
                
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
                                "model": model,
                                "input_tokens": input_tokens,
                                "output_tokens": output_tokens,
                                "total_tokens": input_tokens + output_tokens,
                                "response_time_ms": int(response_time * 1000),
                                "estimated_cost": self.cost_manager.estimate_cost(model, input_tokens, output_tokens),
                                "processed_at": datetime.now().isoformat(),
                                "json_fixed": True,
                                "gemini_version": "2.5",
                                "sdk_version": "google-generativeai"
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

    async def analyze_image_with_text(
        self, 
        image_base64: str, 
        prompt: str, 
        model_name: str = "gemini-1.5-pro",
        max_tokens: int = 1000
    ) -> Dict[str, Any]:
        """
        Base64 이미지와 텍스트 프롬프트를 함께 분석
        
        Args:
            image_base64: Base64 인코딩된 이미지
            prompt: 분석 프롬프트
            model_name: 사용할 모델명
            max_tokens: 최대 출력 토큰 수
            
        Returns:
            Dict: 분석 결과
        """
        if not self.is_available():
            raise Exception("Gemini API가 설정되지 않았습니다.")
        
        try:
            logger.info(f"🔍 Gemini Vision 분석 시작 (모델: {model_name})")
            start_time = time.time()
            
            # 이미지 데이터 준비
            import base64
            image_data = base64.b64decode(image_base64)
            
            # Gemini Vision 모델 초기화
            model_instance = genai.GenerativeModel(model_name)
            
            # 생성 설정
            generation_config = genai.types.GenerationConfig(
                max_output_tokens=max_tokens,
                temperature=0.1,
                candidate_count=1
            )
            
            # 이미지와 텍스트 함께 분석
            image_part = {
                "mime_type": "image/png",
                "data": image_data
            }
            
            # gRPC 타임아웃 환경변수 설정 (30초로 단축)
            import os
            old_timeout = os.environ.get('GRPC_PYTHON_DEFAULT_TIMEOUT_SECONDS')
            os.environ['GRPC_PYTHON_DEFAULT_TIMEOUT_SECONDS'] = '15'  # 15초로 더 단축
            
            try:
                # 🔥 강력한 타임아웃 추가: asyncio.wait_for 사용
                async def make_request():
                    # 동기 함수를 비동기로 실행
                    loop = asyncio.get_event_loop()
                    return await loop.run_in_executor(
                        None,
                        lambda: model_instance.generate_content(
                            [prompt, image_part],
                            generation_config=generation_config
                        )
                    )
                
                # 20초 타임아웃으로 Vision API 호출 (30초에서 단축)
                response = await asyncio.wait_for(make_request(), timeout=20.0)
                
            except asyncio.TimeoutError:
                logger.error("❌ Gemini Vision API 20초 타임아웃 발생")
                raise Exception("Gemini Vision API 응답 시간이 20초를 초과했습니다. 이미지가 너무 크거나 복잡할 수 있습니다.")
            except Exception as e:
                error_msg = str(e).lower()
                if "deadline" in error_msg or "timeout" in error_msg or "429" in error_msg:
                    logger.error("❌ Gemini Vision API 타임아웃 또는 요청 한도 초과")
                    raise Exception("Gemini Vision API 응답 시간이 초과했거나 요청 한도가 초과되었습니다.")
                elif "quota" in error_msg or "limit" in error_msg:
                    logger.error("❌ Gemini Vision API 할당량 초과") 
                    raise Exception("Gemini Vision API 할당량이 초과되었습니다. 잠시 후 다시 시도해주세요.")
                else:
                    logger.error(f"❌ Gemini Vision API 호출 실패: {str(e)}")
                    raise Exception(f"Gemini Vision API 호출 중 오류가 발생했습니다: {str(e)}")
            finally:
                # 환경변수 복구
                if old_timeout is not None:
                    os.environ['GRPC_PYTHON_DEFAULT_TIMEOUT_SECONDS'] = old_timeout
                else:
                    os.environ.pop('GRPC_PYTHON_DEFAULT_TIMEOUT_SECONDS', None)
            
            response_time = time.time() - start_time
            logger.info(f"✅ Gemini Vision 분석 완료: {response_time:.2f}초")
            
            if not response.candidates or not response.text:
                raise Exception("Gemini Vision API에서 응답을 생성하지 못했습니다.")
            
            content = response.text.strip()
            logger.info(f"🔍 Gemini Vision 응답 길이: {len(content)} 문자")
            logger.debug(f"🔍 응답 시작 부분: {content[:200]}...")
            
            # 토큰 사용량 추정 (try-catch로 보호)
            try:
                input_tokens = self.estimate_tokens(prompt) + 1000  # 이미지 토큰 추정
                output_tokens = self.estimate_tokens(content)
                logger.info(f"🔍 토큰 추정 완료: 입력={input_tokens}, 출력={output_tokens}")
            except Exception as e:
                logger.warning(f"⚠️ 토큰 추정 실패: {e}, 기본값 사용")
                input_tokens = 1000
                output_tokens = min(1000, len(content) // 4)  # 안전한 기본값
            
            # 실제 사용량 정보가 있다면 사용
            try:
                if hasattr(response, 'usage_metadata') and response.usage_metadata:
                    if hasattr(response.usage_metadata, 'prompt_token_count'):
                        input_tokens = response.usage_metadata.prompt_token_count
                    if hasattr(response.usage_metadata, 'candidates_token_count'):
                        output_tokens = response.usage_metadata.candidates_token_count
                    logger.info(f"🔍 실제 토큰 사용량: 입력={input_tokens}, 출력={output_tokens}")
            except Exception as e:
                logger.warning(f"⚠️ usage_metadata 접근 실패: {e}")
            
            # 비용 기록 (try-catch로 보호)
            try:
                self.cost_manager.record_api_call(model_name, input_tokens, output_tokens)
                logger.info(f"🔍 비용 기록 완료")
            except Exception as e:
                logger.warning(f"⚠️ 비용 기록 실패: {e}, 계속 진행")
            
            logger.info(f"✅ Gemini Vision 분석 완료: {response_time:.2f}초, 토큰: {input_tokens}/{output_tokens}")
            
            return {
                "success": True,
                "content": content,
                "metadata": {
                    "model": model_name,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "response_time_ms": int(response_time * 1000),
                    "processed_at": datetime.now().isoformat()
                }
            }
            
        except asyncio.TimeoutError:
            logger.error("❌ Gemini Vision API 타임아웃 (60초 초과)")
            raise Exception("Gemini Vision API 응답 시간이 60초를 초과했습니다.")
        except Exception as e:
            error_msg = str(e)
            if "API_KEY_INVALID" in error_msg:
                logger.error("❌ API 키가 유효하지 않습니다")
                raise Exception("Gemini API 키가 유효하지 않습니다. .env 파일의 GEMINI_API_KEY를 확인해주세요.")
            elif "QUOTA_EXCEEDED" in error_msg:
                logger.error("❌ API 할당량 초과")
                raise Exception("Gemini API 할당량이 초과되었습니다.")
            elif "RATE_LIMIT_EXCEEDED" in error_msg:
                logger.error("❌ API 요청 한도 초과")
                raise Exception("Gemini API 요청 한도가 초과되었습니다. 잠시 후 다시 시도해주세요.")
            else:
                logger.error(f"❌ Gemini Vision 분석 실패: {error_msg}")
                raise Exception(f"이미지 분석 중 오류 발생: {error_msg}")

    def _clean_json_string(self, raw_str: str) -> str:
        """JSON 문자열 정리 헬퍼 함수"""
        content = raw_str.strip()
        
        # JSON 코드 블록에서 추출
        if "```json" in content:
            json_start = content.find("```json") + 7
            json_end = content.find("```", json_start)
            if json_end != -1:
                content = content[json_start:json_end]
        
        # 앞뒤 공백 제거
        content = content.strip()
        
        # 불필요한 텍스트 제거
        lines = content.split('\n')
        json_lines = []
        in_json = False
        
        for line in lines:
            if line.strip().startswith('{') or line.strip().startswith('['):
                in_json = True
            if in_json:
                json_lines.append(line)
            if line.strip().endswith('}') or line.strip().endswith(']'):
                break
        
        return '\n'.join(json_lines)

    def _fix_json_format(self, content: str) -> Optional[str]:
        """JSON 형식 자동 수정 시도"""
        try:
            # 1. 기본 정리
            cleaned = self._clean_json_string(content)
            
            # 2. 흔한 JSON 오류 수정
            fixed = cleaned.replace('```json', '').replace('```', '')
            fixed = fixed.replace('\n', ' ').strip()
            
            # 3. 따옴표 문제 수정
            fixed = fixed.replace("'", '"')
            
            # 4. 끝나지 않은 JSON 객체 수정
            if fixed.count('{') > fixed.count('}'):
                fixed += '}'
            
            return fixed
        except:
            return None

    def merge_extraction_results(self, unstructured_issues: List[Dict], gemini_result: Dict) -> List[Dict]:
        """
        Unstructured 라이브러리와 Gemini의 결과를 통합합니다.
        """
        if not gemini_result.get("success") or not gemini_result.get("data"):
            return unstructured_issues
        
        gemini_issues = gemini_result["data"].get("materiality_issues", [])
        
        # 중복 제거를 위한 통합 로직
        merged_issues = unstructured_issues.copy()
        
        for gemini_issue in gemini_issues:
            # 유사한 이슈가 이미 있는지 확인
            is_duplicate = any(
                self._is_similar_issue(gemini_issue, existing_issue) 
                for existing_issue in merged_issues
            )
            
            if not is_duplicate:
                # Gemini에서 온 이슈라는 것을 표시
                gemini_issue["source"] = "gemini"
                merged_issues.append(gemini_issue)
        
        return merged_issues

    def _is_similar_issue(self, issue1: Dict, issue2: Dict) -> bool:
        """두 이슈가 유사한지 확인 (간단한 텍스트 유사도 기반)"""
        name1 = issue1.get("issue_name", "").lower()
        name2 = issue2.get("issue_name", "").lower()
        
        # 간단한 유사도 계산 (실제로는 더 정교한 알고리즘 사용 가능)
        if len(name1) == 0 or len(name2) == 0:
            return False
        
        # 공통 단어 비율 계산
        words1 = set(name1.split())
        words2 = set(name2.split())
        
        if len(words1) == 0 or len(words2) == 0:
            return False
        
        common_words = words1.intersection(words2)
        similarity = len(common_words) / min(len(words1), len(words2))
        
        return similarity > 0.3  # 30% 이상 유사하면 중복으로 간주 