from src.db import mockdb

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


def get_person_row(personel_id: int) -> dict | None:
    for row in mockdb.personeller:
        if row["id"] == personel_id:
            return row
    return None


def _cast(a, b):
    """İkisini de aynı tipe dönüştürür: önce sayı, sonra string."""
    try:
        return float(a), float(b)
    except (ValueError, TypeError):
        return str(a), str(b)


def _compare(row_val, op: str, filter_val) -> bool:
    a, b = _cast(row_val, filter_val)
    if op == "=":
        return a == b
    elif op == ">=":
        return a >= b
    elif op == "<=":
        return a <= b
    elif op == ">":
        return a > b
    elif op == "<":
        return a < b
    return False


def _matches(row: dict, filters: list[dict]) -> bool:
    for f in filters:
        col, op, val = f["col"], f["op"], f["val"]
        if col not in row:
            return False
        if not _compare(row[col], op, val):
            return False
    return True


def query_rows(
    table: str,
    filters: list[dict],
    target_cols: list[str],
) -> list[dict]:
    """
    filters: [{"col": "tarih", "op": ">=", "val": "2026-01-01"}, ...]
    target_cols: döndürülecek sütun adları
    """
    rows = _TABLE_DATA.get(table, [])
    results = []
    for row in rows:
        if _matches(row, filters):
            entry = {col: row[col] for col in target_cols if col in row}
            if entry:
                results.append(entry)
    return results
