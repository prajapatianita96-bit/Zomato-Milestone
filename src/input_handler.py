"""
input_handler.py
────────────────
Responsible for:
  - Collecting user preferences via CLI prompts or programmatic args
  - Validating and normalizing each preference field
  - Producing a standardized UserPreferences dict for downstream use

Architecture Reference: architecture.md §2.2
Edge Cases Handled:    edge_cases.md EC-IH-01 to EC-IH-07
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class InputValidationError(Exception):
    """Raised when user input cannot be resolved to a valid value."""
    pass


class InputHandler:
    """
    Collects, validates, and normalizes user restaurant preferences.

    Usage:
        handler = InputHandler(valid_locations, valid_cuisines, config)
        preferences = handler.collect_from_cli()
        # or
        preferences = handler.collect_from_args(
            location="Delhi", budget="medium",
            cuisine="north indian", min_rating=4.0
        )
    """

    # EC-IH-03: Budget synonym normalization map
    BUDGET_SYNONYMS = {
        "cheap": "low", "affordable": "low", "budget": "low",
        "inexpensive": "low", "economy": "low",
        "moderate": "medium", "mid": "medium", "average": "medium",
        "standard": "medium", "mid-range": "medium",
        "expensive": "high", "luxury": "high", "premium": "high",
        "fine dining": "high", "upscale": "high",
    }

    VALID_BUDGETS = {"low", "medium", "high"}

    def __init__(self, valid_locations: list, valid_cuisines: list, config: dict):
        """
        Args:
            valid_locations (list): All known location values from the dataset.
            valid_cuisines  (list): All known cuisine values from the dataset.
            config          (dict): Parsed config.yaml dictionary.
        """
        self.valid_locations = [loc.lower() for loc in valid_locations]
        self.valid_cuisines = [c.lower() for c in valid_cuisines]
        self.config = config
        self.input_config = config.get("input", {})

    # ── Public API ────────────────────────────────────────────────

    def collect_from_cli(self) -> dict:
        """
        Interactively prompt the user via CLI for all preference fields.

        Returns:
            dict: Validated UserPreferences dict.
        """
        print("\n--- Enter Your Preferences ---")
        location = input("Location (e.g. Delhi): ").strip()
        budget = input("Budget (low/medium/high): ").strip()
        cuisine = input("Preferred Cuisine (or 'any'): ").strip()
        
        min_rating_str = input("Minimum Rating (0.0 to 5.0, default 3.0): ").strip()
        try:
            min_rating = float(min_rating_str) if min_rating_str else self.input_config.get("default_rating", 3.0)
        except ValueError:
            min_rating = self.input_config.get("default_rating", 3.0)
            
        extra = input("Any other preferences? (e.g. family-friendly): ").strip()
        
        return self.collect_from_args(
            location=location,
            budget=budget,
            cuisine=cuisine,
            min_rating=min_rating,
            extra_preferences=extra
        )

    def collect_from_args(
        self,
        location: str,
        budget: str,
        cuisine: str,
        min_rating: float,
        extra_preferences: Optional[str] = "",
    ) -> dict:
        """
        Accept preferences programmatically (for testing / API use).

        Args:
            location           (str):   City name.
            budget             (str):   "low", "medium", or "high" (or synonyms).
            cuisine            (str):   Cuisine type, or "any".
            min_rating         (float): Minimum acceptable rating (0.0 – 5.0).
            extra_preferences  (str):   Free-text additional preferences.

        Returns:
            dict: Validated UserPreferences dict.
        """
        raw_prefs = {
            "location": location,
            "budget": budget,
            "cuisine": cuisine,
            "min_rating": min_rating,
            "extra_preferences": extra_preferences
        }
        return self.validate(raw_prefs)

    def validate(self, preferences: dict) -> dict:
        """
        Validate and normalize a raw preferences dict.

        Applies:
          - EC-IH-01: Empty input guard
          - EC-IH-02: Fuzzy location matching
          - EC-IH-03: Budget synonym normalization
          - EC-IH-04: Rating clamping
          - EC-IH-05: Special character sanitization
          - EC-IH-06: cuisine="any" passthrough
          - EC-IH-07: extra_preferences length truncation

        Args:
            preferences (dict): Raw user input dict.

        Returns:
            dict: Cleaned and validated UserPreferences dict.
        """
        if not preferences:
            raise InputValidationError("Preferences cannot be empty.")
            
        return {
            "location": self._validate_location(preferences.get("location", "")),
            "budget": self._validate_budget(preferences.get("budget", "")),
            "cuisine": self._validate_cuisine(preferences.get("cuisine", "")),
            "min_rating": self._validate_rating(preferences.get("min_rating", self.input_config.get("default_rating", 3.0))),
            "extra_preferences": self._sanitize_text(preferences.get("extra_preferences", ""))
        }

    # ── Private Validators ────────────────────────────────────────

    def _validate_location(self, location: str) -> str:
        """
        Fuzzy-match location against known dataset locations. (EC-IH-02)

        Args:
            location (str): Raw user-provided location.

        Returns:
            str: Best-matched location string (lowercase).

        Raises:
            InputValidationError: If no close match found.
        """
        if not location:
            raise InputValidationError("Location is required.")
            
        location_clean = location.lower().strip()
        
        if location_clean in self.valid_locations:
            return location_clean
            
        import difflib
        cutoff = self.input_config.get("fuzzy_match_cutoff", 0.6)
        matches = difflib.get_close_matches(location_clean, self.valid_locations, n=1, cutoff=cutoff)
        
        if matches:
            return matches[0]
            
        for valid_loc in self.valid_locations:
            if location_clean in valid_loc or valid_loc in location_clean:
                return valid_loc
                
        raise InputValidationError(f"Location '{location}' not found in dataset.")

    def _validate_budget(self, budget: str) -> str:
        """
        Normalize budget string to low/medium/high. (EC-IH-03)

        Args:
            budget (str): Raw budget input.

        Returns:
            str: One of "low", "medium", "high".
        """
        budget_clean = budget.lower().strip()
        if not budget_clean:
            return self.input_config.get("default_budget", "medium")
            
        if budget_clean in self.VALID_BUDGETS:
            return budget_clean
            
        synonym_match = self.BUDGET_SYNONYMS.get(budget_clean)
        if synonym_match:
            return synonym_match
            
        raise InputValidationError(f"Invalid budget '{budget}'. Expected low, medium, or high.")

    def _validate_cuisine(self, cuisine: str) -> str:
        """
        Fuzzy-match cuisine against known dataset cuisines.
        Returns "any" if user provides no preference. (EC-IH-06)

        Args:
            cuisine (str): Raw cuisine input.

        Returns:
            str: Matched cuisine string or "any".
        """
        if not cuisine:
            return "any"
            
        cuisine_clean = cuisine.lower().strip()
        if cuisine_clean == "any":
            return "any"
            
        for valid_c in self.valid_cuisines:
            if cuisine_clean in valid_c:
                return cuisine_clean
                
        import difflib
        cutoff = self.input_config.get("fuzzy_match_cutoff", 0.6)
        matches = difflib.get_close_matches(cuisine_clean, self.valid_cuisines, n=1, cutoff=cutoff)
        
        if matches:
            return matches[0]
            
        return cuisine_clean

    def _validate_rating(self, rating) -> float:
        """
        Cast and clamp rating to [0.0, 5.0]. (EC-IH-04)

        Args:
            rating: Raw rating input (may be str or float).

        Returns:
            float: Clamped rating value.
        """
        try:
            r = float(rating)
            return max(0.0, min(r, 5.0))
        except (ValueError, TypeError):
            return self.input_config.get("default_rating", 3.0)

    def _sanitize_text(self, text: str, max_length: int = 200) -> str:
        """
        Strip dangerous/unexpected characters and truncate. (EC-IH-05, EC-IH-07)

        Args:
            text       (str): Raw free-text input.
            max_length (int): Maximum allowed character count.

        Returns:
            str: Sanitized and truncated string.
        """
        if not text:
            return ""
        
        import re
        sanitized = re.sub(r'[^\w\s\.,;!?-]', '', str(text)).strip()
        max_len = self.input_config.get("max_extra_preferences_length", max_length)
        return sanitized[:max_len]
