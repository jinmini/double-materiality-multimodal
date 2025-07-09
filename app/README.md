# ESG 이슈 풀 추출기 API 서버

## 📋 프로젝트 개요

**ESG 지속가능경영보고서에서 중대성 이슈를 자동 추출하는 AI 기반 API 시스템**

- **목표**: 기존 수동 프로세스(PDF → Excel 수기 정리)를 완전 자동화
- **핵심 기능**: PDF 업로드 → 텍스트 추출 → ESG 중대성 이슈 자동 분석
- **기술 스택**: FastAPI + Unstructured + Gemini AI + Tesseract OCR

---

## 🎯 개발 진행 상황

### ✅ **완료된 주요 작업들**

#### 1. **범용 ESG 키워드 사전 구축** (`app/domain/constants.py`)
- **국제 표준 기반**: GRI, SASB, TCFD, K-ESG 통합 키워드 사전
- **업종별 특화**: 전력, 제조, 금융, 건설, IT 등 주요 업종별 맞춤 키워드
- **동적 매칭**: 유사어, 동의어, 영문/한글 혼용 지원

```python
# 예시: 전력 업종 특화 키워드
INDUSTRY_SPECIFIC_KEYWORDS = {
    "전력": {
        "환경": ["발전소 배출", "전력믹스", "재생에너지 비중", "석탄발전"],
        "사회": ["전력공급 안정성", "에너지 접근성", "정전사고"],
        "지배구조": ["전력시장 투명성", "요금 결정 과정"]
    }
}
```

#### 2. **개선된 이슈 추출 로직** (`app/domain/logic.py`)
- **업종 자동 감지**: 문서 내용 분석을 통한 자동 업종 분류
- **이중 중대성 평가**: 비즈니스 영향도 + 이해관계자 관심도
- **신뢰도 기반 순위화**: 키워드 밀도, 맥락 적합성 종합 평가

#### 3. **FastAPI 기반 REST API 구조** (`app/api/v1/`)
- **모듈화된 엔드포인트**: 문서 처리, 헬스체크, 사용량 관리
- **Swagger UI 자동 생성**: `/docs` 경로에서 실시간 API 테스트
- **비동기 처리**: 대용량 파일 처리 최적화

#### 4. **하이브리드 문서 처리 파이프라인** (`app/services/`)
- **1차: Unstructured 라이브러리**: 빠른 텍스트 추출
- **2차: OCR 처리**: 이미지 기반 PDF 대응
- **3차: Gemini Vision API**: 복잡한 레이아웃 처리 (준비중)

---

## 🔄 API 서버 프로세스 플로우

### **1. 파일 업로드 → 검증**
```
POST /api/v1/documents/upload-fast
│
├── 파일 형식 검증 (PDF만 허용)
├── 파일 크기 검증 (최대 10MB)
├── 사용량 제한 확인
└── 임시 파일 저장 (temp_uploads/)
```

### **2. 문서 처리 파이프라인**
```
PDF 입력
│
├── 1차: 고해상도 텍스트 추출 (Unstructured)
│   ├── 성공 → 3단계로 이동
│   └── 실패 → 2차 처리
│
├── 2차: OCR 텍스트 추출 (Tesseract)
│   ├── 성공 → 3단계로 이동
│   └── 실패 → Gemini Vision 대기
│
└── 3차: AI 비전 처리 (Gemini Vision - 향후)
```

### **3. ESG 이슈 분석**
```
추출된 텍스트
│
├── 업종 자동 감지
├── 키워드 매칭 (범용 + 업종별)
├── 중대성 평가 (비즈니스 영향 + 이해관계자)
└── 신뢰도 계산 및 순위화
```

### **4. 결과 반환**
```json
{
  "file_info": {
    "filename": "esg_report.pdf",
    "processed_at": "2025-07-09T17:45:00"
  },
  "materiality_issues": [
    {
      "issue_name": "기후변화 대응",
      "category": "환경(E)",
      "confidence_score": 0.95,
      "business_impact": "high",
      "stakeholder_interest": "high"
    }
  ],
  "extraction_method": "unstructured_only"
}
```

---

## 🧪 API 테스트 현황

### **✅ 성공한 테스트들**
1. **서버 시작**: `http://localhost:8000` 정상 접속
2. **Swagger UI**: `/docs` 페이지 정상 로드
3. **파일 업로드**: PDF 파일 선택 및 전송 성공
4. **API 요청**: 요청이 서버까지 정상 도달

### **❌ 현재 발생 중인 오류**
```
ERROR: 500 Internal Server Error
{
  "detail": "문서 처리 중 오류가 발생했습니다: "
}
```

---

## 🔍 오류 분석 및 해결 방안

### **오류 원인: Tesseract OCR 한국어 언어팩 누락**

#### **상세 오류 로그**
```
2025-07-09 17:47:46,163 - ERROR - ❌ 문서 처리 오류:
Error opening data file C:\Program Files\Tesseract-OCR/tessdata/kor.traineddata
Please make sure the TESSDATA_PREFIX environment variable is set to your "tessdata" directory.
Failed loading language 'kor'
Tesseract couldn't load any languages!
```

#### **발생 위치**
- 파일: `app/services/document_processing_service.py`
- 함수: `_process_pdf_lightweight_ocr()`
- 라인: `languages=["kor"]` 설정 부분

### **🛠️ 해결 방안 (우선순위 순)**

#### **방안 1: 한국어 언어팩 설치 (추천)**
```bash
# 1. 한국어 언어 데이터 다운로드
wget https://github.com/tesseract-ocr/tessdata/raw/main/kor.traineddata

# 2. Tesseract tessdata 폴더에 복사
copy kor.traineddata "C:\Program Files\Tesseract-OCR\tessdata\"

# 3. 환경변수 설정 (PowerShell)
$env:TESSDATA_PREFIX = "C:\Program Files\Tesseract-OCR\tessdata"
```

#### **방안 2: 코드 레벨 임시 해결**
```python
# document_processing_service.py 수정
languages=["eng"]  # 한국어 대신 영어로 임시 변경
```

#### **방안 3: OCR 우회 처리**
```python
# OCR 실패 시 일반 텍스트 추출만 사용
try:
    # OCR 시도
    elements = partition_pdf(languages=["kor"])
except Exception:
    # OCR 실패 시 일반 처리로 폴백
    elements = partition_pdf(strategy="fast")
```

#### **방안 4: Gemini Vision API 활용**
```python
# OCR 완전 실패 시 AI 비전 모델 사용
if not elements:
    # Gemini Vision으로 이미지 분석
    result = await gemini_client.analyze_pdf_images()
```

---

## 📅 다음 작업 계획

### **단기 목표 (1-2일)**
1. **🔥 긴급**: Tesseract 한국어 언어팩 설치 및 환경 설정
2. **✅ 검증**: API 테스트 성공 확인 및 결과 품질 검토
3. **📊 분석**: 실제 ESG 보고서로 정확도 테스트

### **중기 목표 (1주일)**
1. **🤖 Gemini Vision 통합**: 복잡한 레이아웃 PDF 처리
2. **⚡ 성능 최적화**: 대용량 파일 처리 속도 개선
3. **📈 정확도 향상**: 업종별 키워드 확장 및 정교화

### **장기 목표 (1개월)**
1. **🔒 인증 시스템**: JWT 기반 사용자 인증
2. **💾 데이터베이스**: 처리 이력 및 결과 저장
3. **🚀 배포**: Docker 컨테이너화 및 클라우드 배포

---

## 🏗️ 시스템 아키텍처

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   FastAPI       │    │   AI Services   │
│   (Swagger UI)  │───▶│   Server        │───▶│   (Unstructured │
│                 │    │                 │    │    + Gemini)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │   File Storage  │
                       │   (temp_uploads)│
                       └─────────────────┘
```

---

## 💻 개발 환경 설정

### **필수 설치 구성요소**
```bash
# Python 패키지
pip install -r requirements.txt

# Tesseract OCR
# Windows: https://github.com/UB-Mannheim/tesseract/wiki
# 한국어 언어팩 별도 설치 필요

# 환경변수 설정
GEMINI_API_KEY=your_api_key_here
TESSDATA_PREFIX=C:\Program Files\Tesseract-OCR\tessdata
```

### **서버 실행**
```bash
# 개발 서버 시작
python app/run_server.py

# 또는 uvicorn 직접 실행
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### **API 테스트**
- **Swagger UI**: http://localhost:8000/docs
- **헬스체크**: http://localhost:8000/health
- **API 루트**: http://localhost:8000/

---

## 📊 성능 및 제한사항

### **현재 처리 성능**
- **일반 PDF**: ~10-30초 (페이지 수에 따라)
- **OCR 필요 PDF**: ~30-60초
- **파일 크기 제한**: 최대 10MB
- **일일 요청 제한**: 100회

### **알려진 제한사항**
1. **한국어 OCR**: Tesseract 언어팩 설치 필요
2. **복잡한 레이아웃**: 표, 차트 등의 정확도 개선 필요
3. **대용량 파일**: 메모리 사용량 최적화 필요

---

## 🤝 기여 가이드

### **코드 컨벤션**
- **FastAPI 베스트 프랙티스** 준수
- **타입 힌트** 필수 사용
- **비동기 처리** 적극 활용
- **에러 핸들링** 철저히 구현

### **테스트 가이드**
```bash
# 단위 테스트 실행
pytest app/tests/

# API 테스트
python app/test_api.py
```

---

## 📝 변경 이력

### **v1.0.0 (2025-07-09)**
- ✅ 기본 API 서버 구조 완성
- ✅ 범용 ESG 키워드 사전 구축
- ✅ Unstructured 기반 문서 처리
- ✅ 업종별 맞춤 분석 로직
- 🔧 Tesseract OCR 환경 설정 이슈 발견

---

## 📞 문의 및 지원

현재 개발 진행 중인 프로토타입으로, 이슈 발생 시 개발팀에 문의하시기 바랍니다.

**주요 개발 영역:**
- ESG 중대성 이슈 자동 추출
- AI 기반 문서 분석
- API 서버 및 인프라
