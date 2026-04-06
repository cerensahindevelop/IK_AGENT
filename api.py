import os

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from src.agents import EntityResolverAgent, TableSelectorAgent

load_dotenv()

app = FastAPI(
    title="Table Selector Agent API",
    description="Kullanıcı sorusuna göre ilgili veritabanı tablosunu döner.",
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
    value: str | int


class TableResponse(BaseModel):
    question: str
    personel_id: int
    tables: list[str] | None
    entities: list[EntityResolution] | None


@app.post("/select-table", response_model=TableResponse)
async def select_table(request: QuestionRequest) -> TableResponse:
    if not request.question.strip():
        raise HTTPException(status_code=422, detail="Soru boş olamaz.")

    tables = await _table_selector.run(request.question)
    entities = await _entity_resolver.resolve(request.personel_id, request.question, tables) if tables else None
    return TableResponse(
        question=request.question,
        personel_id=request.personel_id,
        tables=tables,
        entities=entities,
    )


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


if __name__ == "__main__":
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8080"))
    uvicorn.run("api:app", host=host, port=port, reload=True)
