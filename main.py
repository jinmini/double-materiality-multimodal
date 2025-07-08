from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import shutil
import logging
from pathlib import Path
from typing import Dict, Any, List
import uuid
from datetime import datetime

from config import settings, ESG_KEYWORDS, MATERIALITY_KEYWORDS
from process_esg import ESGDocumentProcessor
from cost_manager import get_cost_manager, check_api_limits, get_usage_info
from gemini_service import get_gemini_service

# 로깅 설정
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(settings.LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# FastAPI 앱 초기화
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="ESG 지속가능경영보고서에서 중대성 이슈를 자동 추출하는 API",
    debug=settings.DEBUG
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 제한 필요
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def check_usage_limit():
    """일일 사용량 제한 확인 (CTO 조언 - 향상된 비용 관리)"""
    can_proceed, message = check_api_limits()
    
    if not can_proceed:
        logger.warning(f"API 사용량 제한: {message}")
        raise HTTPException(status_code=429, detail=message)
    
    logger.info("API 사용량 확인 통과")

def validate_file(file: UploadFile) -> None:
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

@app.get("/")
async def root():
    """API 기본 정보"""
    return {
        "message": f"{settings.APP_NAME} API",
        "version": settings.APP_VERSION,
        "endpoints": {
            "upload": "/upload",
            "health": "/health",
            "usage": "/usage"
        }
    }

@app.get("/health")
async def health_check():
    """헬스 체크"""
    usage_info = get_usage_info()
    today_usage = usage_info["today"]
    
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "daily_usage": today_usage["requests_count"],
        "daily_limit": usage_info["daily_limits"]["requests"],
        "estimated_cost": f"${today_usage['estimated_cost']:.4f}",
        "cost_limit": f"${usage_info['daily_limits']['cost']:.2f}"
    }

@app.get("/usage")
async def get_usage_endpoint():
    """현재 사용량 및 비용 확인 (상세 정보)"""
    return get_usage_info()

@app.post("/usage/reset")
async def reset_usage():
    """오늘 사용량 리셋 (개발/테스트용)"""
    cost_manager = get_cost_manager()
    cost_manager.reset_daily_usage()
    
    return {
        "message": "오늘 사용량이 리셋되었습니다.",
        "timestamp": datetime.now().isoformat()
    }

@app.post("/upload")
async def upload_and_process(
    file: UploadFile = File(...),
    _: None = Depends(check_usage_limit)
):
    """
    ESG 문서 업로드 및 이슈 추출
    
    - **file**: PDF 또는 이미지 파일 (PNG, JPG)
    - 중대성 평가 관련 페이지만 업로드하세요
    """
    logger.info(f"파일 업로드 시작: {file.filename}")
    
    # 파일 검증
    validate_file(file)
    
    # 임시 파일 경로 생성
    file_id = str(uuid.uuid4())
    file_extension = file.filename.split('.')[-1].lower()
    temp_filename = f"{file_id}.{file_extension}"
    temp_path = Path(settings.UPLOAD_DIR) / temp_filename
    
    try:
        # 파일 저장
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        logger.info(f"파일 저장 완료: {temp_path}")
        
        # ESG 문서 처리기 초기화
        processor = ESGDocumentProcessor(output_dir=settings.OUTPUT_DIR)
        
        # PDF 처리 (이미지는 향후 확장)
        if file_extension == "pdf":
            elements = processor.process_pdf(str(temp_path))
            
            if not elements:
                raise HTTPException(
                    status_code=422,
                    detail="PDF에서 내용을 추출할 수 없습니다. 파일이 손상되었거나 텍스트가 없을 수 있습니다."
                )
            
            # 문서 구조 분석
            structure = processor.analyze_document_structure(elements)
            
            # ESG 내용 추출
            esg_content = processor.extract_esg_keywords(elements)
            
            # 1차: Unstructured 기반 중대성 이슈 추출
            unstructured_issues = extract_materiality_issues(elements)
            
            # 2차: Gemini AI 기반 텍스트 분석 (선택적)
            gemini_service = get_gemini_service()
            gemini_result = {"success": False}
            
            if gemini_service.is_available() and len(unstructured_issues) < 5:
                # unstructured 결과가 부족한 경우에만 Gemini 활용
                full_text = "\n".join([el.text for el in elements if hasattr(el, 'text')])
                logger.info("Gemini API를 사용한 추가 분석 시작")
                
                success, gemini_result = await gemini_service.extract_issues_from_text(full_text[:5000])
                if not success:
                    logger.warning(f"Gemini 분석 실패: {gemini_result.get('error', '알 수 없는 오류')}")
            
            # 결과 병합
            if gemini_result.get("success"):
                final_issues = gemini_service.merge_extraction_results(unstructured_issues, gemini_result)
                extraction_method = "hybrid"
            else:
                final_issues = unstructured_issues
                extraction_method = "unstructured_only"
            
            # 결과 반환
            result = {
                "file_info": {
                    "filename": file.filename,
                    "file_id": file_id,
                    "processed_at": datetime.now().isoformat()
                },
                "document_analysis": {
                    "total_elements": structure["total_elements"],
                    "page_count": structure["page_count"],
                    "titles_found": len(structure["titles"]),
                    "tables_found": len(structure["tables"])
                },
                "materiality_issues": final_issues,
                "esg_content_summary": {
                    category: len(contents) 
                    for category, contents in esg_content.items()
                },
                "extraction_method": extraction_method,
                "extraction_confidence": calculate_confidence(final_issues, structure),
                "gemini_metadata": gemini_result.get("metadata") if gemini_result.get("success") else None
            }
            
            # 처리 완료 후 사용량 기록 (현재는 unstructured 처리만)
            cost_manager = get_cost_manager()
            # unstructured 처리는 무료이므로 0 비용으로 기록 (요청 횟수만 추적)
            cost_manager.record_api_call("unstructured", 0, 0, 0.0)
            
            logger.info(f"처리 완료: {len(final_issues)}개 이슈 추출 ({extraction_method})")
            return JSONResponse(content=result)
            
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

def extract_materiality_issues(elements: List) -> List[Dict[str, Any]]:
    """중대성 이슈 추출 핵심 로직"""
    issues = []
    
    for element in elements:
        element_text = element.text if hasattr(element, 'text') else str(element)
        
        # 중대성 관련 키워드가 포함된 요소만 필터링
        if any(keyword in element_text for keyword in MATERIALITY_KEYWORDS):
            
            # ESG 카테고리 분류
            category = "기타"
            for esg_category, keywords in ESG_KEYWORDS.items():
                if any(keyword in element_text for keyword in keywords):
                    category = esg_category
                    break
            
            # 이슈 객체 생성
            issue = {
                "issue_id": len(issues) + 1,
                "category": category,
                "content": element_text[:500],  # 최대 500자
                "page_number": getattr(element.metadata, 'page_number', None) if hasattr(element, 'metadata') else None,
                "element_type": str(type(element).__name__),
                "confidence": calculate_issue_confidence(element_text)
            }
            
            issues.append(issue)
    
    # 신뢰도 순으로 정렬
    issues.sort(key=lambda x: x["confidence"], reverse=True)
    
    return issues[:20]  # 상위 20개만 반환

def calculate_issue_confidence(text: str) -> float:
    """이슈 추출 신뢰도 계산"""
    confidence = 0.0
    
    # 중대성 키워드 가중치
    for keyword in MATERIALITY_KEYWORDS:
        if keyword in text:
            confidence += 0.2
    
    # ESG 키워드 가중치
    for keywords in ESG_KEYWORDS.values():
        for keyword in keywords:
            if keyword in text:
                confidence += 0.1
    
    # 테이블이면 가중치 추가
    if any(indicator in text for indicator in ["│", "─", "┌", "└", "┐", "┘"]):
        confidence += 0.3
    
    return min(confidence, 1.0)  # 최대 1.0

def calculate_confidence(issues: List[Dict], structure: Dict) -> Dict[str, Any]:
    """전체 추출 신뢰도 계산"""
    if not issues:
        return {"score": 0.0, "level": "낮음", "reason": "이슈를 찾을 수 없음"}
    
    avg_confidence = sum(issue["confidence"] for issue in issues) / len(issues)
    
    # 테이블 존재 여부도 고려
    has_tables = structure.get("tables", [])
    if has_tables:
        avg_confidence += 0.2
    
    avg_confidence = min(avg_confidence, 1.0)
    
    if avg_confidence >= 0.8:
        level = "높음"
    elif avg_confidence >= 0.5:
        level = "중간"
    else:
        level = "낮음"
    
    return {
        "score": round(avg_confidence, 2),
        "level": level,
        "issues_found": len(issues),
        "has_tables": bool(has_tables)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level=settings.LOG_LEVEL.lower()
    ) 