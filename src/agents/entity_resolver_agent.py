import asyncio
import json
import os
from pathlib import Path
from typing import TypedDict

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama

from src.db.query import get_person_row, query_rows
from src.schema import SCHEMA_METADATA

load_dotenv()


class EntityResolution(TypedDict):
    table: str
    column: str
    value: str | int


class EntityResolverAgent:
    _PROMPT_PATH = Path(__file__).parent / "prompts" / "entity_resolver_prompt.txt"

    def __init__(self) -> None:
        self._llm = self._create_llm()
        self._prompt_template = self._PROMPT_PATH.read_text(encoding="utf-8")

    def _create_llm(self) -> ChatOllama:
        return ChatOllama(
            model=os.environ["OLLAMA_MODEL"],
            base_url=os.environ["OLLAMA_BASE_URL"],
            temperature=float(os.environ["OLLAMA_TEMPERATURE"]),
            request_timeout=60,
        )

    @staticmethod
    def _build_column_descriptions(columns: dict[str, str]) -> str:
        return "\n".join(f"  - {col}: {desc}" for col, desc in columns.items())

    def _get_filter(self, table: str, personel_id: int) -> dict[str, int | str]:
        """
        Tabloya göre temel filtre koşulunu döner.
        - personeller → {id: personel_id}
        - personel_id FK'si olan tablolar → {fk_col: personel_id}
        - departmanlar / pozisyonlar gibi lookup tablolar → personeller üzerinden takip eder
        """
        if table == "personeller":
            return {"id": personel_id}

        foreign_keys = SCHEMA_METADATA[table].get("foreign_keys", {})
        for source_col, fk in foreign_keys.items():
            if fk.get("target_table") == "personeller" and fk.get("target_column") == "id":
                return {source_col: personel_id}

        # Lookup tabloları: personeller → departman_id / pozisyon_id üzerinden erişim
        person_row = get_person_row(personel_id)
        if person_row:
            personel_fks = SCHEMA_METADATA["personeller"].get("foreign_keys", {})
            for col, fk in personel_fks.items():
                if fk.get("target_table") == table:
                    ref_id = person_row.get(col)
                    if ref_id is not None:
                        return {fk["target_column"]: ref_id}

        return {}

    async def _extract_columns(
        self,
        question: str,
        table: str,
        columns: dict[str, str],
    ) -> tuple[list[str], list[dict]]:
        """
        LLM'den JSON çıktı alır ve parse eder.
        Döner:
          - target_cols: DB'den okunacak sütun adları
          - filters: [{"col": ..., "op": ..., "val": ...}] formatında filtre listesi
        """
        column_descriptions = self._build_column_descriptions(columns)
        system_prompt = self._prompt_template.format(
            table_name=table,
            column_descriptions=column_descriptions,
        )
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=question),
        ]
        response = await self._llm.ainvoke(messages)
        raw = response.content.strip()

        try:
            start = raw.index("{")
            end = raw.rindex("}") + 1
            data = json.loads(raw[start:end])
        except (ValueError, json.JSONDecodeError):
            return [], []

        key_fields = {"id", "personel_id", "id_person"}

        target_cols = [
            col for col in data.get("target", [])
            if col in columns and col not in key_fields
        ]
        filters = [
            f for f in data.get("filters", [])
            if isinstance(f, dict)
            and f.get("col") in columns
            and f.get("col") not in key_fields
        ]

        return target_cols, filters

    async def _resolve_table(
        self,
        table: str,
        personel_id: int,
        question: str,
    ) -> list[EntityResolution]:
        columns: dict[str, str] = SCHEMA_METADATA[table]["columns"]

        base_filter = self._get_filter(table, personel_id)
        if not base_filter:
            return []

        base_filters = [{"col": col, "op": "=", "val": val} for col, val in base_filter.items()]
        target_cols, extra_filters = await self._extract_columns(question, table, columns)
        all_filters = base_filters + extra_filters

        cols_to_fetch = target_cols or [f["col"] for f in extra_filters]
        if not cols_to_fetch:
            return []

        rows = query_rows(table, all_filters, cols_to_fetch)
        if not rows:
            return [{"table": table, "column": "", "value": "kayıt bulunamadı"}]

        results: list[EntityResolution] = []
        for row in rows:
            for col, val in row.items():
                results.append({"table": table, "column": col, "value": val})
        return results

    async def resolve(
        self,
        personel_id: int,
        question: str,
        tables: list[str],
    ) -> list[EntityResolution]:
        all_results = await asyncio.gather(
            *[self._resolve_table(table, personel_id, question) for table in tables]
        )
        return [item for sublist in all_results for item in sublist]
