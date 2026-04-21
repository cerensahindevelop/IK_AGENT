import re
import unicodedata

from src.db import mockdb
from src.db.base import DatabaseInterface

_NUMERIC_FORMAT = re.compile(r'^[\d\s\-\(\)\+\.]+$')


def _normalize_text(value: object) -> str:
    text = str(value).strip().casefold()
    text = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in text if not unicodedata.combining(ch))


def _cast(a, b):
    """İkisini de aynı tipe dönüştürür: önce sayı, sonra string."""
    try:
        return float(a), float(b)
    except (ValueError, TypeError):
        na, nb = _normalize_text(a), _normalize_text(b)
        if _NUMERIC_FORMAT.match(na) and _NUMERIC_FORMAT.match(nb):
            return re.sub(r'\D', '', na), re.sub(r'\D', '', nb)
        return na, nb


def _compare(row_val, op: str, filter_val) -> bool:
    a, b = _cast(row_val, filter_val)
    if op == "=":
        return a == b
    if op == ">=":
        return a >= b
    if op == "<=":
        return a <= b
    if op == ">":
        return a > b
    if op == "<":
        return a < b
    return False


def _matches(row: dict, filters: list[dict]) -> bool:
    for f in filters:
        col, op, val = f["col"], f["op"], f["val"]
        if col not in row or not _compare(row[col], op, val):
            return False
    return True


class MockDatabaseAdapter(DatabaseInterface):
    """
    Bellek içi mock veri ile çalışan adapter.
    Geliştirme ve test ortamları için kullanılır.

    Başka bir DB'ye geçmek için DatabaseInterface'i
    miras alan yeni bir sınıf yaz (ör. PostgresAdapter).
    """

    _TABLE_DATA: dict[str, list[dict]] = {
        "personeller": mockdb.personeller,
        "departmanlar": mockdb.departmanlar,
        "pozisyonlar": mockdb.pozisyonlar,
        "maaslar": mockdb.maaslar,
        "mesailer": mockdb.mesailer,
        "izinler": mockdb.izinler,
        "devamsizliklar": mockdb.devamsizliklar,
        "performanslar": mockdb.performanslar,
        "egitimler": mockdb.egitimler,
        "yan_haklar": mockdb.yan_haklar,
    }

    def query_rows(
        self,
        table: str,
        filters: list[dict],
        target_cols: list[str],
    ) -> list[dict]:
        rows = self._TABLE_DATA.get(table, [])
        results = []
        for row in rows:
            if _matches(row, filters):
                entry = {col: row[col] for col in target_cols if col in row}
                if entry:
                    results.append(entry)
        return results

    def get_row_by_id(
        self,
        table: str,
        id_col: str,
        id_val: int | str,
    ) -> dict | None:
        for row in self._TABLE_DATA.get(table, []):
            if row.get(id_col) == id_val:
                return row
        return None

    def list_tables(self) -> list[str]:
        return list(self._TABLE_DATA.keys())

    def get_table_columns(self, table: str) -> list[str]:
        rows = self._TABLE_DATA.get(table, [])
        if not rows:
            return []
        seen: dict[str, None] = {}
        for row in rows:
            for col in row.keys():
                if col not in seen:
                    seen[col] = None
        return list(seen.keys())

    def get_primary_key(self, table: str) -> str | None:
        columns = self.get_table_columns(table)
        if "id" in columns:
            return "id"
        for col in columns:
            if col.endswith("_id"):
                return col
        return None

    def get_foreign_keys(self, table: str) -> dict[str, dict[str, str]]:
        mapping: dict[str, dict[str, str]] = {}
        for fk in getattr(mockdb, "FOREIGN_KEYS", []):
            if fk.get("source_table") == table:
                src = fk.get("source_column")
                target_table = fk.get("target_table")
                target_column = fk.get("target_column")
                if isinstance(src, str) and isinstance(target_table, str) and isinstance(target_column, str):
                    mapping[src] = {
                        "target_table": target_table,
                        "target_column": target_column,
                    }
        return mapping
