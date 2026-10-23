from __future__ import annotations

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.agent import run_agent
from app.config import settings
from app.csv_service import CsvValidationError, load_csv, profile_frame, sanitize_table_name
from app.models import ChatRequest, ChatResponse, DatasetInfo
from app.session_store import store

app = FastAPI(title="Lens AI Data Analyst", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    return {"ok": True, "llm": settings.llm_enabled}


@app.post("/api/sessions")
def create_session() -> dict:
    session = store.create()
    return {"session_id": session.session_id}


@app.post("/api/upload")
async def upload(session_id: str = Form(...), files: list[UploadFile] = File(...)) -> dict:
    try:
        session = store.get(session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Unknown session. Create a session first.") from exc

    max_bytes = settings.max_upload_mb * 1024 * 1024
    datasets: list[DatasetInfo] = []
    for upload in files:
        content = await upload.read()
        filename = upload.filename or "data.csv"
        try:
            frame, warnings = load_csv(content, filename, max_bytes)
        except CsvValidationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        name = sanitize_table_name(filename, set(session.tables))
        session.tables[name] = frame
        datasets.append(DatasetInfo(**profile_frame(name, frame, warnings)))
    return {"session_id": session.session_id, "datasets": [item.model_dump() for item in datasets]}


@app.get("/api/datasets/{session_id}")
def list_datasets(session_id: str) -> dict:
    try:
        session = store.get(session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Unknown session") from exc
    datasets = [
        profile_frame(name, frame, [])
        for name, frame in session.tables.items()
    ]
    return {"session_id": session.session_id, "datasets": datasets}


@app.post("/api/chat", response_model=ChatResponse)
def chat(payload: ChatRequest) -> ChatResponse:
    try:
        session = store.get(payload.session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Unknown session") from exc
    if not payload.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")
    result = run_agent(session, payload.message.strip())
    return ChatResponse(**result)
