"""
PDF를 이미지로 변환하는 유틸리티
"""

import base64
import io
import logging
from pathlib import Path
from typing import List, Tuple, Dict, Any
from PIL import Image
import fitz  # PyMuPDF

logger = logging.getLogger(__name__)

class PDFConverter:
    """PDF를 이미지로 변환하는 클래스"""
    
    def __init__(self, dpi: int = 200):
        """
        Args:
            dpi: 이미지 변환 시 해상도 (기본값: 200)
        """
        self.dpi = dpi
    
    def convert_pdf_to_images(self, pdf_path: str) -> List[Dict[str, Any]]:
        """
        PDF 파일을 페이지별 이미지로 변환
        
        Args:
            pdf_path: PDF 파일 경로
            
        Returns:
            List[Dict]: 각 페이지의 이미지 정보
            [
                {
                    "page_number": 1,
                    "image_base64": "base64_encoded_image",
                    "width": 1200,
                    "height": 1600
                }
            ]
        """
        logger.info(f"🖼️ PDF → 이미지 변환 시작: {pdf_path}")
        
        if not Path(pdf_path).exists():
            raise FileNotFoundError(f"PDF 파일을 찾을 수 없습니다: {pdf_path}")
        
        images = []
        
        try:
            # PyMuPDF로 PDF 열기
            pdf_document = fitz.open(pdf_path)
            total_pages = len(pdf_document)
            
            logger.info(f"🖼️ 총 {total_pages}페이지 변환 시작")
            
            for page_num in range(total_pages):
                page = pdf_document[page_num]
                
                # 이미지로 변환 (DPI 설정)
                mat = fitz.Matrix(self.dpi / 72, self.dpi / 72)
                pix = page.get_pixmap(matrix=mat)
                
                # PIL Image로 변환
                img_data = pix.tobytes("png")
                img = Image.open(io.BytesIO(img_data))
                
                # Base64 인코딩
                img_base64 = self._image_to_base64(img)
                
                page_info = {
                    "page_number": page_num + 1,
                    "image_base64": img_base64,
                    "width": img.width,
                    "height": img.height,
                    "format": "png"
                }
                
                images.append(page_info)
                logger.info(f"🖼️ 페이지 {page_num + 1}/{total_pages} 변환 완료 ({img.width}x{img.height})")
            
            pdf_document.close()
            logger.info(f"✅ PDF → 이미지 변환 완료: {len(images)}페이지")
            
            return images
            
        except Exception as e:
            logger.error(f"❌ PDF 변환 실패: {str(e)}")
            raise Exception(f"PDF 이미지 변환 중 오류 발생: {str(e)}")
    
    def convert_specific_pages(self, pdf_path: str, page_numbers: List[int]) -> List[Dict[str, Any]]:
        """
        특정 페이지만 이미지로 변환
        
        Args:
            pdf_path: PDF 파일 경로
            page_numbers: 변환할 페이지 번호 리스트 (1부터 시작)
            
        Returns:
            List[Dict]: 선택된 페이지의 이미지 정보
        """
        logger.info(f"🖼️ 특정 페이지 변환: {page_numbers}")
        
        if not Path(pdf_path).exists():
            raise FileNotFoundError(f"PDF 파일을 찾을 수 없습니다: {pdf_path}")
        
        images = []
        
        try:
            pdf_document = fitz.open(pdf_path)
            total_pages = len(pdf_document)
            
            for page_num in page_numbers:
                if page_num < 1 or page_num > total_pages:
                    logger.warning(f"⚠️ 잘못된 페이지 번호: {page_num} (총 {total_pages}페이지)")
                    continue
                
                page = pdf_document[page_num - 1]  # 0부터 시작하므로 -1
                
                # 이미지로 변환
                mat = fitz.Matrix(self.dpi / 72, self.dpi / 72)
                pix = page.get_pixmap(matrix=mat)
                
                # PIL Image로 변환
                img_data = pix.tobytes("png")
                img = Image.open(io.BytesIO(img_data))
                
                # Base64 인코딩
                img_base64 = self._image_to_base64(img)
                
                page_info = {
                    "page_number": page_num,
                    "image_base64": img_base64,
                    "width": img.width,
                    "height": img.height,
                    "format": "png"
                }
                
                images.append(page_info)
                logger.info(f"🖼️ 페이지 {page_num} 변환 완료")
            
            pdf_document.close()
            logger.info(f"✅ 특정 페이지 변환 완료: {len(images)}페이지")
            
            return images
            
        except Exception as e:
            logger.error(f"❌ 특정 페이지 변환 실패: {str(e)}")
            raise Exception(f"PDF 특정 페이지 변환 중 오류 발생: {str(e)}")
    
    def _image_to_base64(self, img: Image.Image) -> str:
        """PIL Image를 Base64 문자열로 변환"""
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        img_bytes = buffer.getvalue()
        return base64.b64encode(img_bytes).decode('utf-8')
    
    def get_pdf_info(self, pdf_path: str) -> Dict[str, Any]:
        """
        PDF 파일 정보 조회
        
        Args:
            pdf_path: PDF 파일 경로
            
        Returns:
            Dict: PDF 정보
        """
        if not Path(pdf_path).exists():
            raise FileNotFoundError(f"PDF 파일을 찾을 수 없습니다: {pdf_path}")
        
        try:
            pdf_document = fitz.open(pdf_path)
            
            info = {
                "file_path": pdf_path,
                "file_size": Path(pdf_path).stat().st_size,
                "total_pages": len(pdf_document),
                "metadata": pdf_document.metadata,
                "has_text": any(page.get_text().strip() for page in pdf_document),
                "has_images": any(page.get_images() for page in pdf_document)
            }
            
            pdf_document.close()
            return info
            
        except Exception as e:
            logger.error(f"❌ PDF 정보 조회 실패: {str(e)}")
            raise Exception(f"PDF 정보 조회 중 오류 발생: {str(e)}") 