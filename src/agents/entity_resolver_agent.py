import json
import os
import re
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import TypedDict

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from langgraph.graph import END, START, StateGraph

from src.db.base import DatabaseInterface
from src.db.query import MockDatabaseAdapter
from src.schema import SCHEMA_METADATA

load_dotenv()


class EntityResolution(TypedDict):
    table: str
    column: str
    value: str | int | float


class AppliedFilter(TypedDict):
    table: str
    column: str
    op: str
    value: str | int | float


class ResolverState(TypedDict):
    question: str
    tables: list[str]
    query_plan: list[dict] | None
    answer_fields: list[EntityResolution] | None
    applied_filters: list[AppliedFilter] | None


class ResolveOutput(TypedDict):
    answer_fields: list[EntityResolution]
    applied_filters: list[AppliedFilter]


class EntityResolverAgent:
    _PROMPT_PATH = Path(__file__).parent / "prompts" / "query_planner_prompt.txt"

    _QUESTION_CONCEPTS: dict[str, set[str]] = {
        "location": {"sehir", "il", "city", "yasadigi", "yasiyor", "oturdugu", "oturuyor", "ikamet", "adres", "lokasyon", "konum", "nerede"},
        "salary": {"maas", "ucret", "salary", "gelir", "kazanc"},
        "email": {"mail", "eposta", "email"},
        "phone": {"telefon", "tel", "numara", "gsm"},
        "name": {"isim", "ismi", "adi", "soyad", "soyadi", "name", "surname"},
        "date": {"tarih", "date", "zaman"},
    }

    _COLUMN_HINTS: dict[str, set[str]] = {
        "location": {"adres", "ikamet", "sehir", "il", "city", "lokasyon", "konum"},
        "salary": {"maas", "ucret", "salary", "gelir", "kazanc"},
        "email": {"mail", "eposta", "email"},
        "phone": {"telefon", "tel", "numara", "gsm"},
        "name": {"ad", "isim", "soyad", "name", "surname"},
        "date": {"tarih", "date", "time"},
    }

    def __init__(self, db: DatabaseInterface | None = None) -> None:
        self._db = db or MockDatabaseAdapter()
        self._llm = self._create_llm()
        self._prompt_template = self._PROMPT_PATH.read_text(encoding="utf-8")
        self._graph = self._build_graph()

    def _create_llm(self) -> ChatOllama:
        return ChatOllama(
            model=os.environ["OLLAMA_MODEL"],
            base_url=os.environ["OLLAMA_BASE_URL"],
            temperature=float(os.environ["OLLAMA_TEMPERATURE"]),
            request_timeout=float(os.environ.get("OLLAMA_REQUEST_TIMEOUT", "60")),
        )

    @staticmethod
    def _normalize_text(value: object) -> str:
        text = str(value).strip().casefold()
        text = unicodedata.normalize("NFKD", text)
        text = "".join(ch for ch in text if not unicodedata.combining(ch))
        return text.replace("\u0131", "i")

    @classmethod
    def _tokenize(cls, text: object) -> set[str]:
        return set(re.findall(r"[^\W_]+", cls._normalize_text(text), flags=re.UNICODE))

    @staticmethod
    def _token_match(keyword: str, question_token: str) -> bool:
        if len(keyword) < 3:
            return keyword == question_token
        return question_token == keyword or question_token.startswith(keyword)

    @classmethod
    def _contains_keyword_tokens(cls, keyword_tokens: set[str], question_tokens: set[str]) -> bool:
        if not keyword_tokens:
            return False
        for keyword in keyword_tokens:
            if not any(cls._token_match(keyword, qt) for qt in question_tokens):
                return False
        return True

    def _get_table_columns(self, table: str) -> list[str]:
        discovered = self._db.get_table_columns(table)
        if discovered:
            return discovered
        return list(SCHEMA_METADATA.get(table, {}).get("columns", {}).keys())

    def _get_primary_key(self, table: str) -> str | None:
        discovered = self._db.get_primary_key(table)
        if discovered:
            return discovered
        meta = SCHEMA_METADATA.get(table, {})
        pk = meta.get("primary_key")
        return pk if isinstance(pk, str) else None

    def _get_foreign_keys(self, table: str) -> dict[str, dict[str, str]]:
        discovered = self._db.get_foreign_keys(table)
        if discovered:
            return discovered
        meta = SCHEMA_METADATA.get(table, {})
        fks = meta.get("foreign_keys", {})
        return fks if isinstance(fks, dict) else {}

    def _get_column_aliases(self, table: str, column: str) -> list[str]:
        meta = SCHEMA_METADATA.get(table, {})
        aliases = meta.get("column_aliases", {})
        if not isinstance(aliases, dict):
            return []
        values = aliases.get(column, [])
        return [str(v) for v in values] if isinstance(values, list) else []

    def _get_column_description(self, table: str, column: str) -> str:
        meta = SCHEMA_METADATA.get(table, {})
        columns = meta.get("columns", {})
        if isinstance(columns, dict):
            val = columns.get(column)
            return str(val) if isinstance(val, str) else ""
        return ""

    def _build_schema_context(self, tables: list[str]) -> str:
        lines: list[str] = []
        for table in tables:
            columns = self._get_table_columns(table)
            if not columns:
                continue

            pk = self._get_primary_key(table) or "unknown"
            lines.append(f"Tablo: {table} (pk: {pk})")

            for col in columns:
                desc = self._get_column_description(table, col)
                aliases = self._get_column_aliases(table, col)
                alias_str = f" (diger ifadeler: {', '.join(aliases)})" if aliases else ""
                line_desc = desc if desc else "aciklama yok"
                lines.append(f"  - {col}: {line_desc}{alias_str}")

            for src_col, fk in self._get_foreign_keys(table).items():
                target_table = fk.get("target_table", "?")
                target_col = fk.get("target_column", "?")
                lines.append(f"  FK: {src_col} -> {target_table}.{target_col}")

            lines.append("")

        return "\n".join(lines)

    async def _plan_queries(self, state: ResolverState) -> ResolverState:
        schema_context = self._build_schema_context(state["tables"])
        system_prompt = self._prompt_template.format(schema_context=schema_context)
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=state["question"]),
        ]
        response = await self._llm.ainvoke(messages)
        raw = str(response.content).strip()

        try:
            start = raw.index("{")
            end = raw.rindex("}") + 1
            data = json.loads(raw[start:end])
            query_plan = data.get("queries", []) if isinstance(data, dict) else []
        except (ValueError, json.JSONDecodeError):
            query_plan = []

        if not isinstance(query_plan, list):
            query_plan = []

        return {**state, "query_plan": query_plan}

    @staticmethod
    def _resolve_var(val: object, results_so_far: dict[str, list[dict]]) -> object:
        if isinstance(val, str) and val.startswith("$"):
            table, _, col = val[1:].partition(".")
            rows = results_so_far.get(table, [])
            if rows and col:
                return rows[0].get(col, val)
        return val

    @staticmethod
    def _sort_key(value: object) -> tuple[int, object]:
        if value is None:
            return (3, "")
        if isinstance(value, (int, float)):
            return (0, value)
        text = str(value)
        try:
            return (1, datetime.fromisoformat(text))
        except ValueError:
            return (2, text)

    @staticmethod
    def _is_key_like(column: str, pk: str | None, fk_fields: set[str]) -> bool:
        normalized = column.casefold()
        if pk and column == pk:
            return True
        if column in fk_fields:
            return True
        return normalized == "id" or normalized.endswith("_id") or normalized.startswith("id_")

    def _question_concepts(self, question: str) -> set[str]:
        tokens = self._tokenize(question)
        concepts: set[str] = set()
        for concept, words in self._QUESTION_CONCEPTS.items():
            for word in words:
                if self._contains_keyword_tokens(self._tokenize(word), tokens):
                    concepts.add(concept)
                    break
        return concepts

    def _column_concepts(self, table: str, column: str) -> set[str]:
        tokens = self._tokenize(column)
        for alias in self._get_column_aliases(table, column):
            tokens.update(self._tokenize(alias))
        description = self._get_column_description(table, column)
        if description:
            tokens.update(self._tokenize(description))

        concepts: set[str] = set()
        for concept, words in self._COLUMN_HINTS.items():
            if tokens.intersection(words):
                concepts.add(concept)
        return concepts

    def _score_answer_column(
        self,
        question: str,
        question_concepts: set[str],
        table: str,
        column: str,
        filter_columns: set[str],
    ) -> int:
        question_norm = self._normalize_text(question)
        question_tokens = self._tokenize(question_norm)

        phrases = {self._normalize_text(column)}
        phrases.update(self._normalize_text(alias) for alias in self._get_column_aliases(table, column))
        description = self._get_column_description(table, column)
        if description:
            phrases.add(self._normalize_text(description))

        score = 0

        column_tokens = self._tokenize(column)
        if any(
            len(col_token) >= 3 and self._token_match(col_token, qtoken)
            for col_token in column_tokens
            for qtoken in question_tokens
        ):
            score += 3

        for phrase in phrases:
            if not phrase:
                continue
            phrase_tokens = self._tokenize(phrase)
            if not phrase_tokens:
                continue
            if len(phrase_tokens) == 1:
                token = next(iter(phrase_tokens))
                if len(token) >= 3 and token in question_tokens:
                    score += 2
                    break
            else:
                if phrase_tokens.issubset(question_tokens):
                    score += 2
                    break

        column_concepts = self._column_concepts(table, column)
        if column_concepts.intersection(question_concepts):
            score += 2

        if "name" in column_concepts and "name" not in question_concepts:
            score -= 2

        if column in filter_columns:
            score -= 3

        return score

    def _select_answer_columns(
        self,
        question: str,
        table: str,
        requested_cols: list[str],
        filter_columns: set[str],
        pk: str | None,
        fk_fields: set[str],
    ) -> list[str]:
        candidates = [
            c for c in requested_cols
            if not self._is_key_like(c, pk, fk_fields) and c not in filter_columns
        ]
        if not candidates:
            return []

        concepts = self._question_concepts(question)
        scored: list[tuple[str, int]] = []
        for col in candidates:
            score = self._score_answer_column(question, concepts, table, col, filter_columns)
            scored.append((col, score))

        matched = [col for col, score in scored if score > 0]
        return matched if matched else candidates

    def _execute_queries(self, state: ResolverState) -> ResolverState:
        results_so_far: dict[str, list[dict]] = {}
        answer_fields: list[EntityResolution] = []
        applied_filters: list[AppliedFilter] = []
        applied_filter_keys: set[tuple] = set()

        for query in state.get("query_plan") or []:
            if not isinstance(query, dict):
                continue

            table = query.get("table")
            if not isinstance(table, str) or not table:
                continue

            table_columns = set(self._get_table_columns(table))
            if not table_columns:
                continue

            pk = self._get_primary_key(table)
            fk_fields = set(self._get_foreign_keys(table).keys())

            raw_parsed: list[tuple[str, str, object]] = []
            for raw_f in query.get("filters", []):
                if not isinstance(raw_f, dict):
                    continue
                col = raw_f.get("col")
                op = raw_f.get("op")
                raw_val = raw_f.get("val")
                if not isinstance(col, str) or col not in table_columns:
                    continue
                if op not in {"=", ">=", "<=", ">", "<"}:
                    continue
                raw_parsed.append((col, op, raw_val))

            # Expansion: $ref ile birden fazla önceki satır varsa her biri için ayrı sorgu çalıştır
            expansion_key: tuple[str, str] | None = None
            expansion_vals: list = []
            for *_, raw_val in raw_parsed:
                if isinstance(raw_val, str) and raw_val.startswith("$"):
                    ref_table, _, ref_col = raw_val[1:].partition(".")
                    ref_rows = results_so_far.get(ref_table, [])
                    if len(ref_rows) > 1 and ref_col:
                        expansion_key = (ref_table, ref_col)
                        expansion_vals = [r[ref_col] for r in ref_rows if ref_col in r]
                        break

            iterations: list = expansion_vals if expansion_vals else [None]

            requested_cols = [
                col for col in query.get("target", [])
                if isinstance(col, str) and col in table_columns
            ]
            order_by = query.get("order_by")
            if not isinstance(order_by, str) or order_by not in table_columns:
                order_by = None
            order = query.get("order") if query.get("order") in {"asc", "desc"} else "desc"
            limit_val = query.get("limit")
            limit = limit_val if isinstance(limit_val, int) and limit_val > 0 else None
            cols_to_fetch = list(dict.fromkeys(requested_cols + ([order_by] if order_by else [])))
            if not cols_to_fetch:
                continue

            all_rows: list[dict] = []
            seen_row_keys: set[str] = set()

            for exp_val in iterations:
                iter_filters: list[dict] = []

                for col, op, raw_val in raw_parsed:
                    resolved_val = self._resolve_var(raw_val, results_so_far)
                    if expansion_key and isinstance(raw_val, str) and raw_val.startswith("$"):
                        ref_table, _, ref_col = raw_val[1:].partition(".")
                        if (ref_table, ref_col) == expansion_key:
                            resolved_val = exp_val

                    iter_filters.append({"col": col, "op": op, "val": resolved_val})

                    is_literal = isinstance(resolved_val, (str, int, float)) and not (
                        isinstance(resolved_val, str) and resolved_val.startswith("$")
                    )
                    if is_literal:
                        af_key = (table, col, op, str(resolved_val))
                        if af_key not in applied_filter_keys:
                            applied_filter_keys.add(af_key)
                            applied_filters.append({"table": table, "column": col, "op": op, "value": resolved_val})

                sub_rows = self._db.query_rows(table, iter_filters, cols_to_fetch)
                for row in sub_rows:
                    row_key = str(sorted(row.items()))
                    if row_key not in seen_row_keys:
                        seen_row_keys.add(row_key)
                        all_rows.append(row)

            rows = all_rows

            if order_by:
                rows = sorted(rows, key=lambda r: self._sort_key(r.get(order_by)), reverse=(order == "desc"))
            if limit:
                rows = rows[:limit]

            results_so_far[table] = rows

            filter_columns = {col for col, *_ in raw_parsed}
            answer_cols = self._select_answer_columns(
                question=state["question"],
                table=table,
                requested_cols=requested_cols,
                filter_columns=filter_columns,
                pk=pk,
                fk_fields=fk_fields,
            )

            if not answer_cols:
                if not rows and raw_parsed:
                    answer_fields.append({"table": table, "column": "", "value": "kayit bulunamadi"})
                continue

            if not rows:
                answer_fields.append({"table": table, "column": "", "value": "kayit bulunamadi"})
                continue

            for row in rows:
                for col in answer_cols:
                    if col in row and isinstance(row[col], (str, int, float)):
                        answer_fields.append({"table": table, "column": col, "value": row[col]})

        if not answer_fields:
            answer_fields = [{"table": "", "column": "", "value": "sonuc bulunamadi"}]

        return {
            **state,
            "answer_fields": answer_fields,
            "applied_filters": applied_filters,
        }

    def _build_graph(self) -> StateGraph:
        graph = StateGraph(ResolverState)
        graph.add_node("plan_queries", self._plan_queries)
        graph.add_node("execute_queries", self._execute_queries)
        graph.add_edge(START, "plan_queries")
        graph.add_edge("plan_queries", "execute_queries")
        graph.add_edge("execute_queries", END)
        return graph.compile()

    async def resolve(self, question: str, tables: list[str]) -> ResolveOutput:
        result = await self._graph.ainvoke({
            "question": question,
            "tables": tables,
            "query_plan": None,
            "answer_fields": None,
            "applied_filters": None,
        })

        return {
            "answer_fields": result.get("answer_fields") or [],
            "applied_filters": result.get("applied_filters") or [],
        }
