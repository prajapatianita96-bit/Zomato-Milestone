"""
filter_engine.py
────────────────
Responsible for:
  - Querying the cleaned DataFrame based on validated user preferences
  - Applying progressive constraint relaxation when results are sparse
  - Capping result set size before passing to PromptBuilder

Architecture Reference: architecture.md §2.3
Edge Cases Handled:    edge_cases.md EC-FE-01 to EC-FE-06
"""

import logging
import pandas as pd

logger = logging.getLogger(__name__)


class FilterEngine:
    """
    Filters the restaurant DataFrame based on user preferences.
    Implements progressive fallback relaxation when strict filters
    return too few results.

    Usage:
        engine = FilterEngine(df, config)
        filtered_df = engine.filter(preferences)
    """

    def __init__(self, df: pd.DataFrame, config: dict):
        """
        Args:
            df     (pd.DataFrame): Cleaned dataset from DataLoader.
            config (dict):         Parsed config.yaml dictionary.
        """
        self.df = df
        self.config = config
        self.dataset_config = config.get("dataset", {})
        self.max_results = self.dataset_config.get("max_filter_results", 20)
        self.min_threshold = self.dataset_config.get("min_result_threshold", 5)

    # ── Public API ────────────────────────────────────────────────


    def filter(self, preferences: dict) -> pd.DataFrame:
        """
        Main entry point. Filters the dataset using strict → relaxed logic.

        Relaxation sequence (EC-FE-01):
          1. Strict: all 4 filters applied
          2. Relax budget if results < min_threshold
          3. Relax cuisine if still < min_threshold
          4. Lower min_rating by 0.5 if still < min_threshold
          5. Return top results for location only

        Args:
            preferences (dict): Validated UserPreferences dict from InputHandler.

        Returns:
            pd.DataFrame: Filtered and sorted restaurant records (max 20 rows).
        """
        # Step 1: Strict
        df_filtered = self._apply_strict_filter(preferences)
        if len(df_filtered) >= self.min_threshold:
            return self._sort_and_cap(df_filtered)
            
        # Step 2: Relax budget
        self._log_relaxation("Relaxed budget filter")
        df_filtered = self._apply_relaxed_filter(preferences, relax_budget=True)
        if len(df_filtered) >= self.min_threshold:
            return self._sort_and_cap(df_filtered)
            
        # Step 3: Relax cuisine
        self._log_relaxation("Relaxed cuisine filter")
        df_filtered = self._apply_relaxed_filter(preferences, relax_budget=True, relax_cuisine=True)
        if len(df_filtered) >= self.min_threshold:
            return self._sort_and_cap(df_filtered)
            
        # Step 4: Lower min_rating
        self._log_relaxation("Lowered minimum rating by 0.5")
        df_filtered = self._apply_relaxed_filter(preferences, relax_budget=True, relax_cuisine=True, rating_offset=0.5)
        
        # Step 5: Always return what we have
        return self._sort_and_cap(df_filtered)

    # ── Private Filter Methods ────────────────────────────────────

    def _apply_strict_filter(self, preferences: dict) -> pd.DataFrame:
        """
        Apply all 4 constraints simultaneously.

        Filters:
          - location CONTAINS preferences["location"] (case-insensitive)
          - budget_tier == preferences["budget"]
          - cuisines CONTAINS preferences["cuisine"]
          - aggregate_rating >= preferences["min_rating"]

        Args:
            preferences (dict): Validated user preferences.

        Returns:
            pd.DataFrame: Strictly filtered results.
        """
        return self._apply_relaxed_filter(preferences)

    def _apply_relaxed_filter(
        self,
        preferences: dict,
        relax_budget: bool = False,
        relax_cuisine: bool = False,
        rating_offset: float = 0.0,
    ) -> pd.DataFrame:
        """
        Apply filters with one or more constraints relaxed.

        Args:
            preferences    (dict):  Validated user preferences.
            relax_budget   (bool):  Skip budget_tier filter if True.
            relax_cuisine  (bool):  Skip cuisine filter if True.
            rating_offset  (float): Subtract this from min_rating threshold.

        Returns:
            pd.DataFrame: Relaxed filtered results.
        """
        df_filtered = self.df.copy()
        
        # Location (always applied)
        if preferences.get("location"):
            df_filtered = df_filtered[df_filtered["location"].str.contains(preferences["location"], case=False, na=False)]
            
        # Budget
        if not relax_budget and preferences.get("budget"):
            df_filtered = df_filtered[df_filtered["budget_tier"] == preferences["budget"]]
            
        # Cuisine
        if not relax_cuisine and preferences.get("cuisine") and preferences.get("cuisine") != "any":
            df_filtered = df_filtered[df_filtered["cuisines"].str.contains(preferences["cuisine"], case=False, na=False)]
            
        # Rating
        min_rating = max(0.0, preferences.get("min_rating", 0.0) - rating_offset)
        df_filtered = df_filtered[df_filtered["aggregate_rating"] >= min_rating]
        
        return df_filtered

    def _sort_and_cap(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Sort by aggregate_rating DESC, votes DESC and cap at max_results.
        Handles EC-FE-04 (too many results).

        Args:
            df (pd.DataFrame): Filtered DataFrame.

        Returns:
            pd.DataFrame: Sorted and capped DataFrame.
        """
        if df.empty:
            return df
            
        sorted_df = df.sort_values(by=["aggregate_rating", "votes"], ascending=[False, False])
        return sorted_df.head(self.max_results)

    def _log_relaxation(self, step: str) -> None:
        """
        Log which constraint was relaxed for observability.

        Args:
            step (str): Description of the relaxation applied.
        """
        logger.info(f"Fallback triggered: {step} to find more results.")
