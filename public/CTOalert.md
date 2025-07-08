안녕하세요! 30년 경력의 CTO 관점에서 이 PRD를 검토하고, 6개월 경험의 신입 개발자가 혼자 구현해야 한다는 점을 고려하여 실질적인 피드백을 드리겠습니다.

## 🚨 **전반적인 우려사항**

이 프로젝트는 **신입 개발자가 혼자 구현하기에는 너무 복잡하고 위험부담이 큽니다.** 특히 OpenAI API 비용, 멀티모달 처리의 복잡성, 비정형 데이터 파싱의 어려움을 고려할 때 실패 가능성이 매우 높습니다.

## 📋 **실질적인 Subtask 분해**

### **Phase 1: MVP (2-3주)**
```python
1. 기본 파일 업로드 API 구축
   - FastAPI 기본 설정
   - 단일 PDF/이미지 업로드 엔드포인트
   - 파일 유효성 검증 (크기, 형식)
   - 로컬 스토리지 임시 저장

2. PDF to Image 변환기
   - pdf2image 라이브러리 활용
   - 페이지별 이미지 추출
   - 해상도 최적화 (API 비용 절감)

3. OpenAI API 연동
   - API 키 환경변수 관리
   - 기본 프롬프트 작성
   - JSON 응답 파싱
   - 에러 핸들링
```

### **Phase 2: 핵심 기능 (3-4주)**
```python
4. 프롬프트 엔지니어링
   - ESG 중대성 평가 특화 프롬프트
   - JSON 스키마 검증
   - 다양한 보고서 형식 대응

5. 하이브리드 파이프라인
   - unstructured.io 기본 구현
   - 실패 시 GPT-4V 폴백
   - 결과 병합 로직

6. 데이터 정제 및 검증
   - 중복 제거
   - 필수 필드 검증
   - 카테고리 표준화
```

### **Phase 3: 안정화 (2-3주)**
```python
7. 에러 처리 및 로깅
   - 상세 에러 메시지
   - 처리 상태 추적
   - 디버깅용 로그

8. 기본 테스트
   - 단위 테스트
   - 통합 테스트
   - 샘플 데이터 테스트
```

## ⚠️ **개발자가 반드시 고려해야 할 문제들**

### **1. API 비용 관리 (가장 중요!)**
```python
# 비용 추정 예시
"""
- GPT-4V API: 이미지당 약 $0.01-0.03
- 하루 100개 처리 시: 약 $1-3
- 월간: $30-90 (최소)
- 실수나 무한루프 시 비용 폭탄 위험!
"""

# 필수 구현 사항
class APIUsageTracker:
    def __init__(self, daily_limit=50):
        self.daily_limit = daily_limit
        self.usage_count = 0
        
    def check_limit(self):
        if self.usage_count >= self.daily_limit:
            raise Exception("일일 API 사용 한도 초과")
```

### **2. 이미지 전처리 최적화**
```python
# 이미지 크기 최적화 (API 비용 절감)
def optimize_image_for_api(image_path):
    img = Image.open(image_path)
    
    # 최대 해상도 제한 (2048x2048)
    max_size = (2048, 2048)
    img.thumbnail(max_size, Image.LANCZOS)
    
    # JPEG 변환 및 압축
    output = io.BytesIO()
    img.convert('RGB').save(output, format='JPEG', quality=85)
    
    return output.getvalue()
```

### **3. 프롬프트 엔지니어링 핵심**
```python
EXTRACTION_PROMPT = """
다음 이미지는 ESG 중대성 평가 페이지입니다.
모든 중대성 이슈를 찾아 아래 JSON 형식으로 추출해주세요.

주의사항:
1. 표의 모든 행을 빠짐없이 확인
2. 시각적 아이콘이나 색상도 해석
3. 우선순위는 위치나 크기로도 판단

JSON 형식:
{
  "issues": [
    {
      "issue_name": "이슈명",
      "category": "E/S/G 중 하나",
      "priority": "높음/중간/낮음",
      "description": "설명 (있는 경우)"
    }
  ]
}

반드시 valid JSON만 반환하세요.
"""
```

### **4. 비정형 데이터 처리의 현실**
```python
# 실제로 마주칠 문제들
common_issues = {
    "merged_cells": "병합된 셀 처리",
    "rotated_text": "회전된 텍스트",
    "icons_only": "텍스트 없이 아이콘만 있는 경우",
    "multi_language": "한글/영문 혼재",
    "low_quality": "스캔 품질이 낮은 PDF"
}

# 폴백 전략
def extract_with_fallback(file_path):
    try:
        # 1차 시도: unstructured
        result = extract_with_unstructured(file_path)
        if validate_result(result):
            return result
    except:
        pass
    
    # 2차 시도: GPT-4V
    return extract_with_gpt4v(file_path)
```

### **5. 메모리 및 파일 관리**
```python
# 임시 파일 자동 정리
import tempfile
import contextlib

@contextlib.contextmanager
def temporary_file_handler(uploaded_file):
    temp_dir = tempfile.mkdtemp()
    try:
        temp_path = os.path.join(temp_dir, uploaded_file.filename)
        with open(temp_path, 'wb') as f:
            f.write(uploaded_file.file.read())
        yield temp_path
    finally:
        # 자동 정리
        shutil.rmtree(temp_dir)
```

## 🎯 **신입 개발자를 위한 현실적인 조언**

### **1. 단계적 접근 필수**
```python
# Week 1-2: 정말 간단한 것부터
async def basic_upload(file: UploadFile):
    """파일 받아서 텍스트만 추출"""
    content = await file.read()
    # PyPDF2로 단순 텍스트 추출
    return {"text": extract_text(content)}

# Week 3-4: OCR 추가
# Week 5-6: GPT API 연동
# Week 7-8: 구조화 및 검증
```

### **2. 비용 관리 체크리스트**
- [ ] API 키는 절대 코드에 하드코딩 X
- [ ] 일일 사용량 제한 구현
- [ ] 각 요청마다 비용 로깅
- [ ] 테스트는 목업 데이터로
- [ ] 프로덕션 전 비용 시뮬레이션

### **3. 에러 처리 템플릿**
```python
class IssueExtractor:
    def __init__(self):
        self.max_retries = 3
        self.timeout = 30
        
    async def extract(self, file_path):
        for attempt in range(self.max_retries):
            try:
                # API 호출
                result = await self._call_api(file_path)
                
                # 검증
                if self._validate_result(result):
                    return result
                else:
                    raise ValueError("Invalid response format")
                    
            except TimeoutError:
                if attempt == self.max_retries - 1:
                    return {"error": "처리 시간 초과", "issues": []}
                await asyncio.sleep(2 ** attempt)  # 지수 백오프
                
            except Exception as e:
                logger.error(f"Attempt {attempt + 1} failed: {str(e)}")
                if attempt == self.max_retries - 1:
                    return {"error": str(e), "issues": []}
```

## 💡 **최종 권고사항**

### **현실적인 MVP 재정의**
1. **Phase 1 (2주)**: PDF 업로드 → 텍스트 추출 → 키워드 기반 이슈 추출
2. **Phase 2 (2주)**: 간단한 표 구조 파싱 추가
3. **Phase 3 (2주)**: GPT API 연동 (텍스트만)
4. **Phase 4 (2주)**: 이미지 처리 추가 (선택사항)

### **필수 멘토링 영역**
- API 비용 관리 및 최적화
- 비동기 프로그래밍 패턴
- 에러 처리 및 복구 전략
- 프롬프트 엔지니어링

### **위험 신호**
```python
# 이런 코드가 보이면 즉시 중단!
while True:
    response = openai.ChatCompletion.create(...)  # 무한 루프 + API 호출
    
# 이렇게 바꿔야 함
for _ in range(MAX_ATTEMPTS):
    if success:
        break
```

**결론**: 이 프로젝트는 신입 개발자 혼자 하기에는 너무 어렵습니다. 최소한 시니어 개발자의 주 1-2회 코드 리뷰와 멘토링이 필요하며, 특히 API 비용 관리 부분은 반드시 경험자의 감독이 필요합니다. 

가능하다면 프로젝트 범위를 대폭 축소하여 "텍스트 기반 추출"부터 시작하고, 멀티모달 AI는 나중에 추가하는 것을 강력히 권장합니다.