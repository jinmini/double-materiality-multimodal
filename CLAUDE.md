# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an **ESG Materiality Issues Extraction API** service that automatically extracts ESG (Environmental, Social, Governance) materiality issues from Korean sustainability reports. The system processes PDF documents using AI-powered text extraction and analysis.

**Key Technologies:**
- FastAPI (async web framework)
- Unstructured (document processing)
- Tesseract OCR (optical character recognition)
- Google Gemini AI (text analysis)
- Pydantic (data validation)

## Common Development Commands

### Server Operations
```bash
# Start development server
python app/run_server.py

# Alternative with uvicorn directly
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# View API documentation
# http://localhost:8000/docs (Swagger UI)
# http://localhost:8000/health (Health check)
```

### Testing
```bash
# Run unit tests
pytest app/tests/

# Run API integration tests
python app/test_api.py

# Manual API testing available at /docs endpoint
```

### Environment Setup
```bash
# Install dependencies
pip install -r app/requirements.txt

# Set up environment variables (copy from app/env_example.txt)
# Required: GEMINI_API_KEY, TESSDATA_PREFIX (for Korean OCR)
```

## Architecture Overview

The application follows a **Clean Architecture** pattern with clear separation of concerns:

### Directory Structure
```
app/
├── api/v1/               # FastAPI routes and endpoints
│   ├── endpoints/        # Individual endpoint modules
│   └── api.py           # Router configuration
├── core/                # Application core (config, logging)
├── domain/              # Business logic and constants
│   ├── constants.py     # ESG keyword dictionary
│   └── logic.py         # Core business logic
├── infrastructure/      # External service clients
│   └── clients/         # Gemini, PDF converter, cost manager
├── services/           # Application services
├── dependencies/       # Dependency injection
└── schemas/           # Pydantic models
```

### Key Components

**1. ESG Keyword Dictionary (`app/domain/constants.py`)**
- Comprehensive ESG keyword mapping based on GRI, SASB, TCFD, K-ESG standards
- Industry-specific keyword variants (power, manufacturing, finance, etc.)
- Automatic industry detection capabilities
- Materiality assessment keywords

**2. Document Processing Pipeline (`app/services/document_processing_service.py`)**
- Multi-tier processing strategy:
  1. Fast text extraction (Unstructured library)
  2. OCR fallback (Tesseract + Korean language pack)
  3. AI vision processing (Gemini Vision API - future)
- Hybrid approach for handling various PDF formats

**3. Business Logic (`app/domain/logic.py`)**
- Industry auto-detection from document content
- Dynamic keyword matching based on detected industry
- Enhanced confidence scoring with multiple factors
- Industry-specific priority weighting

**4. API Layer (`app/api/v1/`)**
- RESTful endpoints for document processing
- File upload with validation and size limits
- Usage tracking and rate limiting
- Health monitoring endpoints

## Development Guidelines

### Code Standards
- Follow FastAPI best practices from `.cursor/rules/fastapi.mdc`
- Use async/await for I/O operations
- Implement proper error handling with HTTP status codes
- Use Pydantic models for data validation
- Include comprehensive type hints

### Key Design Patterns
- **Dependency Injection**: Services are injected via `app/dependencies/`
- **Repository Pattern**: Data access abstracted through clients
- **Clean Architecture**: Domain logic isolated from infrastructure
- **Strategy Pattern**: Multiple document processing strategies

### Known Technical Constraints

**OCR Requirements:**
- Tesseract OCR with Korean language pack (`kor.traineddata`) required
- Set `TESSDATA_PREFIX` environment variable to tessdata directory
- Common path: `C:\Program Files\Tesseract-OCR\tessdata` (Windows)

**File Processing Limits:**
- Maximum file size: 50MB (configurable in `settings.MAX_FILE_SIZE`)
- Supported formats: PDF, PNG, JPG, JPEG
- Daily API limits: 20 requests, $5.00 cost limit

**API Rate Limits:**
- 5 requests per minute
- Usage tracking via `CostManagerClient`
- Automatic limit enforcement in endpoints

### Configuration Management

**Environment Variables:**
- `GEMINI_API_KEY`: Required for AI text analysis
- `TESSDATA_PREFIX`: Path to Tesseract language data
- `DEBUG`: Enable detailed logging (default: True)
- `LOG_LEVEL`: Logging verbosity (default: DEBUG)

**Key Settings (`app/core/config.py`):**
- File upload limits and allowed extensions
- API rate limits and cost thresholds
- Gemini model configuration
- Directory paths for uploads and processing

### Common Development Tasks

**Adding New ESG Keywords:**
1. Update `UNIVERSAL_ESG_ISSUES` in `app/domain/constants.py`
2. Add industry-specific variants if needed
3. Test with sample documents

**Extending Document Processing:**
1. Add new strategy methods to `DocumentProcessingService`
2. Update processing pipeline in `process_document()` method
3. Consider fallback chain for robustness

**Adding New Endpoints:**
1. Create endpoint module in `app/api/v1/endpoints/`
2. Add router to `app/api/v1/api.py`
3. Include proper error handling and validation

### Testing Strategy

**Unit Tests:**
- Test business logic in `app/domain/logic.py`
- Mock external dependencies (Gemini API, file system)
- Focus on ESG keyword matching and confidence scoring

**Integration Tests:**
- Test complete document processing pipeline
- Verify API endpoints with sample PDF files
- Test error handling and edge cases

**Manual Testing:**
- Use Swagger UI at `/docs` for interactive testing
- Test with various PDF formats and layouts
- Verify Korean OCR functionality

## Current Known Issues

1. **OCR Configuration**: Tesseract Korean language pack setup required
2. **Large File Processing**: Memory usage optimization needed for large PDFs
3. **Complex Layouts**: Table and chart extraction accuracy improvements needed
4. **Rate Limiting**: Current implementation is basic, consider Redis for production

## Future Development Areas

1. **Gemini Vision Integration**: Complete implementation for complex document layouts
2. **Database Integration**: Add persistence for processing history
3. **Authentication**: Implement JWT-based user authentication
4. **Containerization**: Docker setup for deployment
5. **Performance Optimization**: Async processing for large documents

## Recent Development Log

### 2025-07-10: Tesseract OCR Language Configuration Fix
**Issue**: API returning 500 errors when processing Korean PDF files due to Tesseract OCR Korean language pack dependencies.

**Solution**: Modified OCR language settings from Korean to English to resolve immediate API functionality:
- Updated `app/services/document_processing_service.py:265` in `_process_pdf_fast()` function
- Updated `app/services/document_processing_service.py:286` in `_process_pdf_lightweight_ocr()` function
- Changed `languages=["kor"]` to `languages=["eng"]` in both functions
- Preserved original Korean settings as comments for future restoration

**Files Modified**:
- `app/services/document_processing_service.py` (lines 265, 286)

**Impact**: 
- ✅ Enables API testing with English PDF documents
- ✅ Resolves immediate 500 error blocking API functionality
- ⚠️ Temporarily limits Korean document processing capability
- 🔄 Korean OCR can be re-enabled once proper Tesseract language pack is configured

**Next Steps**:
1. Test API functionality with English PDF documents
2. Configure proper Tesseract Korean language pack for production
3. Implement language auto-detection for hybrid processing

---

