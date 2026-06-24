"""
data_loader.py
──────────────
Responsible for:
  - Fetching the Zomato dataset from Hugging Face
  - Preprocessing and normalizing the raw data
  - Caching the cleaned DataFrame to disk
  - Loading from cache when available and fresh

Architecture Reference: architecture.md §2.1
Edge Cases Handled:    edge_cases.md EC-DL-01 to EC-DL-07
"""

import os
import pickle
import logging
from datetime import datetime, timedelta

import pandas as pd

logger = logging.getLogger(__name__)


class DataLoadError(Exception):
    """Raised when the dataset cannot be loaded from any source."""
    pass


class SchemaError(Exception):
    """Raised when the dataset schema does not match expected column names."""
    pass


class DataLoader:
    """
    Loads, preprocesses, and caches the Zomato restaurant dataset.

    Usage:
        loader = DataLoader(config)
        df = loader.load()
    """

    # EC-DL-02: Column alias map to handle schema drift on Hugging Face
    COLUMN_MAP = {
        "name":             ["name", "restaurant_name", "res_name"],
        "location":         ["location", "city", "area"],
        "cuisines":         ["cuisines", "cuisine_type", "cuisine"],
        "cost_for_two":     ["average_cost_for_two", "cost_for_two", "cost", "approx_cost(for two people)"],
        "aggregate_rating": ["aggregate_rating", "rating", "user_rating", "Rate", "rate"],
        "votes":            ["votes", "vote_count", "num_votes"],
        "highlights":       ["highlights", "tags", "features"],
    }

    def __init__(self, config: dict):
        """
        Args:
            config (dict): Parsed config.yaml dictionary.
        """
        self.config = config
        self.dataset_config = config.get("dataset", {})
        self.budget_tiers = config.get("budget_tiers", {})
        self.cache_path = self.dataset_config.get("cache_path", "data/zomato_dataset.pkl")
        self.cache_ttl = self.dataset_config.get("cache_ttl_hours", 24)
        self.source = self.dataset_config.get("source", "ManikaSaini/zomato-restaurant-recommendation")

    # ── Public API ────────────────────────────────────────────────

    def load(self) -> pd.DataFrame:
        """
        Main entry point. Returns a clean, preprocessed DataFrame.

        Load order:
          1. Try loading from cache (if fresh)
          2. Download from Hugging Face and preprocess
          3. Save to cache

        Returns:
            pd.DataFrame: Cleaned restaurant data.

        Raises:
            DataLoadError: If neither cache nor network is available.
        """
        if self._is_cache_valid():
            logger.info("Cache is valid. Loading from cache...")
            try:
                return self._load_cache()
            except Exception as e:
                logger.warning(f"Failed to load cache: {e}. Downloading dataset...")
        
        logger.info("Downloading dataset from Hugging Face...")
        df_raw = self._download()
        logger.info("Preprocessing dataset...")
        df_clean = self._preprocess(df_raw)
        logger.info("Saving cleaned dataset to cache...")
        self._save_cache(df_clean)
        return df_clean

    # ── Private Methods ───────────────────────────────────────────

    def _is_cache_valid(self) -> bool:
        """
        Check if a valid, fresh cache file exists.

        Returns:
            bool: True if cache file is present and within TTL window.
        """
        if not os.path.exists(self.cache_path):
            return False
        
        file_mtime = datetime.fromtimestamp(os.path.getmtime(self.cache_path))
        age = datetime.now() - file_mtime
        if age <= timedelta(hours=self.cache_ttl):
            return True
        return False

    def _load_cache(self) -> pd.DataFrame:
        """
        Load the preprocessed DataFrame from the .pkl cache file.

        Returns:
            pd.DataFrame

        Raises:
            DataLoadError: If cache is corrupt or unreadable. (EC-DL-03)
        """
        try:
            with open(self.cache_path, 'rb') as f:
                df = pickle.load(f)
            return df
        except Exception as e:
            # Delete corrupted cache
            if os.path.exists(self.cache_path):
                try:
                    os.remove(self.cache_path)
                except OSError:
                    pass
            raise DataLoadError(f"Failed to load from cache: {e}")

    def _download(self) -> pd.DataFrame:
        """
        Fetch the raw dataset from Hugging Face and convert to DataFrame.

        Returns:
            pd.DataFrame: Raw (unprocessed) dataset.

        Raises:
            DataLoadError: If network unavailable and no cache exists. (EC-DL-01)
        """
        try:
            import datasets
            # Download the dataset using HF datasets library
            dataset = datasets.load_dataset(self.source)
            # Assuming 'train' split contains the relevant data
            df = dataset['train'].to_pandas()
            return df
        except Exception as e:
            raise DataLoadError(f"Failed to download dataset from {self.source}: {e}")

    def _resolve_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Map actual column names to expected names using COLUMN_MAP.
        Handles schema drift on Hugging Face. (EC-DL-02)

        Args:
            df (pd.DataFrame): Raw DataFrame from HF.

        Returns:
            pd.DataFrame: DataFrame with standardized column names.

        Raises:
            SchemaError: If a required column cannot be resolved.
        """
        resolved = df.copy()
        for expected_col, aliases in self.COLUMN_MAP.items():
            found = False
            for alias in aliases:
                if alias in resolved.columns:
                    if expected_col != alias:
                        resolved.rename(columns={alias: expected_col}, inplace=True)
                    found = True
                    break
            # Some columns might be optional, but we will catch missing required ones in _preprocess
        return resolved

    def _preprocess(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Clean and normalize the raw DataFrame.

        Steps:
          - Resolve column name aliases
          - Drop rows missing critical fields
          - Normalize text (lowercase location, cuisines)
          - Parse cost_for_two to numeric (EC-DL-06)
          - Map cost_for_two → budget_tier
          - Cast aggregate_rating → float, votes → int
          - Deduplicate on (name, location) (EC-DL-07)
          - Reset index

        Args:
            df (pd.DataFrame): Raw DataFrame.

        Returns:
            pd.DataFrame: Cleaned DataFrame.
        """
        df = self._resolve_columns(df)
        
        required_cols = ["name", "location", "cuisines", "aggregate_rating", "cost_for_two"]
        missing_cols = [c for c in required_cols if c not in df.columns]
        if missing_cols:
            raise SchemaError(f"Dataset is missing required columns: {missing_cols}")
            
        # Drop rows missing critical fields
        df = df.dropna(subset=required_cols).copy()
        
        # Normalize text
        df['location'] = df['location'].astype(str).str.lower().str.strip()
        df['cuisines'] = df['cuisines'].astype(str).str.lower().str.strip()
        
        # Ensure all strings are stripped
        for col in df.columns:
            if pd.api.types.is_string_dtype(df[col]) or pd.api.types.is_object_dtype(df[col]):
                df[col] = df[col].astype(str).str.strip()
            
        # Parse cost_for_two to numeric
        df['cost_for_two'] = df['cost_for_two'].astype(str).str.replace(r'[^\d.]', '', regex=True)
        df['cost_for_two'] = pd.to_numeric(df['cost_for_two'], errors='coerce')
        df = df.dropna(subset=['cost_for_two']).copy()
        
        # Map budget tiers
        df['budget_tier'] = df['cost_for_two'].apply(self._map_budget_tier)
        
        # Cast ratings and votes
        df['aggregate_rating'] = df['aggregate_rating'].astype(str).str.split('/').str[0].str.strip()
        df['aggregate_rating'] = pd.to_numeric(df['aggregate_rating'], errors='coerce').astype(float)
        if 'votes' in df.columns:
            df['votes'] = pd.to_numeric(df['votes'], errors='coerce').fillna(0).astype(int)
        else:
            df['votes'] = 0
            
        df = df.dropna(subset=['aggregate_rating']).copy()
        
        # Deduplicate
        df = df.drop_duplicates(subset=['name', 'location']).copy()
        
        # Reset index
        df = df.reset_index(drop=True)
        
        target_cols = ["name", "location", "cuisines", "cost_for_two", "budget_tier", "aggregate_rating", "votes"]
        if "highlights" in df.columns:
            target_cols.append("highlights")
            
        return df[target_cols]

    def _map_budget_tier(self, cost: float) -> str:
        """
        Map a numeric cost value to a budget tier label.

        Args:
            cost (float): cost_for_two value in INR.

        Returns:
            str: One of "low", "medium", "high", or "unknown".
        """
        if pd.isna(cost):
            return "unknown"
            
        for tier, tier_range in self.budget_tiers.items():
            if isinstance(tier_range, list) and len(tier_range) == 2:
                min_cost, max_cost = tier_range
            elif isinstance(tier_range, dict):
                min_cost = tier_range.get("min", 0)
                max_cost = tier_range.get("max", float('inf'))
            else:
                continue
                
            if min_cost <= cost <= max_cost:
                return tier
        return "unknown"

    def _save_cache(self, df: pd.DataFrame) -> None:
        """
        Persist the preprocessed DataFrame to disk as a .pkl file.
        Handles disk-full gracefully. (EC-SYS-05)

        Args:
            df (pd.DataFrame): Cleaned DataFrame to cache.
        """
        os.makedirs(os.path.dirname(self.cache_path) or '.', exist_ok=True)
        try:
            with open(self.cache_path, 'wb') as f:
                pickle.dump(df, f)
        except Exception as e:
            logger.warning(f"Failed to save cache to {self.cache_path}: {e}")
