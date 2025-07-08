# ESG PDF 문서 처리 및 분석 스크립트
# Unstructured.io를 활용한 지속가능경영보고서 자동 파싱

import os
import json
from pathlib import Path
from typing import List, Dict, Any
from unstructured.partition.pdf import partition_pdf
from unstructured.chunking.title import chunk_by_title
from unstructured.staging.base import elements_to_json
import time

class ESGDocumentProcessor:
    """ESG 문서 처리를 위한 클래스"""
    
    def __init__(self, output_dir: str = "processed_docs"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
    def process_pdf(self, pdf_path: str, use_ocr: bool = False) -> List[Dict]:
        """
        PDF 문서를 처리하여 구조화된 요소들을 추출
        
        Args:
            pdf_path: PDF 파일 경로
            use_ocr: OCR 사용 여부 (기본값: False)
        
        Returns:
            List[Dict]: 추출된 문서 요소들
        """
        print(f"📄 PDF 처리 시작: {pdf_path}")
        start_time = time.time()
        
        try:
            # Unstructured로 PDF 파티셔닝
            elements = partition_pdf(
                filename=pdf_path,
                strategy="fast",  # "fast", "hi_res", "ocr_only" 옵션
                infer_table_structure=True,  # 테이블 구조 인식
                include_page_breaks=True,    # 페이지 구분 포함
                extract_images_in_pdf=False, # 이미지 추출 (용량 절약을 위해 False)
                chunking_strategy="by_title" # 제목별 청킹
            )
            
            print(f"✅ 총 {len(elements)}개 요소 추출 완료")
            print(f"⏱️ 처리 시간: {time.time() - start_time:.2f}초")
            
            return elements
            
        except Exception as e:
            print(f"❌ PDF 처리 중 오류 발생: {str(e)}")
            return []
    
    def analyze_document_structure(self, elements: List) -> Dict[str, Any]:
        """문서 구조 분석"""
        structure = {
            "total_elements": len(elements),
            "element_types": {},
            "titles": [],
            "tables": [],
            "page_count": 0
        }
        
        for element in elements:
            # 요소 타입별 카운트
            element_type = str(type(element).__name__)
            structure["element_types"][element_type] = structure["element_types"].get(element_type, 0) + 1
            
            # 제목 요소 수집
            if hasattr(element, 'category') and element.category == "Title":
                structure["titles"].append(element.text)
            
            # 테이블 요소 수집
            if hasattr(element, 'category') and element.category == "Table":
                structure["tables"].append(element.text[:200] + "..." if len(element.text) > 200 else element.text)
            
            # 페이지 수 계산
            if hasattr(element, 'metadata') and element.metadata.page_number:
                structure["page_count"] = max(structure["page_count"], element.metadata.page_number)
        
        return structure
    
    def extract_esg_keywords(self, elements: List) -> Dict[str, List[str]]:
        """ESG 관련 키워드 및 내용 추출"""
        esg_keywords = {
            "환경(E)": ["온실가스", "탄소배출", "에너지", "재생에너지", "환경경영", "기후변화", "탄소중립"],
            "사회(S)": ["안전", "직원", "다양성", "지역사회", "인권", "고용", "복지", "교육"],
            "지배구조(G)": ["이사회", "윤리", "컴플라이언스", "투명성", "감사", "위험관리", "지배구조"]
        }
        
        extracted_content = {category: [] for category in esg_keywords.keys()}
        
        for element in elements:
            element_text = element.text if hasattr(element, 'text') else str(element)
            
            for category, keywords in esg_keywords.items():
                for keyword in keywords:
                    if keyword in element_text:
                        # 키워드가 포함된 문단 전체 저장 (최대 500자)
                        content = element_text[:500] + "..." if len(element_text) > 500 else element_text
                        if content not in extracted_content[category]:
                            extracted_content[category].append(content)
        
        return extracted_content
    
    def save_results(self, elements: List, structure: Dict, esg_content: Dict, filename: str):
        """결과를 JSON 파일로 저장"""
        
        # 1. 전체 요소를 JSON으로 저장
        elements_json = elements_to_json(elements)
        with open(self.output_dir / f"{filename}_elements.json", "w", encoding="utf-8") as f:
            json.dump(elements_json, f, ensure_ascii=False, indent=2)
        
        # 2. 구조 분석 결과 저장
        with open(self.output_dir / f"{filename}_structure.json", "w", encoding="utf-8") as f:
            json.dump(structure, f, ensure_ascii=False, indent=2)
        
        # 3. ESG 내용 저장
        with open(self.output_dir / f"{filename}_esg_content.json", "w", encoding="utf-8") as f:
            json.dump(esg_content, f, ensure_ascii=False, indent=2)
        
        # 4. 요약 텍스트 파일 저장
        with open(self.output_dir / f"{filename}_summary.txt", "w", encoding="utf-8") as f:
            f.write("=" * 50 + "\n")
            f.write("ESG 문서 처리 결과 요약\n")
            f.write("=" * 50 + "\n\n")
            
            f.write(f"📊 문서 구조:\n")
            f.write(f"- 전체 요소 수: {structure['total_elements']}개\n")
            f.write(f"- 페이지 수: {structure['page_count']}페이지\n")
            f.write(f"- 제목 수: {len(structure['titles'])}개\n")
            f.write(f"- 테이블 수: {len(structure['tables'])}개\n\n")
            
            f.write("📋 요소 타입별 분포:\n")
            for elem_type, count in structure['element_types'].items():
                f.write(f"- {elem_type}: {count}개\n")
            f.write("\n")
            
            f.write("🎯 주요 제목들:\n")
            for i, title in enumerate(structure['titles'][:10], 1):
                f.write(f"{i}. {title}\n")
            f.write("\n")
            
            f.write("🔍 ESG 관련 내용 추출:\n")
            for category, contents in esg_content.items():
                f.write(f"\n[{category}] - {len(contents)}건 발견:\n")
                for i, content in enumerate(contents[:3], 1):  # 상위 3개만 표시
                    f.write(f"{i}. {content[:100]}...\n")
        
        print(f"💾 결과 저장 완료: {self.output_dir}")

def main():
    """메인 실행 함수"""
    print("🚀 ESG PDF 처리기 시작")
    print("=" * 50)
    
    # PDF 파일 경로 설정
    pdf_path = "esg.pdf"  # 실제 파일 경로로 변경하세요
    
    # PDF 파일 존재 확인
    if not os.path.exists(pdf_path):
        print(f"❌ 오류: '{pdf_path}' 파일을 찾을 수 없습니다.")
        print("📝 다음 중 하나를 수행하세요:")
        print("   1. 'esg.pdf' 파일을 현재 디렉토리에 복사")
        print("   2. 아래 코드에서 pdf_path 변수를 실제 파일 경로로 변경")
        return
    
    # 문서 처리기 초기화
    processor = ESGDocumentProcessor()
    
    try:
        # 1. PDF 문서 처리
        elements = processor.process_pdf(pdf_path)
        
        if not elements:
            print("❌ 문서 처리에 실패했습니다.")
            return
        
        # 2. 문서 구조 분석
        print("\n📊 문서 구조 분석 중...")
        structure = processor.analyze_document_structure(elements)
        
        # 3. ESG 내용 추출
        print("🔍 ESG 관련 내용 추출 중...")
        esg_content = processor.extract_esg_keywords(elements)
        
        # 4. 결과 출력
        print("\n" + "=" * 50)
        print("📋 처리 결과")
        print("=" * 50)
        print(f"📄 총 요소 수: {structure['total_elements']}개")
        print(f"📄 페이지 수: {structure['page_count']}페이지")
        print(f"📄 제목 수: {len(structure['titles'])}개")
        print(f"📄 테이블 수: {len(structure['tables'])}개")
        
        print(f"\n📊 요소 타입별 분포:")
        for elem_type, count in structure['element_types'].items():
            print(f"  - {elem_type}: {count}개")
        
        print(f"\n🎯 주요 제목들 (상위 5개):")
        for i, title in enumerate(structure['titles'][:5], 1):
            print(f"  {i}. {title}")
        
        print(f"\n🔍 ESG 관련 내용 발견:")
        for category, contents in esg_content.items():
            print(f"  [{category}]: {len(contents)}건")
        
        # 5. 결과 저장
        filename = Path(pdf_path).stem
        processor.save_results(elements, structure, esg_content, filename)
        
        print(f"\n✅ 모든 처리가 완료되었습니다!")
        print(f"📁 결과 파일들을 '{processor.output_dir}' 폴더에서 확인하세요.")
        
        # 6. Dify용 데이터 준비 안내
        print(f"\n🔄 다음 단계: Dify에 업로드")
        print(f"   - 텍스트 파일: {processor.output_dir}/{filename}_summary.txt")
        print(f"   - 상세 JSON: {processor.output_dir}/{filename}_elements.json")
        
    except Exception as e:
        print(f"❌ 처리 중 오류 발생: {str(e)}")
        print("💡 해결 방법:")
        print("   1. PDF 파일이 손상되지 않았는지 확인")
        print("   2. 텍스트가 포함된 PDF인지 확인 (스캔 이미지가 아닌)")
        print("   3. 필요시 OCR 옵션 활성화")

if __name__ == "__main__":
    main()