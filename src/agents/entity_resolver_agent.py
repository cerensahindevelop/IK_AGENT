import os
from pathlib import Path
from typing import TypedDict

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

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

    def _create_llm(self) -> ChatOpenAI:
        return ChatOpenAI(
            model=os.environ["VLLM_MODEL"],
            base_url=os.environ["VLLM_BASE_URL"],
            api_key=os.environ["VLLM_API_KEY"],
            temperature=float(os.environ["VLLM_TEMPERATURE"]),
        )

    @staticmethod
    def _build_column_descriptions(columns: dict[str, str]) -> str:
        return "\n".join(f"  - {col}: {desc}" for col, desc in columns.items())

    async def _llm_resolve(
        self,
        question: str,
        table: str,
        columns: dict[str, str],
    ) -> EntityResolution | None:
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

        if "|||" not in raw:
            return None

        parts = raw.split("|||", maxsplit=1)
        if len(parts) != 2:
            return None

        column, value_str = parts[0].strip(), parts[1].strip()

        if column not in columns:
            return None

        value: str | int = int(value_str) if value_str.isdigit() else value_str
        return {"table": table, "column": column, "value": value}

    async def resolve(
        self,
        personel_id: int,
        question: str,
        tables: list[str],
    ) -> list[EntityResolution]:
        results: list[EntityResolution] = []
        for table in tables:
            columns: dict[str, str] = SCHEMA_METADATA[table]["columns"]
            if table == "personeller":
                results.append({"table": table, "column": "id", "value": personel_id})
            elif "personel_id" in columns:
                results.append({"table": table, "column": "personel_id", "value": personel_id})
            else:
                resolution = await self._llm_resolve(question, table, columns)
                if resolution:
                    results.append(resolution)
        return results
