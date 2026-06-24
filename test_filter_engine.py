"""
tests/test_filter_engine.py
───────────────────────────
Unit tests for the FilterEngine component.

Run with:
    pytest tests/test_filter_engine.py -v
"""

import pytest
import pandas as pd
from src.filter_engine import FilterEngine

@pytest.fixture
def mock_config():
    return {
        "dataset": {
            "max_filter_results": 3,
            "min_result_threshold": 2
        }
    }

@pytest.fixture
def sample_df():
    return pd.DataFrame({
        "name": ["R1", "R2", "R3", "R4", "R5"],
        "location": ["delhi", "delhi", "delhi", "mumbai", "delhi"],
        "cuisines": ["north indian", "north indian", "chinese", "north indian", "italian"],
        "budget_tier": ["medium", "high", "medium", "medium", "medium"],
        "aggregate_rating": [4.5, 4.6, 4.0, 4.2, 3.5],
        "votes": [100, 200, 50, 300, 10]
    })

class TestFilterEngine:
    """Unit tests for src/filter_engine.py — FilterEngine class."""

    def test_strict_filter_returns_correct_results(self, mock_config, sample_df):
        """Strict filter returns only restaurants matching all 4 criteria."""
        engine = FilterEngine(sample_df, mock_config)
        prefs = {"location": "delhi", "budget": "medium", "cuisine": "north indian", "min_rating": 4.0}
        
        # We need min_threshold=1 to prevent fallback since we only have 1 match
        engine.min_threshold = 1
        df = engine.filter(prefs)
        
        assert len(df) == 1
        assert df.iloc[0]["name"] == "R1"

    def test_results_capped_at_max(self, mock_config, sample_df):
        """Result set must not exceed max_filter_results. (EC-FE-04)"""
        engine = FilterEngine(sample_df, mock_config)
        engine.max_results = 2
        engine.min_threshold = 1
        prefs = {"location": "delhi", "budget": "medium", "cuisine": "any", "min_rating": 3.0}
        df = engine.filter(prefs)
        
        assert len(df) == 2

    def test_budget_relaxation_triggers_when_few_results(self, mock_config, sample_df):
        """Budget filter must be dropped when results < min_threshold. (EC-FE-01)"""
        engine = FilterEngine(sample_df, mock_config)
        # 1 match for medium + north indian, but min_threshold=2
        prefs = {"location": "delhi", "budget": "medium", "cuisine": "north indian", "min_rating": 4.0}
        df = engine.filter(prefs)
        
        assert len(df) == 2
        # R1 (medium) and R2 (high) should both be included due to relaxed budget
        names = df["name"].tolist()
        assert "R1" in names and "R2" in names

    def test_cuisine_relaxation_triggers_when_still_few_results(self, mock_config, sample_df):
        """Cuisine filter must be dropped after budget relaxation fails. (EC-FE-01)"""
        engine = FilterEngine(sample_df, mock_config)
        engine.min_threshold = 3
        # Strict: 1 match. Relax budget: 2 matches. Still < 3. Relax cuisine: R3 is added.
        prefs = {"location": "delhi", "budget": "medium", "cuisine": "north indian", "min_rating": 4.0}
        df = engine.filter(prefs)
        
        assert len(df) == 3
        names = df["name"].tolist()
        assert "R3" in names

    def test_empty_result_for_unknown_location(self, mock_config, sample_df):
        """Filter must return an empty DataFrame for a location not in dataset. (EC-FE-01)"""
        engine = FilterEngine(sample_df, mock_config)
        prefs = {"location": "chennai", "budget": "medium", "cuisine": "north indian", "min_rating": 4.0}
        df = engine.filter(prefs)
        
        assert df.empty

    def test_results_sorted_by_rating_desc(self, mock_config, sample_df):
        """Results must be sorted by aggregate_rating descending, then votes descending."""
        engine = FilterEngine(sample_df, mock_config)
        engine.min_threshold = 1
        prefs = {"location": "delhi", "budget": "medium", "cuisine": "any", "min_rating": 3.0}
        df = engine.filter(prefs)
        
        ratings = df["aggregate_rating"].tolist()
        assert ratings == sorted(ratings, reverse=True)

    def test_cuisine_any_skips_cuisine_filter(self, mock_config, sample_df):
        """If cuisine='any', cuisine filter must not be applied. (EC-IH-06)"""
        engine = FilterEngine(sample_df, mock_config)
        engine.min_threshold = 1
        prefs = {"location": "delhi", "budget": "medium", "cuisine": "any", "min_rating": 3.0}
        df = engine.filter(prefs)
        
        # R1, R3, R5 are all medium budget in delhi
        assert len(df) == 3

    def test_single_result_handled_gracefully(self, mock_config, sample_df):
        """Filter must handle a single result without crashing. (EC-FE-03)"""
        engine = FilterEngine(sample_df, mock_config)
        # Add a unique restaurant
        df_new = pd.concat([sample_df, pd.DataFrame({"name": ["Unique"], "location": ["delhi"], "cuisines": ["unique"], "budget_tier": ["low"], "aggregate_rating": [5.0], "votes": [1]})])
        engine.df = df_new
        engine.min_threshold = 1
        prefs = {"location": "delhi", "budget": "low", "cuisine": "unique", "min_rating": 4.0}
        df = engine.filter(prefs)
        
        assert len(df) == 1
        assert df.iloc[0]["name"] == "Unique"

