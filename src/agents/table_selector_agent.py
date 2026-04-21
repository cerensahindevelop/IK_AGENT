import asyncio
import os
from pathlib import Path
from typing import TypedDict

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
# from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama
from langgraph.graph import END, START, StateGraph

from src.schema import SCHEMA_METADATA

load_dotenv()


class AgentState(TypedDict):
    question: str
    selected_table: list[str] | None


class TableSelectorAgent:
    _PROMPT_PATH = Path(__file__).parent / "prompts" / "system_prompt.txt"

    def __init__(self) -> None:
        self._llm = self._create_llm()
        self._system_prompt = self._load_system_prompt()
        self._graph = self._build_graph()

    def _create_llm(self) -> ChatOllama:
        return ChatOllama(
            model=os.environ["OLLAMA_MODEL"],
            base_url=os.environ["OLLAMA_BASE_URL"],
            temperature=float(os.environ["OLLAMA_TEMPERATURE"]),
            request_timeout=float(os.environ.get("OLLAMA_REQUEST_TIMEOUT", "60")),
        )

    @staticmethod
    def _build_schema_context() -> str:
        lines = []
        for table_name, meta in SCHEMA_METADATA.items():
            lines.append(f"Tablo: {table_name}")
            lines.append(f"  Açıklama: {meta['description']}")
            lines.append(f"  Sütunlar: {', '.join(meta['columns'].keys())}")
            keywords = ", ".join(meta["query_hints"]["keywords"])
            lines.append(f"  Anahtar kelimeler: {keywords}")
            examples = " | ".join(meta["query_hints"]["common_questions"])
            lines.append(f"  Örnek sorular: {examples}")
            lines.append("")
        return "\n".join(lines)

    def _load_system_prompt(self) -> str:
        template = self._PROMPT_PATH.read_text(encoding="utf-8")
        return template.format(schema_context=self._build_schema_context())

    async def _select_table(self, state: AgentState) -> AgentState:
        messages = [
            SystemMessage(content=self._system_prompt),
            HumanMessage(content=state["question"]),
        ]
        response = await self._llm.ainvoke(messages)
        raw = response.content.strip().lower()
        candidates = [t.strip() for t in raw.split(",") if t.strip()]
        valid = [t for t in candidates if t in SCHEMA_METADATA]
        return {**state, "selected_table": valid if valid else None}

    def _build_graph(self) -> StateGraph:
        graph = StateGraph(AgentState)
        graph.add_node("select_table", self._select_table)
        graph.add_edge(START, "select_table")
        graph.add_edge("select_table", END)
        return graph.compile()

    async def run(self, question: str) -> list[str] | None:
        result = await self._graph.ainvoke({"question": question, "selected_table": None})
        return result["selected_table"]


async def _demo() -> None:
    agent = TableSelectorAgent()
    test_questions = [
        "Ahmet'in maaşı ne kadar?",
        "Kim hafta sonu mesaisi yaptı?",
        "Şirkette hangi departmanlar var?",
        "Bu personelin performans puanı kaç?",
        "Kimler yıllık izin kullandı?",
    ]
    for question in test_questions:
        table = await agent.run(question)
        print(f"Soru : {question}")
        print(f"Tablo: {table}")
        print()


if __name__ == "__main__":
    asyncio.run(_demo())
