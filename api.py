import os

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from src.agents import EntityResolverAgent, TableSelectorAgent

load_dotenv()

app = FastAPI(
    title="Table Selector Agent API",
    description="Kullanici sorusuna gore ilgili veritabani tablolarini ve cevap alanlarini dondurur.",
    version="1.0.0",
)

_table_selector = TableSelectorAgent()
_entity_resolver = EntityResolverAgent()


class QuestionRequest(BaseModel):
    question: str
    personel_id: int


class EntityResolution(BaseModel):
    table: str
    column: str
    value: str | int | float


class AppliedFilter(BaseModel):
    table: str
    column: str
    op: str
    value: str | int | float


class TableResponse(BaseModel):
    question: str
    personel_id: int
    tables: list[str] | None
    entities: list[EntityResolution] | None
    applied_filters: list[AppliedFilter] | None


@app.post("/select-table", response_model=TableResponse)
async def select_table(request: QuestionRequest) -> TableResponse:
    if not request.question.strip():
        raise HTTPException(status_code=422, detail="Soru bos olamaz.")

    tables = await _table_selector.run(request.question)
    resolution = await _entity_resolver.resolve(request.question, tables) if tables else {"answer_fields": None, "applied_filters": None}

    return TableResponse(
        question=request.question,
        personel_id=request.personel_id,
        tables=tables,
        entities=resolution.get("answer_fields"),
        applied_filters=resolution.get("applied_filters"),
    )


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


if __name__ == "__main__":
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "11434"))
    uvicorn.run("api:app", host=host, port=port, reload=True)
