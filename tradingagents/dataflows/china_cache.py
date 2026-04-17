import json
import os
import time
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd


class ChinaDataCache:
    """轻量级文件缓存代理 - 为 ChinaDataRouter 提供缓存服务"""

    def __init__(self, cache_dir: str | None = None):
        if cache_dir is None:
            from tradingagents.default_config import DEFAULT_CONFIG

            cache_dir = os.path.join(DEFAULT_CONFIG["data_cache_dir"], "china")
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.ttl_config = {
            "stock_data": timedelta(days=1),
            "fundamentals": timedelta(days=1),
            "news": timedelta(hours=2),
        }

    def _cache_path(
        self, data_type: str, symbol: str, provider: str, suffix: str
    ) -> Path:
        safe_symbol = symbol.replace(".", "_")
        return self.cache_dir / provider / data_type / safe_symbol / suffix

    def _meta_path(self, data_path: Path) -> Path:
        return data_path.with_suffix(data_path.suffix + ".meta.json")

    def _is_valid(self, data_path: Path, data_type: str) -> bool:
        if not data_path.exists():
            return False
        meta_path = self._meta_path(data_path)
        if not meta_path.exists():
            return False
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            cached_at = datetime.fromisoformat(meta["cached_at"])
            ttl = self.ttl_config.get(data_type, timedelta(hours=1))
            return datetime.now() - cached_at < ttl
        except Exception:
            return False

    def _save_meta(self, data_path: Path):
        meta_path = self._meta_path(data_path)
        meta_path.parent.mkdir(parents=True, exist_ok=True)
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump({"cached_at": datetime.now().isoformat()}, f)

    def get_stock_data(
        self, symbol: str, start_date: str, end_date: str, provider: str
    ) -> pd.DataFrame | None:
        path = self._cache_path(
            "stock_data", symbol, provider, f"{start_date}_{end_date}.csv"
        )
        if self._is_valid(path, "stock_data"):
            try:
                return pd.read_csv(path, parse_dates=["Date"])
            except Exception:
                return None
        return None

    def save_stock_data(
        self,
        data: pd.DataFrame,
        symbol: str,
        start_date: str,
        end_date: str,
        provider: str,
    ):
        path = self._cache_path(
            "stock_data", symbol, provider, f"{start_date}_{end_date}.csv"
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        data.to_csv(path, index=False)
        self._save_meta(path)

    def get_fundamentals(self, symbol: str, provider: str) -> dict | None:
        path = self._cache_path("fundamentals", symbol, provider, f"fundamentals.json")
        if self._is_valid(path, "fundamentals"):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return None
        return None

    def save_fundamentals(self, data: dict, symbol: str, provider: str):
        path = self._cache_path("fundamentals", symbol, provider, f"fundamentals.json")
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        self._save_meta(path)

    def get_news(self, symbol: str, provider: str, limit: int) -> list | None:
        path = self._cache_path("news", symbol, provider, f"news_{limit}.json")
        if self._is_valid(path, "news"):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return None
        return None

    def save_news(self, data: list, symbol: str, provider: str, limit: int):
        path = self._cache_path("news", symbol, provider, f"news_{limit}.json")
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        self._save_meta(path)
