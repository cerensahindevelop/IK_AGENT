from abc import ABC, abstractmethod


class DatabaseInterface(ABC):
    """
    Veritabani islemleri icin soyut arayuz.

    Yeni bir DB eklemek icin bu sinifi miras al ve
    iki metodu doldur: query_rows + get_row_by_id
    """

    @abstractmethod
    def query_rows(
        self,
        table: str,
        filters: list[dict],
        target_cols: list[str],
    ) -> list[dict]:
        """
        Verilen filtrelerle eslesen satirlari doner.

        filters : [{"col": "tarih", "op": ">=", "val": "2026-01-01"}, ...]
        target_cols : dondurulecek sutun adlari
        """
        ...

    @abstractmethod
    def get_row_by_id(
        self,
        table: str,
        id_col: str,
        id_val: int | str,
    ) -> dict | None:
        """Birincil anahtara gore tek satir doner; bulunamazsa None."""
        ...

    def list_tables(self) -> list[str]:
        """Veritabanindaki tablolar. Desteklenmiyorsa bos liste doner."""
        return []

    def get_table_columns(self, table: str) -> list[str]:
        """Tablo sutunlari. Desteklenmiyorsa bos liste doner."""
        return []

    def get_primary_key(self, table: str) -> str | None:
        """Birincil anahtar. Bilinmiyorsa None doner."""
        return None

    def get_foreign_keys(self, table: str) -> dict[str, dict[str, str]]:
        """
        FK haritasi:
        {source_col: {"target_table": "...", "target_column": "..."}}
        """
        return {}
