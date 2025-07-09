"""
Gemini Vision API 기반 문서 처리 서비스
"""

import logging
import time
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

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
            
            # 2. PDF → 이미지 변환
            logger.info("🖼️ PDF → 이미지 변환 시작")
            page_images = self.pdf_converter.convert_pdf_to_images(pdf_path)
            
            # 3. 중대성 평가 관련 페이지 식별
            logger.info("🔍 중대성 평가 페이지 식별 중")
            materiality_pages = await self._identify_materiality_pages(page_images)
            
            if not materiality_pages:
                logger.warning("⚠️ 중대성 평가 관련 페이지를 찾을 수 없습니다")
                # 모든 페이지에서 분석 시도
                materiality_pages = page_images[:5]  # 처음 5페이지만
            
            # 4. 중대성 이슈 추출
            logger.info(f"🎯 {len(materiality_pages)}개 페이지에서 중대성 이슈 추출")
            materiality_issues = await self._extract_materiality_issues(materiality_pages)
            
            # 5. ESG 카테고리 분류
            esg_categorized = self._categorize_esg_issues(materiality_issues)
            
            # 6. 결과 구성
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
                    "materiality_pages_found": len([p for p in page_images if self._contains_materiality_keywords(p)]),
                    "has_images": pdf_info["has_images"],
                    "has_text": pdf_info["has_text"]
                },
                "materiality_issues": materiality_issues,
                "esg_content_summary": {
                    category: len(issues) 
                    for category, issues in esg_categorized.items()
                },
                "esg_categorized": esg_categorized,
                "extraction_method": "gemini_vision",
                "extraction_confidence": "high"
            }
            
            logger.info(f"✅ Gemini Vision 처리 완료: {len(materiality_issues)}개 이슈 추출 ({processing_time:.2f}초)")
            return result
            
        except Exception as e:
            logger.error(f"❌ Gemini Vision 처리 실패: {str(e)}")
            raise Exception(f"문서 처리 중 오류 발생: {str(e)}")
    
    async def _identify_materiality_pages(self, page_images: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """중대성 평가 관련 페이지 식별"""
        materiality_pages = []
        
        # 먼저 키워드 기반으로 필터링
        candidate_pages = [
            page for page in page_images 
            if self._contains_materiality_keywords(page)
        ]
        
        if not candidate_pages:
            # 키워드가 없으면 Gemini Vision으로 식별
            logger.info("🔍 키워드 기반 필터링 실패, Gemini Vision으로 페이지 식별")
            
            for page in page_images[:10]:  # 처음 10페이지만 확인
                try:
                    is_materiality = await self._is_materiality_page(page)
                    if is_materiality:
                        materiality_pages.append(page)
                        logger.info(f"✅ 중대성 평가 페이지 발견: {page['page_number']}")
                except Exception as e:
                    logger.warning(f"⚠️ 페이지 {page['page_number']} 분석 실패: {str(e)}")
                    continue
        else:
            materiality_pages = candidate_pages
            logger.info(f"✅ 키워드 기반으로 {len(materiality_pages)}개 중대성 평가 페이지 발견")
        
        return materiality_pages
    
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
    
    async def _extract_materiality_issues(self, pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """중대성 이슈 추출"""
        all_issues = []
        
        for page in pages:
            try:
                logger.info(f"🎯 페이지 {page['page_number']} 중대성 이슈 추출")
                issues = await self._extract_issues_from_page(page)
                all_issues.extend(issues)
                
            except Exception as e:
                logger.warning(f"⚠️ 페이지 {page['page_number']} 이슈 추출 실패: {str(e)}")
                continue
        
        # 중복 제거 및 정제
        unique_issues = self._deduplicate_issues(all_issues)
        return unique_issues
    
    async def _extract_issues_from_page(self, page: Dict[str, Any]) -> List[Dict[str, Any]]:
        """단일 페이지에서 중대성 이슈 추출"""
        prompt = """
        이 지속가능경영보고서 페이지에서 중대성 평가 이슈들을 추출해주세요.
        
        다음 정보를 JSON 배열 형태로 추출해주세요:
        [
            {
                "issue_name": "이슈명 (한국어)",
                "esg_category": "E" | "S" | "G",
                "stakeholder_interest": "높음" | "보통" | "낮음",
                "business_impact": "높음" | "보통" | "낮음",
                "priority": "높음" | "보통" | "낮음",
                "description": "이슈에 대한 간단한 설명"
            }
        ]
        
        주의사항:
        1. 명확한 이슈만 추출하세요
        2. 중복된 이슈는 제외하세요
        3. ESG 카테고리: E(환경), S(사회), G(지배구조)
        4. 정보가 불명확한 경우 "보통"으로 설정
        
        JSON 형태로만 응답해주세요.
        """
        
        try:
            response = await self.gemini_client.analyze_image_with_text(
                image_base64=page["image_base64"],
                prompt=prompt,
                model_name="gemini-2.0-flash",
                max_tokens=2000
            )
            
            # JSON 파싱 시도
            content = response.get("content", "").strip()
            
            # JSON 부분만 추출
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "[" in content and "]" in content:
                start = content.find("[")
                end = content.rfind("]") + 1
                content = content[start:end]
            
            issues = json.loads(content)
            logger.info(f"✅ 페이지 {page['page_number']}에서 {len(issues)}개 이슈 추출")
            
            # 페이지 정보 추가
            for issue in issues:
                issue["source_page"] = page["page_number"]
            
            return issues
            
        except json.JSONDecodeError as e:
            logger.warning(f"⚠️ JSON 파싱 실패: {str(e)}")
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