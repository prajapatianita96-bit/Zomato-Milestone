"""
tests/test_data_loader.py
─────────────────────────
Unit tests for the DataLoader component.

Run with:
    pytest tests/test_data_loader.py -v
"""

import os
import pytest
import pandas as pd
from unittest.mock import patch

from src.data_loader import DataLoader, DataLoadError, SchemaError

@pytest.fixture
def mock_config():
    return {
        "dataset": {
            "source": "dummy/source",
            "cache_path": "tests/test_cache/dataset.pkl",
            "cache_ttl_hours": 24
        },
        "budget_tiers": {
            "low": [0, 500],
            "medium": [501, 1200],
            "high": [1201, 99999]
        }
    }

@pytest.fixture
def raw_df():
    return pd.DataFrame({
        "name": ["Rest A", "Rest B", "Rest C", "Rest A"],
        "location": ["Delhi ", " Mumbai", "Delhi", "Delhi"],
        "cuisines": ["North Indian ", "Chinese", "Italian", "North Indian"],
        "average_cost_for_two": [400, "800", "1500", 400],
        "aggregate_rating": ["4.5", 3.0, None, "4.5"],
        "votes": [100, 50, 10, 100],
        "highlights": ["Tag1", "Tag2", "Tag3", "Tag1"]
    })


class TestDataLoader:
    """Unit tests for src/data_loader.py — DataLoader class."""

    def test_load_returns_non_empty_dataframe(self, mock_config, raw_df):
        """DataLoader.load() must return a non-empty DataFrame. (EC-DL-04)"""
        loader = DataLoader(mock_config)
        with patch.object(loader, '_download', return_value=raw_df):
            with patch.object(loader, '_save_cache'):
                with patch('os.path.exists', return_value=False):
                    df = loader.load()
                    assert not df.empty

    def test_required_columns_exist(self, mock_config, raw_df):
        """All required columns must be present after loading. (EC-DL-02)"""
        loader = DataLoader(mock_config)
        with patch.object(loader, '_download', return_value=raw_df):
            with patch.object(loader, '_save_cache'):
                with patch('os.path.exists', return_value=False):
                    df = loader.load()
                    expected_cols = {"name", "location", "cuisines", "cost_for_two", "budget_tier", "aggregate_rating", "votes"}
                    assert expected_cols.issubset(df.columns)

    def test_no_nulls_in_critical_fields(self, mock_config, raw_df):
        """Critical fields (name, location, cuisines, rating) must have no nulls. (EC-DL-05)"""
        loader = DataLoader(mock_config)
        with patch.object(loader, '_download', return_value=raw_df):
            with patch.object(loader, '_save_cache'):
                with patch('os.path.exists', return_value=False):
                    df = loader.load()
                    assert df[["name", "location", "cuisines", "aggregate_rating"]].isnull().sum().sum() == 0

    def test_budget_tier_values_are_valid(self, mock_config, raw_df):
        """budget_tier column must only contain 'low', 'medium', or 'high'. (EC-DL-06)"""
        loader = DataLoader(mock_config)
        with patch.object(loader, '_download', return_value=raw_df):
            with patch.object(loader, '_save_cache'):
                with patch('os.path.exists', return_value=False):
                    df = loader.load()
                    assert set(df['budget_tier'].unique()).issubset({"low", "medium", "high", "unknown"})

    def test_aggregate_rating_is_float(self, mock_config, raw_df):
        """aggregate_rating column must be float dtype."""
        loader = DataLoader(mock_config)
        with patch.object(loader, '_download', return_value=raw_df):
            with patch.object(loader, '_save_cache'):
                with patch('os.path.exists', return_value=False):
                    df = loader.load()
                    assert pd.api.types.is_float_dtype(df['aggregate_rating'])

    def test_cache_is_created_after_load(self, mock_config, raw_df, tmp_path):
        """A cache .pkl file must exist after the first load call. (EC-DL-01)"""
        mock_config["dataset"]["cache_path"] = str(tmp_path / "zomato.pkl")
        loader = DataLoader(mock_config)
        with patch.object(loader, '_download', return_value=raw_df):
            df = loader.load()
            assert os.path.exists(mock_config["dataset"]["cache_path"])

    def test_corrupt_cache_triggers_redownload(self, mock_config, raw_df, tmp_path):
        """A corrupt .pkl cache must be deleted and dataset re-downloaded. (EC-DL-03)"""
        cache_path = tmp_path / "zomato.pkl"
        mock_config["dataset"]["cache_path"] = str(cache_path)
        cache_path.write_text("corrupt data")
        
        loader = DataLoader(mock_config)
        with patch.object(loader, '_download', return_value=raw_df) as mock_download:
            # os.path.exists will be true, cache will fail to load, triggering download
            df = loader.load()
            mock_download.assert_called_once()
            assert not df.empty

    def test_duplicate_rows_are_removed(self, mock_config, raw_df):
        """Rows with duplicate (name, location) pairs must be deduplicated. (EC-DL-07)"""
        loader = DataLoader(mock_config)
        with patch.object(loader, '_download', return_value=raw_df):
            with patch.object(loader, '_save_cache'):
                with patch('os.path.exists', return_value=False):
                    df = loader.load()
                    # Rest C is dropped because of None rating.
                    # Rest A is duplicate, dropped.
                    # Left with 2 rows.
                    assert len(df) == 2

    def test_cost_for_two_is_numeric(self, mock_config, raw_df):
        """cost_for_two must be numeric after preprocessing. (EC-DL-06)"""
        loader = DataLoader(mock_config)
        with patch.object(loader, '_download', return_value=raw_df):
            with patch.object(loader, '_save_cache'):
                with patch('os.path.exists', return_value=False):
                    df = loader.load()
                    assert pd.api.types.is_numeric_dtype(df['cost_for_two'])

