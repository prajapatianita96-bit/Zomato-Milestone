"""
tests/test_prompt_builder.py
────────────────────────────
Unit tests for the PromptBuilder component.

To be implemented fully in Phase 4.
These are placeholder stubs defining the test contract.

Run with:
    pytest tests/test_prompt_builder.py -v
"""

import pytest
import pandas as pd
from src.prompt_builder import PromptBuilder

class TestPromptBuilder:
    """Unit tests for src/prompt_builder.py — PromptBuilder class."""

    @pytest.fixture
    def builder(self):
        config = {
            "prompt": {
                "max_prompt_tokens": 3000,
                "token_estimate_divisor": 4,
                "max_restaurants_in_prompt": 10
            }
        }
        return PromptBuilder(config)

    @pytest.fixture
    def sample_preferences(self):
        return {
            "location": "delhi",
            "budget": "medium",
            "cuisine": "north indian",
            "min_rating": 4.0,
            "extra_preferences": "family friendly"
        }

    @pytest.fixture
    def sample_restaurants(self):
        data = {
            "name": ["Spice Garden", "Curry House"],
            "location": ["delhi", "delhi"],
            "cuisines": ["North Indian", "North Indian, Mughlai"],
            "aggregate_rating": [4.5, 4.2],
            "votes": [100, 50],
            "cost_for_two": [800, 1000],
            "budget_tier": ["medium", "medium"],
            "highlights": ["Family Friendly", "Live Music"]
        }
        return pd.DataFrame(data)

    def test_prompt_is_non_empty_string(self, builder, sample_preferences, sample_restaurants):
        """build() must return a non-empty string."""
        prompt = builder.build(sample_preferences, sample_restaurants)
        assert isinstance(prompt, str)
        assert len(prompt) > 0

    def test_prompt_contains_location(self, builder, sample_preferences, sample_restaurants):
        """Prompt must include the user's location."""
        prompt = builder.build(sample_preferences, sample_restaurants)
        assert "delhi" in prompt

    def test_prompt_contains_budget(self, builder, sample_preferences, sample_restaurants):
        """Prompt must include the user's budget tier."""
        prompt = builder.build(sample_preferences, sample_restaurants)
        assert "medium" in prompt

    def test_prompt_contains_cuisine(self, builder, sample_preferences, sample_restaurants):
        """Prompt must include the user's preferred cuisine."""
        prompt = builder.build(sample_preferences, sample_restaurants)
        assert "north indian" in prompt

    def test_prompt_contains_min_rating(self, builder, sample_preferences, sample_restaurants):
        """Prompt must include the user's minimum rating threshold."""
        prompt = builder.build(sample_preferences, sample_restaurants)
        assert "4.0" in prompt

    def test_prompt_contains_restaurant_names(self, builder, sample_preferences, sample_restaurants):
        """Prompt must include restaurant names from the filtered list."""
        prompt = builder.build(sample_preferences, sample_restaurants)
        assert "Spice Garden" in prompt
        assert "Curry House" in prompt

    def test_nan_fields_replaced_with_defaults(self, builder, sample_preferences):
        """NaN values in restaurant fields must be replaced with 'N/A' or '0'. (EC-PB-02)"""
        bad_data = {
            "name": [None],
            "location": ["delhi"],
            "cuisines": [None],
            "aggregate_rating": [None],
            "votes": [None],
            "cost_for_two": [None],
            "budget_tier": [None],
            "highlights": [None]
        }
        df = pd.DataFrame(bad_data)
        prompt = builder.build(sample_preferences, df)
        assert "Unknown" in prompt
        assert "N/A" in prompt
        assert "0.0 ⭐" in prompt

    def test_token_trimming_activates_on_large_input(self, builder, sample_preferences):
        """Restaurant list must be trimmed when estimated tokens > max_prompt_tokens. (EC-PB-01)"""
        builder.max_tokens = 10
        builder.max_restaurants = 2
        
        data = {
            "name": [f"Restaurant {i}" for i in range(10)],
            "aggregate_rating": [4.0 + (i*0.1) for i in range(10)]
        }
        df = pd.DataFrame(data)
        prompt = builder.build(sample_preferences, df)
        assert "Restaurant 9" in prompt
        assert "Restaurant 8" in prompt
        assert "Restaurant 1" not in prompt

    def test_extra_preferences_are_framed_safely(self, builder, sample_preferences, sample_restaurants):
        """Extra preferences must be wrapped in a safe delimiter block. (EC-PB-03)"""
        prompt = builder.build(sample_preferences, sample_restaurants)
        assert "```\nfamily friendly\n```" in prompt
        
        sample_preferences["extra_preferences"] = "```malicious```"
        prompt2 = builder.build(sample_preferences, sample_restaurants)
        assert "```malicious```" not in prompt2
        assert "malicious" in prompt2

    def test_prompt_contains_system_role(self, builder, sample_preferences, sample_restaurants):
        """Prompt must include the system role / expert persona instruction."""
        prompt = builder.build(sample_preferences, sample_restaurants)
        assert "SYSTEM:" in prompt
        assert builder.SYSTEM_ROLE in prompt
