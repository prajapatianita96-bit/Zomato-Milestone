"""
prompt_builder.py
─────────────────
Responsible for:
  - Converting filtered restaurant records + user preferences into
    a structured, token-safe LLM prompt
  - Enforcing token limits via trimming
  - Framing extra preferences safely to prevent prompt injection

Architecture Reference: architecture.md §2.4
Edge Cases Handled:    edge_cases.md EC-PB-01 to EC-PB-05
"""
import logging
import pandas as pd

logger = logging.getLogger(__name__)


class PromptBuilder:
    """
    Builds structured LLM prompts from filtered restaurant data
    and validated user preferences.

    Usage:
        builder = PromptBuilder(config)
        prompt = builder.build(preferences, filtered_df)
    """

    SYSTEM_ROLE = (
        "You are an expert restaurant recommendation assistant with deep knowledge "
        "of Indian dining. Given a list of restaurants and user preferences, your task "
        "is to recommend the top 3–5 best-matching restaurants. "
        "You MUST respond ONLY with a valid JSON array of objects. Do not include any conversational preamble, markdown formatting (like ```json), or trailing text. "
        "Use this exact schema for each recommendation:\n"
        "[\n"
        "  {{\n"
        '    "name": "Restaurant Name",\n'
        '    "cuisine": "Cuisine Types",\n'
        '    "rating": "Rating value",\n'
        '    "cost": "Cost estimate",\n'
        '    "explanation": "A 2-3 sentence personalized explanation of why it fits."\n'
        "  }}\n"
        "]\n"
        "Respond ONLY in English."
    )

    def __init__(self, config: dict):
        """
        Args:
            config (dict): Parsed config.yaml dictionary.
        """
        self.config = config
        self.prompt_config = config.get("prompt", {})
        self.max_tokens = self.prompt_config.get("max_prompt_tokens", 3000)
        self.token_divisor = self.prompt_config.get("token_estimate_divisor", 4)
        self.max_restaurants = self.prompt_config.get("max_restaurants_in_prompt", 10)

    # ── Public API ────────────────────────────────────────────────

    def build(self, preferences: dict, restaurants: pd.DataFrame) -> str:
        """
        Build the complete LLM prompt string.

        Steps:
          1. Format restaurant list (handle NaN fields — EC-PB-02)
          2. Trim list if token estimate exceeds limit (EC-PB-01)
          3. Frame extra_preferences safely (EC-PB-03)
          4. Assemble system + user prompt

        Args:
            preferences (dict):         Validated UserPreferences dict.
            restaurants (pd.DataFrame): Filtered restaurant records.

        Returns:
            str: Complete, token-safe LLM prompt.
        """
        if restaurants.empty:
            logger.warning("Empty restaurant list passed to PromptBuilder.")
            return ""

        formatted_list = self._format_restaurant_list(restaurants)
        extra = self._frame_extra_preferences(preferences.get("extra_preferences", ""))

        template = (
            f"SYSTEM:\n{self.SYSTEM_ROLE}\n\n"
            f"USER:\n## My Preferences\n"
            f"- Location       : {preferences.get('location', 'N/A')}\n"
            f"- Budget         : {preferences.get('budget', 'N/A')}\n"
            f"- Preferred Cuisine: {preferences.get('cuisine', 'N/A')}\n"
            f"- Minimum Rating : {preferences.get('min_rating', 0.0)} / 5.0\n"
            f"- Extra Preferences: {extra}\n\n"
            f"## Available Restaurants\n{{restaurant_list}}\n\n"
            f"## Instructions\n"
            f"Please rank and recommend the top restaurants from the list above.\n"
            f"Explain briefly why each fits my preferences.\n"
            f"OUTPUT STRICTLY A VALID JSON ARRAY based on the schema in the system prompt. No extra text."
        )

        prompt_with_all = template.format(restaurant_list=formatted_list)

        if self._estimate_tokens(prompt_with_all) > self.max_tokens:
            logger.info("Prompt exceeds token limit. Trimming restaurant list.")
            trimmed_df = self._trim_restaurant_list(restaurants)
            formatted_list = self._format_restaurant_list(trimmed_df)
            prompt_with_all = template.format(restaurant_list=formatted_list)

        return prompt_with_all

    # ── Private Methods ───────────────────────────────────────────

    def _format_restaurant_list(self, df: pd.DataFrame) -> str:
        """
        Format each restaurant record as a numbered text entry.
        Replace NaN/None fields with sensible defaults. (EC-PB-02)

        Args:
            df (pd.DataFrame): Restaurant records to format.

        Returns:
            str: Numbered, human-readable restaurant list.
        """
        entries = []
        for i, row in enumerate(df.itertuples(), 1):
            name = getattr(row, "name", "Unknown") if pd.notna(getattr(row, "name", None)) else "Unknown"
            cuisines = getattr(row, "cuisines", "N/A") if pd.notna(getattr(row, "cuisines", None)) else "N/A"
            rating = getattr(row, "aggregate_rating", 0.0) if pd.notna(getattr(row, "aggregate_rating", None)) else 0.0
            votes = getattr(row, "votes", 0) if pd.notna(getattr(row, "votes", None)) else 0
            cost = getattr(row, "cost_for_two", 0) if pd.notna(getattr(row, "cost_for_two", None)) else 0
            budget_tier = getattr(row, "budget_tier", "N/A") if pd.notna(getattr(row, "budget_tier", None)) else "N/A"
            highlights = getattr(row, "highlights", "N/A") if pd.notna(getattr(row, "highlights", None)) else "N/A"

            entry = (
                f"{i}. {name}\n"
                f"   Cuisine  : {cuisines}\n"
                f"   Rating   : {rating} ⭐ ({votes} votes)\n"
                f"   Cost     : ₹{cost} for two ({budget_tier} budget)\n"
                f"   Tags     : {highlights}"
            )
            entries.append(entry)
        return "\n\n".join(entries)

    def _estimate_tokens(self, text: str) -> int:
        """
        Estimate token count using character length heuristic.
        Formula: len(text) // token_estimate_divisor

        Args:
            text (str): Prompt text to estimate.

        Returns:
            int: Estimated token count.
        """
        return len(text) // self.token_divisor

    def _trim_restaurant_list(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Trim the restaurant list to max_restaurants_in_prompt rows
        when token limit would be exceeded. (EC-PB-01)

        Args:
            df (pd.DataFrame): Full filtered restaurant list.

        Returns:
            pd.DataFrame: Trimmed list sorted by rating DESC.
        """
        if 'aggregate_rating' in df.columns:
            return df.sort_values(by='aggregate_rating', ascending=False).head(self.max_restaurants)
        return df.head(self.max_restaurants)

    def _frame_extra_preferences(self, extra: str) -> str:
        """
        Wrap extra_preferences in a safe delimiter to prevent
        prompt injection. (EC-PB-03)

        Args:
            extra (str): Sanitized extra preferences string.

        Returns:
            str: Safely framed preferences block.
        """
        if not extra or not isinstance(extra, str) or not extra.strip():
            return "None"
        safe_extra = extra.replace("```", "").strip()
        return f"```\n{safe_extra}\n```"
