# AI Document Workflow

Temporal 기반 AI 문서 처리 Workflow 실습 프로젝트입니다. 사용자가 PDF 또는 이미지 문서를 업로드하면, Temporal Workflow가 파일 검증 → OCR → 텍스트 정제 → DB 저장을 비동기로 처리합니다. 각 처리 단계는 Activity로 분리되어 있어 재시도(Retry), 타임아웃, 상태 조회가 가능합니다.

## 현재 구현 범위 (1차 MVP)

**완료된 것**

- PDF / 이미지(PNG, JPG) 업로드
- Temporal Workflow를 통한 비동기 처리
- 파일 검증 (확장자, 크기)
- OCR 텍스트 추출 (Tesseract, 한국어+영어)
- 텍스트 정제 (공백/줄바꿈 정리)
- PostgreSQL에 결과 저장
- 처리 상태 조회 API (`UPLOADED → PROCESSING → OCR_COMPLETED → COMPLETED` / `FAILED`)
- OCR 실패 시 Activity 재시도, 대용량 다페이지 PDF 처리를 위한 heartbeat

**아직 없는 것 (향후 로드맵)**

- 페이지별 Child Workflow 병렬 처리 / 실패 페이지 재처리
- Query / Signal (진행률 조회, 취소, 재처리 요청)
- LLM 기반 문서 요약
- Embedding 생성 및 Vector DB 저장
- RAG 검색 API

## 아키텍처

```mermaid
flowchart LR
    Client[Client] -->|POST /documents/upload| API[FastAPI]
    API -->|메타데이터 저장| DB[(PostgreSQL)]
    API -->|Workflow 시작| TemporalServer[Temporal Server]

    TemporalServer -->|Task 할당| Worker[Temporal Worker]
    Worker -->|ValidateFile| Worker
    Worker -->|ExtractText - OCR| Worker
    Worker -->|CleanText| Worker
    Worker -->|SaveExtractedText / UpdateStatus| DB

    Client -->|GET /documents/id, /status| API
    API -->|조회| DB
```

## 기술 스택

| 구분 | 내용 |
|---|---|
| Language | Python 3.11 |
| API Server | FastAPI |
| Workflow Engine | Temporal (Python SDK) |
| Database | PostgreSQL |
| OCR | Tesseract (pytesseract), pdf2image |
| Container | Docker Compose |

## 프로젝트 구조

```
ai-document-workflow/
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── app/
│   ├── main.py                  # FastAPI 앱 진입점
│   ├── config.py                # 환경변수 로딩
│   ├── database.py              # SQLAlchemy engine/session
│   ├── models.py                # documents 테이블 ORM 모델
│   ├── schemas.py                # Pydantic 요청/응답 스키마
│   └── api/
│       └── documents.py         # /documents/* 라우터
├── worker/
│   └── main.py                  # Temporal Worker 실행 진입점
├── workflows/
│   └── document_processing_workflow.py
├── activities/
│   ├── file_activities.py       # 파일 검증
│   ├── ocr_activities.py        # OCR 텍스트 추출
│   ├── text_activities.py       # 텍스트 정제
│   └── db_activities.py         # DB 저장 / 상태 갱신
├── shared/
│   └── types.py                 # Workflow/Activity 공유 타입, 상태 Enum
└── storage/                      # 업로드 파일 저장 경로
```

## 시작하기

### 사전 요구사항

- Docker / Docker Compose

### 실행

```bash
git clone <repo-url>
cd ai-document-workflow
cp .env.example .env
docker compose up --build
```

| 서비스 | 주소 |
|---|---|
| API (Swagger UI) | http://localhost:8000/docs |
| Temporal Web UI | http://localhost:8080 |

## API 사용 예시

### 문서 업로드

```bash
curl -F "file=@document.pdf" http://localhost:8000/documents/upload
```

```json
{"document_id": 1, "status": "UPLOADED"}
```

### 처리 상태 조회

```bash
curl http://localhost:8000/documents/1/status
```

```json
{"document_id": 1, "status": "COMPLETED", "error_message": null}
```

### 결과 조회

```bash
curl http://localhost:8000/documents/1
```

```json
{
  "document_id": 1,
  "file_name": "document.pdf",
  "file_type": "pdf",
  "status": "COMPLETED",
  "page_count": 3,
  "extracted_text": "추출된 문서 내용...",
  "summary": null,
  "created_at": "2026-07-01T01:49:00.261897",
  "updated_at": "2026-07-01T01:49:00.619531"
}
```

## Workflow 구조

`DocumentProcessingWorkflow`는 아래 순서로 Activity를 실행합니다.

```
ValidateFile
  → UpdateStatus(PROCESSING)
  → ExtractText (OCR)
  → UpdateStatus(OCR_COMPLETED)
  → CleanText
  → SaveExtractedText
  → UpdateStatus(COMPLETED)
```

중간 Activity가 재시도 후에도 실패하면 `UpdateStatus(FAILED, error_message)`를 호출하고 Workflow를 실패 처리합니다.

## 트러블슈팅 / 알게 된 점

- **한글 OCR 미인식**: `pytesseract.image_to_string()`에 `lang`을 지정하지 않으면 기본값이 영어(`eng`)라 한글이 거의 인식되지 않았습니다. Dockerfile에 `tesseract-ocr-kor`를 설치하고 `lang="kor+eng"`를 명시해 해결했습니다.
- **대용량 PDF 타임아웃**: 175페이지짜리 PDF를 테스트했을 때, `ExtractTextActivity`의 타임아웃이 1분으로 짧게 설정되어 있어 처리 중간에 실패했습니다. 타임아웃을 30분으로 늘리고, 페이지 처리마다 `activity.heartbeat()`를 호출해 Worker가 살아있음을 Temporal에 알리도록 개선했습니다.
- **Temporal 컨테이너 기동 이슈**: `temporalio/auto-setup` 이미지에서 존재하지 않는 `DYNAMIC_CONFIG_FILE_PATH`를 지정하면 컨테이너가 크래시했고, Worker가 `default` 네임스페이스 생성 전에 기동을 시도하면 초기 연결에 실패했습니다. 전자는 기본 경로를 사용하도록 설정을 제거하고, 후자는 `restart: unless-stopped`로 해결했습니다.

## 로드맵

1. 페이지별 Child Workflow 처리 (병렬 OCR, 실패 페이지 재처리)
2. Query / Signal (진행률 조회, 처리 취소, 실패 페이지 재처리 요청)
3. LLM 기반 문서 요약
4. 텍스트 청킹 + Embedding 생성 + Vector DB 저장
5. RAG 검색 API
