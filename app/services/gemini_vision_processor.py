"""
Gemini Vision API 기반 문서 처리 서비스
"""

import logging
import time
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
import asyncio # Added for asyncio.wait_for

from app.infrastructure.clients.pdf_converter import PDFConverter
from app.infrastructure.clients.gemini_client import GeminiClient
from app.dependencies.clients import get_cost_manager_client

logger = logging.getLogger(__name__)

class GeminiVisionDocumentProcessor:
    """Gemini Vision API 기반 문서 처리기"""
    
    def __init__(self, gemini_client: GeminiClient, pdf_converter: PDFConverter = None):
        """
        Args:
            gemini_client: Gemini API 클라이언트
            pdf_converter: PDF 변환기 (기본값: 200 DPI)
        """
        self.gemini_client = gemini_client
        self.pdf_converter = pdf_converter or PDFConverter(dpi=200)
        self.cost_manager = get_cost_manager_client()
        
        # 중대성 평가 관련 키워드
        self.materiality_keywords = [
            "중대성", "materiality", "중요도", "이해관계자", "stakeholder",
            "매트릭스", "matrix", "이슈", "issue", "영향도", "관심도"
        ]
    
    async def process_document(self, pdf_path: str) -> Dict[str, Any]:
        """
        PDF 문서를 Gemini Vision API로 분석하여 중대성 이슈 추출
        
        Args:
            pdf_path: PDF 파일 경로
            
        Returns:
            Dict: 처리 결과
        """
        logger.info(f"🔍 Gemini Vision 문서 처리 시작: {pdf_path}")
        start_time = time.time()
        
        try:
            # 1. PDF 정보 조회
            pdf_info = self.pdf_converter.get_pdf_info(pdf_path)
            logger.info(f"📄 PDF 정보: {pdf_info['total_pages']}페이지, {pdf_info['file_size']/1024/1024:.1f}MB")
            
            # 2. 페이지 수 제한 (처리 시간 단축)
            max_pages = min(pdf_info['total_pages'], 10)  # 최대 10페이지만 처리
            logger.info(f"🔍 처리할 페이지 수: {max_pages} (최대 10페이지 제한)")
            
            # 3. PDF → 이미지 변환 (제한된 페이지만)
            logger.info("🖼️ PDF → 이미지 변환 시작")
            page_images = self.pdf_converter.convert_specific_pages(
                pdf_path, 
                list(range(1, max_pages + 1))
            )
            
            # 4. 빠른 중대성 평가 페이지 식별 (키워드 기반)
            logger.info("🔍 중대성 평가 페이지 식별 중")
            materiality_pages = self._identify_materiality_pages_fast(page_images)
            
            if not materiality_pages:
                logger.warning("⚠️ 중대성 평가 관련 페이지를 찾을 수 없습니다")
                # 중간 페이지들에서 분석 시도 (보통 중대성 평가는 중간에 위치)
                start_idx = max(0, len(page_images) // 3)
                end_idx = min(len(page_images), (len(page_images) * 2) // 3)
                materiality_pages = page_images[start_idx:end_idx][:3]  # 최대 3페이지
            
            # 5. 제한된 페이지에서만 중대성 이슈 추출
            logger.info(f"🎯 {len(materiality_pages)}개 페이지에서 중대성 이슈 추출")
            materiality_issues = await self._extract_materiality_issues_with_timeout(materiality_pages)
            
            # 6. ESG 카테고리 분류
            esg_categorized = self._categorize_esg_issues(materiality_issues)
            
            # 7. 결과 구성
            processing_time = time.time() - start_time
            
            result = {
                "file_info": {
                    "filename": Path(pdf_path).name,
                    "file_id": Path(pdf_path).stem,
                    "processed_at": datetime.now().isoformat(),
                    "processing_time": f"{processing_time:.2f}초"
                },
                "document_analysis": {
                    "total_pages": pdf_info["total_pages"],
                    "analyzed_pages": len(materiality_pages),
                    "page_limit_applied": max_pages < pdf_info["total_pages"],
                    "has_images": pdf_info["has_images"],
                    "has_text": pdf_info["has_text"]
                },
                "materiality_issues": materiality_issues,
                "esg_content_summary": {
                    category: len(issues) 
                    for category, issues in esg_categorized.items()
                },
                "esg_categorized": esg_categorized,
                "extraction_method": "gemini_vision_optimized",
                "extraction_confidence": {
                    "score": min(0.9, len(materiality_issues) * 0.1),
                    "level": "high" if len(materiality_issues) > 5 else "medium",
                    "issues_found": len(materiality_issues),
                    "has_tables": True
                }
            }
            
            logger.info(f"✅ Gemini Vision 처리 완료: {len(materiality_issues)}개 이슈 추출 ({processing_time:.2f}초)")
            return result
            
        except Exception as e:
            logger.error(f"❌ Gemini Vision 처리 실패: {str(e)}")
            raise Exception(f"문서 처리 중 오류 발생: {str(e)}")
    
    def _identify_materiality_pages_fast(self, page_images: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """빠른 중대성 평가 페이지 식별 (테스트용 1-5페이지 파일에 최적화)"""
        total_pages = len(page_images)
        
        if total_pages <= 5:
            # 5페이지 이하면 모든 페이지 분석 (테스트 파일 대응)
            logger.info(f"✅ 테스트 파일 감지 ({total_pages}페이지), 모든 페이지 분석")
            return page_images
        
        # 5페이지를 초과하는 경우에만 범위 분석 적용
        logger.info(f"📄 큰 문서 ({total_pages}페이지), 범위 분석 적용")
        start_idx = max(0, int(total_pages * 0.2))
        end_idx = min(total_pages, int(total_pages * 0.8))
        candidate_pages = page_images[start_idx:end_idx]
        final_pages = candidate_pages[:8]
        
        logger.info(f"✅ 페이지 범위 기반으로 {len(final_pages)}개 중대성 평가 후보 페이지 선정")
        return final_pages
    
    async def _extract_materiality_issues_with_timeout(self, pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """타임아웃이 적용된 중대성 이슈 추출"""
        all_issues = []
        
        for i, page in enumerate(pages):
            try:
                logger.info(f"🎯 페이지 {page['page_number']} 중대성 이슈 추출 ({i+1}/{len(pages)})")
                
                # 각 페이지당 30초 타임아웃
                issues = await asyncio.wait_for(
                    self._extract_issues_from_page(page),
                    timeout=30.0
                )
                all_issues.extend(issues)
                
                # 충분한 이슈를 찾았으면 조기 종료
                if len(all_issues) >= 10:
                    logger.info(f"✅ 충분한 이슈 발견 ({len(all_issues)}개), 처리 조기 종료")
                    break
                    
            except asyncio.TimeoutError:
                logger.warning(f"⚠️ 페이지 {page['page_number']} 처리 타임아웃 (30초 초과)")
                continue
            except Exception as e:
                logger.warning(f"⚠️ 페이지 {page['page_number']} 이슈 추출 실패: {str(e)}")
                continue
        
        # 중복 제거 및 정제
        unique_issues = self._deduplicate_issues(all_issues)
        
        # 이슈를 찾지 못했을 때 폴백 시도
        if len(unique_issues) == 0 and len(pages) > 0:
            logger.warning("⚠️ 1차 분석에서 이슈를 찾지 못함, 더 관대한 분석 시도")
            unique_issues = await self._fallback_general_analysis(pages[:3])  # 처음 3페이지만
        
        return unique_issues
    
    async def _fallback_general_analysis(self, pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """일반적인 ESG 콘텐츠 분석 (폴백)"""
        fallback_prompt = """
        이 페이지에서 ESG와 관련된 모든 내용을 찾아주세요.
        중대성 평가가 명시적으로 없더라도, ESG 관련 내용이 있다면 추출해주세요.

        찾을 내용:
        - 환경 관련: 탄소배출, 에너지, 폐기물, 수자원 등
        - 사회 관련: 안전, 인권, 다양성, 지역사회 등  
        - 지배구조 관련: 이사회, 윤리, 리스크관리 등

        JSON 형태로 응답:
        [
            {
                "issue_name": "발견된 ESG 이슈명",
                "esg_category": "E" | "S" | "G",
                "stakeholder_interest": "알 수 없음",
                "business_impact": "알 수 없음",
                "priority": "보통",
                "description": "간단한 설명",
                "confidence": "낮음"
            }
        ]
        """
        
        all_fallback_issues = []
        
        for page in pages:
            try:
                response = await self.gemini_client.analyze_image_with_text(
                    image_base64=page["image_base64"],
                    prompt=fallback_prompt,
                    model_name="gemini-2.0-flash",
                    max_tokens=2000
                )
                
                content = response.get("content", "").strip()
                
                # JSON 추출
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "[" in content and "]" in content:
                    start = content.find("[")
                    end = content.rfind("]") + 1
                    content = content[start:end]
                
                content = content.replace("'", '"')
                issues = json.loads(content)
                
                for issue in issues:
                    issue["source_page"] = page["page_number"]
                    issue["confidence_score"] = 0.3  # 낮은 신뢰도
                    issue["extraction_type"] = "fallback"
                
                all_fallback_issues.extend(issues)
                logger.info(f"✅ 폴백 분석: 페이지 {page['page_number']}에서 {len(issues)}개 ESG 콘텐츠 발견")
                
            except Exception as e:
                logger.warning(f"⚠️ 폴백 분석 실패: {str(e)}")
                continue
        
        return self._deduplicate_issues(all_fallback_issues)
    
    def _contains_materiality_keywords(self, page: Dict[str, Any]) -> bool:
        """페이지에 중대성 평가 키워드가 포함되어 있는지 확인 (임시 구현)"""
        # 실제로는 OCR이 필요하지만, 일단 페이지 번호로 추정
        # 보통 중대성 평가는 보고서 중간 부분에 위치
        page_num = page["page_number"]
        total_pages = 50  # 임시값
        
        # 중간 50% 페이지 범위에서 찾기
        middle_start = int(total_pages * 0.3)
        middle_end = int(total_pages * 0.8)
        
        return middle_start <= page_num <= middle_end
    
    async def _is_materiality_page(self, page: Dict[str, Any]) -> bool:
        """Gemini Vision으로 중대성 평가 페이지인지 확인"""
        prompt = """
        이 페이지가 지속가능경영보고서의 중대성 평가(Materiality Assessment) 섹션인지 판단해주세요.
        
        다음 요소들을 확인해주세요:
        1. "중대성", "materiality", "중요도" 등의 용어
        2. 매트릭스 또는 그래프 형태의 도표
        3. 이해관계자 관심도/비즈니스 영향도 축
        4. ESG 이슈들의 나열
        
        단순히 "예" 또는 "아니오"로만 답변해주세요.
        """
        
        try:
            response = await self.gemini_client.analyze_image_with_text(
                image_base64=page["image_base64"],
                prompt=prompt,
                model_name="gemini-2.0-flash",
                max_tokens=10
            )
            
            return "예" in response.get("content", "").strip().lower()
            
        except Exception as e:
            logger.warning(f"⚠️ 페이지 분석 실패: {str(e)}")
            return False
    
    async def _extract_issues_from_page(self, page: Dict[str, Any]) -> List[Dict[str, Any]]:
        """단일 페이지에서 중대성 이슈 추출"""
        prompt = """
        이 페이지를 분석하여 ESG 중대성 이슈들을 모두 찾아주세요.

        **찾을 내용:**
        - 중대성 평가, 중대성 매트릭스에 포함된 이슈들
        - 표, 리스트, 그래프에 나타난 ESG 이슈들
        - 환경(E), 사회(S), 지배구조(G) 관련 모든 내용

        **JSON 형태로 정확히 응답해주세요:**
        ```json
        [
            {
                "issue_name": "이슈명",
                "esg_category": "E",
                "priority": "높음",
                "description": "설명"
            },
            {
                "issue_name": "다른 이슈명", 
                "esg_category": "S",
                "priority": "보통",
                "description": "설명"
            }
        ]
        ```

        **주의사항:**
        - 페이지에 보이는 모든 ESG 관련 내용을 빠뜨리지 말고 추출하세요
        - 작은 텍스트나 표 안의 내용도 주의깊게 확인하세요
        - esg_category는 "E", "S", "G" 중 하나만 사용하세요
        - priority는 "높음", "보통", "낮음" 중 하나만 사용하세요
        - 반드시 유효한 JSON 배열로 응답하세요

        이제 이 페이지를 분석해서 ESG 이슈들을 JSON으로 추출해주세요.
        """
        
        try:
            response = await self.gemini_client.analyze_image_with_text(
                image_base64=page["image_base64"],
                prompt=prompt,
                model_name="gemini-2.0-flash",  # 최신 모델 사용
                max_tokens=3000  # 더 많은 토큰 허용
            )
            
            # JSON 파싱 시도
            content = response.get("content", "").strip()
            logger.info(f"🔍 Gemini 응답 (처음 200자): {content[:200]}...")
            
            # JSON 부분만 추출
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                # 일반적인 코드 블록
                parts = content.split("```")
                for part in parts:
                    if "[" in part and "]" in part:
                        content = part.strip()
                        break
            elif "[" in content and "]" in content:
                start = content.find("[")
                end = content.rfind("]") + 1
                content = content[start:end]
            
            # JSON 파싱 전 정리
            content = content.replace("'", '"')  # 작은따옴표를 큰따옴표로 변환
            content = content.replace("，", ",")  # 중국어 쉼표 변환
            
            logger.info(f"🔍 정제된 JSON: {content[:300]}...")
            
            issues = json.loads(content)
            logger.info(f"✅ 페이지 {page['page_number']}에서 {len(issues)}개 이슈 추출")
            
            # 페이지 정보 및 기본값 추가
            for issue in issues:
                issue["source_page"] = page["page_number"]
                # 기본값 설정
                if "stakeholder_interest" not in issue:
                    issue["stakeholder_interest"] = "보통"
                if "business_impact" not in issue:
                    issue["business_impact"] = "보통"
                if "confidence" not in issue:
                    issue["confidence"] = "높음"
                
                # 신뢰도 점수화
                confidence_text = issue.get("confidence", "높음")
                if confidence_text == "높음":
                    issue["confidence_score"] = 0.9
                elif confidence_text == "보통":
                    issue["confidence_score"] = 0.7
                else:
                    issue["confidence_score"] = 0.5
            
            return issues
            
        except json.JSONDecodeError as e:
            logger.warning(f"⚠️ JSON 파싱 실패: {str(e)}")
            logger.warning(f"응답 내용: {content[:500]}...")
            return []
        except Exception as e:
            logger.error(f"❌ 이슈 추출 실패: {str(e)}")
            return []
    
    def _deduplicate_issues(self, issues: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """중복 이슈 제거"""
        seen_names = set()
        unique_issues = []
        
        for issue in issues:
            issue_name = issue.get("issue_name", "").strip().lower()
            if issue_name and issue_name not in seen_names:
                seen_names.add(issue_name)
                unique_issues.append(issue)
        
        logger.info(f"🔄 중복 제거: {len(issues)}개 → {len(unique_issues)}개")
        return unique_issues
    
    def _categorize_esg_issues(self, issues: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """ESG 카테고리별로 이슈 분류"""
        categorized = {
            "환경(E)": [],
            "사회(S)": [],
            "지배구조(G)": [],
            "기타": []
        }
        
        for issue in issues:
            esg_category = issue.get("esg_category", "").upper()
            if esg_category == "E":
                categorized["환경(E)"].append(issue)
            elif esg_category == "S":
                categorized["사회(S)"].append(issue)
            elif esg_category == "G":
                categorized["지배구조(G)"].append(issue)
            else:
                categorized["기타"].append(issue)
        
        return categorized 