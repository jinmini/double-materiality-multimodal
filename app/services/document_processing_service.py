# app/services/document_processing_service.py

import logging
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
from fastapi import UploadFile, HTTPException
import time
from pathlib import Path
from datetime import datetime

from app.core.config import settings
from app.infrastructure.clients.cost_manager_client import CostManagerClient
from app.infrastructure.clients.gemini_client import GeminiClient
from app.domain.logic import (
    extract_materiality_issues_enhanced,  # 새로운 개선된 함수
    detect_industry_from_text,
    calculate_overall_confidence
)

# ESGDocumentProcessor 제거 완료 - process_esg.py 삭제됨

logger = logging.getLogger(__name__)

class DocumentProcessingService:
    """문서 처리 워크플로우를 담당하는 서비스 클래스"""
    
    def __init__(self, 
                 cost_manager: CostManagerClient,
                 gemini_client: GeminiClient):
        self.cost_manager = cost_manager
        self.gemini_client = gemini_client
    
    def validate_file(self, file: UploadFile) -> None:
        """업로드된 파일 검증"""
        # 파일 크기 확인
        if file.size and file.size > settings.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"파일 크기가 너무 큽니다. 최대 {settings.MAX_FILE_SIZE/1024/1024:.1f}MB까지 허용됩니다."
            )
        
        # 파일 확장자 확인
        if file.filename:
            extension = file.filename.split('.')[-1].lower()
            if extension not in settings.ALLOWED_EXTENSIONS:
                raise HTTPException(
                    status_code=400,
                    detail=f"지원하지 않는 파일 형식입니다. 허용된 형식: {', '.join(settings.ALLOWED_EXTENSIONS)}"
                )
    
    def check_usage_limit(self) -> None:
        """일일 사용량 제한 확인"""
        can_proceed, message = self.cost_manager.check_limits()
        
        if not can_proceed:
            logger.warning(f"API 사용량 제한: {message}")
            raise HTTPException(status_code=429, detail=message)
        
        logger.info("API 사용량 확인 통과")
    
    async def save_uploaded_file_and_process_with_vision(self, file: UploadFile) -> Dict[str, Any]:
        """
        Vision API용 파일 저장 및 처리 헬퍼 메서드
        """
        logger.info(f"🔍 Vision API 파일 업로드 시작: {file.filename}")
        
        # 1. 사전 검증
        self.validate_file(file)
        self.check_usage_limit()
        
        # 2. 임시 파일 저장
        file_id = str(uuid.uuid4())
        file_extension = file.filename.split('.')[-1].lower()
        temp_filename = f"{file_id}.{file_extension}"
        temp_path = Path(settings.UPLOAD_DIR) / temp_filename
        
        try:
            # 파일 저장
            with open(temp_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            logger.info(f"🔍 파일 저장 완료: {temp_path}")
            
            # 3. Vision API로 문서 처리
            if file_extension == "pdf":
                result = await self.process_document_with_vision(str(temp_path))
                # 파일 정보 업데이트
                result["file_info"]["filename"] = file.filename
                result["file_info"]["file_id"] = file_id
                return result
            else:
                raise HTTPException(
                    status_code=501,
                    detail="Vision API는 현재 PDF 파일만 지원합니다."
                )
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Vision API 처리 중 오류 발생: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Vision API 파일 처리 중 오류가 발생했습니다: {str(e)}"
            )
        finally:
            # 임시 파일 정리
            if temp_path.exists():
                temp_path.unlink()
                logger.info(f"🔍 임시 파일 삭제: {temp_path}")
    
    async def process_uploaded_file(self, file: UploadFile) -> Dict[str, Any]:
        """
        업로드된 파일을 처리하여 중대성 이슈를 추출하는 메인 워크플로우
        
        Args:
            file: 업로드된 파일
            
        Returns:
            처리 결과를 담은 딕셔너리
        """
        logger.info(f"파일 업로드 시작: {file.filename}")
        
        # 1. 사전 검증
        self.validate_file(file)
        self.check_usage_limit()
        
        # 2. 임시 파일 저장
        file_id = str(uuid.uuid4())
        file_extension = file.filename.split('.')[-1].lower()
        temp_filename = f"{file_id}.{file_extension}"
        temp_path = Path(settings.UPLOAD_DIR) / temp_filename
        
        try:
            # 파일 저장
            with open(temp_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            logger.info(f"파일 저장 완료: {temp_path}")
            
            # 3. 문서 처리
            if file_extension == "pdf":
                result = await self.process_document(str(temp_path))
                # 파일 정보 업데이트
                result["file_info"]["filename"] = file.filename
                result["file_info"]["file_id"] = file_id
                return result
            else:
                # 이미지 처리는 추후 구현
                raise HTTPException(
                    status_code=501,
                    detail="이미지 처리 기능은 현재 개발 중입니다. PDF 파일을 사용해주세요."
                )
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"처리 중 오류 발생: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"파일 처리 중 오류가 발생했습니다: {str(e)}"
            )
        finally:
            # 임시 파일 정리
            if temp_path.exists():
                temp_path.unlink()
                logger.info(f"임시 파일 삭제: {temp_path}")
    
    async def process_document(self, file_path: str) -> Dict[str, Any]:
        """
        🚀 개선된 문서 처리 - 새로운 범용 키워드 사전 활용
        """
        logger.info(f"🔵 개선된 문서 처리 시작: {file_path}")
        start_time = time.time()
        
        try:
            # 1차: FAST 전략으로 시도 (가장 빠름)
            logger.info("🔵 1차: FAST 전략으로 처리 시도")
            elements = self._process_pdf_fast(file_path)
            
            if not elements or len(elements) < 3:
                # 2차: 최소한의 OCR으로 시도
                logger.info("🔵 2차: 경량 OCR 전략으로 처리 시도")
                elements = self._process_pdf_lightweight_ocr(file_path)
            
            if not elements:
                raise HTTPException(
                    status_code=422,
                    detail="문서에서 텍스트를 추출할 수 없습니다."
                )
            
            logger.info(f"✅ 총 {len(elements)}개 요소 추출 완료")
            
            # 📊 업종 자동 감지
            full_text = " ".join([str(elem) for elem in elements[:50]])  # 처음 50개 요소로 업종 감지
            detected_industry = detect_industry_from_text(full_text)
            logger.info(f"🏭 감지된 업종: {detected_industry}")
            
            # 문서 구조 분석
            structure = self._analyze_structure_simple(elements)
            
            # ESG 내용 추출
            esg_content = self._extract_esg_simple(elements)
            
            # 🎯 개선된 중대성 이슈 추출 (새로운 범용 키워드 사전 사용)
            materiality_analysis = extract_materiality_issues_enhanced(elements)
            
            processing_time = time.time() - start_time
            logger.info(f"⏱️ 총 처리 시간: {processing_time:.2f}초")
            
            # 📈 개선된 결과 구성
            result = {
                "file_info": {
                    "filename": Path(file_path).name,
                    "file_id": Path(file_path).stem,
                    "processed_at": datetime.now().isoformat(),
                    "processing_time": f"{processing_time:.2f}초"
                },
                "document_analysis": {
                    "total_elements": structure["total_elements"],
                    "page_count": structure["page_count"],
                    "titles_found": len(structure["titles"]),
                    "tables_found": len(structure["tables"])
                },
                "industry_analysis": {
                    "detected_industry": materiality_analysis.get("detected_industry", detected_industry),
                    "confidence": "높음" if materiality_analysis.get("detected_industry", detected_industry) != "기타" else "낮음",
                    "keywords_used": "업종별 특화 키워드" if materiality_analysis.get("detected_industry", detected_industry) != "기타" else "범용 키워드"
                },
                "materiality_issues": materiality_analysis.get("issues", []),
                "extraction_confidence": materiality_analysis.get("overall_confidence", {
                    "level": "중간",
                    "score": 0.5,
                    "details": {}
                }),
                "analysis_summary": {
                    "총_이슈_수": len(materiality_analysis.get("issues", [])),
                    "높은_신뢰도_이슈": len([i for i in materiality_analysis.get("issues", []) if i.get("confidence", 0) >= 0.7]),
                    "환경_이슈": len([i for i in materiality_analysis.get("issues", []) if i.get("category", "").startswith("환경")]),
                    "사회_이슈": len([i for i in materiality_analysis.get("issues", []) if i.get("category", "").startswith("사회")]),
                    "지배구조_이슈": len([i for i in materiality_analysis.get("issues", []) if i.get("category", "").startswith("지배구조")]),
                    "이슈_다양성": materiality_analysis.get("overall_confidence", {}).get("details", {}).get("issue_diversity", 0)
                },
                "esg_content_summary": {
                    category: len(contents) 
                    for category, contents in esg_content.items()
                },
                "extraction_method": "enhanced_universal_keywords",
                "version": "2.0"
            }
            
            return result
            
        except Exception as e:
            logger.error(f"❌ 문서 처리 오류: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"문서 처리 중 오류가 발생했습니다: {str(e)}"
            )
    
    async def process_document_with_vision(self, file_path: str) -> Dict[str, Any]:
        """
        Gemini Vision API 기반 문서 처리 (타임아웃 적용)
        """
        logger.info(f"🔍 Gemini Vision 문서 처리 시작: {file_path}")
        
        try:
            # Gemini Vision 처리기 초기화
            from app.services.gemini_vision_processor import GeminiVisionDocumentProcessor
            from app.infrastructure.clients.pdf_converter import PDFConverter
            import asyncio
            
            pdf_converter = PDFConverter(dpi=200)
            vision_processor = GeminiVisionDocumentProcessor(
                gemini_client=self.gemini_client,
                pdf_converter=pdf_converter
            )
            
            # 전체 처리에 180초 (3분) 타임아웃 적용
            logger.info("🔍 Vision API 처리 시작 (최대 3분 타임아웃)")
            result = await asyncio.wait_for(
                vision_processor.process_document(file_path),
                timeout=180.0
            )
            
            # 비용 기록
            self.cost_manager.record_api_call("gemini_vision", 1, 1000, 0.01)  # 임시 비용
            
            return result
            
        except asyncio.TimeoutError:
            logger.error("❌ Gemini Vision 전체 처리 타임아웃 (3분 초과)")
            raise HTTPException(
                status_code=408,
                detail="문서 처리 시간이 3분을 초과했습니다. 더 작은 파일을 사용하거나 일반 업로드를 시도해주세요."
            )
        except Exception as e:
            logger.error(f"❌ Gemini Vision 처리 오류: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Gemini Vision 처리 중 오류가 발생했습니다: {str(e)}"
            )
    
    def _process_pdf_fast(self, file_path: str) -> List:
        """빠른 PDF 처리 - FAST 전략"""
        try:
            from unstructured.partition.pdf import partition_pdf
            
            elements = partition_pdf(
                filename=file_path,
                strategy="hi_res",  # 고해상도 전략으로 변경
                infer_table_structure=True,  # 테이블 구조 인식 활성화
                include_page_breaks=True,    # 페이지 구분 활성화
                extract_images_in_pdf=False,  # 이미지 추출 비활성화
                languages=["eng"]  # 영어 (한국어 OCR 문제 해결을 위해 변경)
                # languages=["kor"]  # 한국어만 (주석처리)
            )
            
            logger.info(f"🔵 FAST 전략: {len(elements)}개 요소 추출")
            return elements
            
        except Exception as e:
            logger.warning(f"🔵 FAST 전략 실패: {str(e)}")
            return []
    
    def _process_pdf_lightweight_ocr(self, file_path: str) -> List:
        """경량 OCR 처리"""
        try:
            from unstructured.partition.pdf import partition_pdf
            
            elements = partition_pdf(
                filename=file_path,
                strategy="hi_res",  # 고해상도 전략으로 변경
                infer_table_structure=True,  # 테이블 구조 인식 활성화
                include_page_breaks=True,    # 페이지 구분 활성화
                extract_images_in_pdf=False,  # 이미지 추출 비활성화
                languages=["eng"],  # 영어 (한국어 OCR 문제 해결을 위해 변경)
                # languages=["kor"],  # 한국어만 (주석처리)
                max_pages=5  # 최대 5페이지만 처리
            )
            
            logger.info(f"🔵 경량 OCR: {len(elements)}개 요소 추출")
            return elements
            
        except Exception as e:
            logger.warning(f"🔵 경량 OCR 실패: {str(e)}")
            return []
    
    def _analyze_structure_simple(self, elements: List) -> Dict[str, Any]:
        """간단한 문서 구조 분석"""
        structure = {
            "total_elements": len(elements),
            "titles": [],
            "tables": [],
            "page_count": 1
        }
        
        for element in elements:
            # 제목 요소 수집
            if hasattr(element, 'category') and element.category == "Title":
                structure["titles"].append(element.text)
            
            # 테이블 요소 수집
            elif hasattr(element, 'category') and element.category == "Table":
                structure["tables"].append(element.text[:100])
            
            # 페이지 수 계산
            if hasattr(element, 'metadata') and hasattr(element.metadata, 'page_number') and element.metadata.page_number:
                structure["page_count"] = max(structure["page_count"], element.metadata.page_number)
        
        return structure
    
    def _extract_esg_simple(self, elements: List) -> Dict[str, List[str]]:
        """간단한 ESG 키워드 추출"""
        esg_keywords = {
            "환경(E)": ["기후변화", "탄소", "에너지", "환경"],
            "사회(S)": ["안전", "직원", "인권", "지역사회"],
            "지배구조(G)": ["이사회", "지배구조", "윤리", "투명성"],
            "중대성평가": ["중대성", "이슈", "중요도", "이해관계자"]
        }
        
        extracted_content = {category: [] for category in esg_keywords.keys()}
        
        for element in elements:
            element_text = element.text if hasattr(element, 'text') else str(element)
            
            for category, keywords in esg_keywords.items():
                for keyword in keywords:
                    if keyword in element_text:
                        content = element_text[:200]  # 200자로 제한
                        if content not in extracted_content[category]:
                            extracted_content[category].append(content)
                            break  # 첫 번째 키워드 매치 시 중단
        
        return extracted_content
    

    
    def get_usage_summary(self) -> Dict[str, Any]:
        """현재 사용량 및 비용 확인"""
        return self.cost_manager.get_usage_summary()
    
    def reset_daily_usage(self) -> Dict[str, Any]:
        """오늘 사용량 리셋 (개발/테스트용)"""
        self.cost_manager.reset_daily_usage()
        
        return {
            "message": "오늘 사용량이 리셋되었습니다.",
            "timestamp": datetime.now().isoformat()
        }
    
    def get_health_status(self) -> Dict[str, Any]:
        """헬스 체크 정보 반환"""
        usage_info = self.cost_manager.get_usage_summary()
        today_usage = usage_info["today"]
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "daily_usage": today_usage["requests_count"],
            "daily_limit": usage_info["daily_limits"]["requests"],
            "estimated_cost": f"${today_usage['estimated_cost']:.4f}",
            "cost_limit": f"${usage_info['daily_limits']['cost']:.2f}",
            "gemini_available": self.gemini_client.is_available()
        }
