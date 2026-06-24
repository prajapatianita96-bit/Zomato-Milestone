"""
output_renderer.py
──────────────────
Responsible for:
  - Parsing the LLM response and displaying it in a formatted layout
  - Rendering a plain fallback list when LLM is unavailable
  - Gracefully handling empty results, long responses, and terminal issues

Architecture Reference: architecture.md §2.6
Edge Cases Handled:    edge_cases.md EC-OR-01 to EC-OR-04
"""

import logging
import pandas as pd
from typing import Optional

logger = logging.getLogger(__name__)


class OutputRenderer:
    """
    Formats and displays restaurant recommendations to the user.

    Modes:
      1. LLM mode: Display ranked AI-generated recommendations
      2. Fallback mode: Display plain sorted list when LLM unavailable

    Usage:
        renderer = OutputRenderer(config)
        renderer.render(llm_response, fallback_df=filtered_df)
    """

    # Box-drawing characters for rich terminal output
    BOX_TOP    = "╔" + "═" * 58 + "╗"
    BOX_BOTTOM = "╚" + "═" * 58 + "╝"
    BOX_DIV    = "╠" + "═" * 58 + "╣"
    DIVIDER    = "━" * 60

    # Plain-text fallback characters (EC-OR-02)
    PLAIN_DIVIDER = "-" * 60
    PLAIN_HEADER  = "=" * 60

    def __init__(self, config: dict, plain_mode: bool = False):
        """
        Args:
            config     (dict): Parsed config.yaml dictionary.
            plain_mode (bool): If True, disable emoji and box-drawing chars.
                               Use for terminals that don't support Unicode.
        """
        self.config = config
        self.plain_mode = plain_mode
        self.output_config = config.get("output", {})
        self.max_display_chars = self.output_config.get("max_display_chars", 1500)
        self.max_name_length = self.output_config.get("max_restaurant_name_length", 40)
        self.save_path = self.output_config.get("save_response_path", "output/last_response.txt")

    # ── Public API ────────────────────────────────────────────────

    def render(self, llm_response: Optional[str], fallback_df: Optional[pd.DataFrame] = None) -> None:
        """
        Main entry point. Choose rendering mode based on LLM response.

        Logic:
          - If llm_response is valid → render LLM output
          - If llm_response is None/empty → render fallback list
          - If fallback_df also empty → render no-results message (EC-OR-03)

        Args:
            llm_response (Optional[str]):        Raw LLM response text.
            fallback_df  (Optional[DataFrame]):  Filtered restaurants for fallback display.
        """
        if llm_response:
            self._render_llm_output(llm_response)
        else:
            if fallback_df is not None and not fallback_df.empty:
                self._render_fallback(fallback_df)
            else:
                self._render_no_results()

    # ── Private Rendering Methods ─────────────────────────────────

    def _render_llm_output(self, text: str) -> None:
        """
        Display the LLM recommendation response with formatting.

        Parses the JSON array and formats it.
        Saves full response to file.

        Args:
            text (str): Validated LLM response string (JSON format).
        """
        import json
        self._print_header()
        
        # Save raw JSON for reference
        self._save_full_response(text)

        try:
            recommendations = json.loads(text)
            for idx, rec in enumerate(recommendations, start=1):
                name = self._truncate_name(str(rec.get("name", "Unknown")))
                cuisine = str(rec.get("cuisine", "N/A"))
                rating = str(rec.get("rating", "N/A"))
                cost = str(rec.get("cost", "N/A"))
                explanation = str(rec.get("explanation", ""))

                if self.plain_mode:
                    print(f"Recommendation #{idx}")
                    print(self.PLAIN_DIVIDER)
                    print(f"Name      : {name}")
                    print(f"Cuisine   : {cuisine}")
                    print(f"Rating    : {rating}")
                    print(f"Est. Cost : {cost}")
                    print(f"Why?      : {explanation}")
                    print(self.PLAIN_DIVIDER)
                    print()
                else:
                    print(f"🏆 Recommendation #{idx}")
                    print(self.DIVIDER)
                    print(f"🍽️  Name      : {name}")
                    print(f"🍜  Cuisine   : {cuisine}")
                    print(f"⭐  Rating    : {rating}")
                    print(f"💰  Est. Cost : {cost}")
                    print(f"🤖  Why?      : {explanation}")
                    print(self.DIVIDER)
                    print()
                    
            if not recommendations:
                print("No recommendations returned by AI.")
                
        except Exception as e:
            logger.error(f"Failed to render JSON response: {e}")
            print(text)

    def _render_fallback(self, df: pd.DataFrame) -> None:
        """
        Display a plain, sorted list of restaurants when LLM is unavailable.
        Shows top 5 by aggregate_rating with key fields.

        Args:
            df (pd.DataFrame): Filtered restaurant DataFrame.
        """
        self._print_header()
        
        top_5 = df.sort_values(by="aggregate_rating", ascending=False).head(5)
        
        print("⚠️ LLM unavailable. Showing top recommendations based on raw ratings:\n")
        
        for idx, row in enumerate(top_5.itertuples(), start=1):
            name = self._truncate_name(str(row.name))
            rating = f"{row.aggregate_rating:.1f} / 5.0"
            cost = f"₹{row.cost_for_two} for two"
            cuisine = str(row.cuisines)
            
            if self.plain_mode:
                print(f"Recommendation #{idx}")
                print(self.PLAIN_DIVIDER)
                print(f"Name      : {name}")
                print(f"Cuisine   : {cuisine}")
                print(f"Rating    : {rating}")
                print(f"Est. Cost : {cost}")
                print(self.PLAIN_DIVIDER)
                print()
            else:
                print(f"🏆 Recommendation #{idx}")
                print(self.DIVIDER)
                print(f"🍽️  Name      : {name}")
                print(f"🍜  Cuisine   : {cuisine}")
                print(f"⭐  Rating    : {rating}")
                print(f"💰  Est. Cost : {cost}")
                print(self.DIVIDER)
                print()

    def _render_no_results(self) -> None:
        """
        Display a helpful message when no restaurants are found. (EC-OR-03)
        """
        self._print_header()
        if self.plain_mode:
            print("No restaurants matched your exact criteria.")
            print("Try broadening your budget or cuisine preferences.")
        else:
            print("❌ No restaurants matched your exact criteria.")
            print("💡 Try broadening your budget or cuisine preferences.")
        
        print(self.PLAIN_DIVIDER if self.plain_mode else self.DIVIDER)

    def _print_header(self) -> None:
        """Print the application banner / title header."""
        print()
        if self.plain_mode:
            print(self.PLAIN_HEADER)
            print("ZOMATO AI RESTAURANT RECOMMENDATIONS".center(60))
            print(self.PLAIN_HEADER)
        else:
            print(self.BOX_TOP)
            print("║" + "🍽️  ZOMATO AI RESTAURANT RECOMMENDATIONS".center(56) + "║")
            print(self.BOX_BOTTOM)
        print()

    def _truncate_name(self, name: str) -> str:
        """
        Truncate long restaurant names for display. (EC-OR-04)

        Args:
            name (str): Full restaurant name.

        Returns:
            str: Truncated name with ellipsis if needed.
        """
        if len(name) > self.max_name_length:
            return name[:self.max_name_length - 3] + "..."
        return name

    def _truncate_response(self, text: str) -> str:
        """
        Truncate LLM response beyond max_display_chars. (EC-OR-01)

        Args:
            text (str): Full LLM response.

        Returns:
            str: Truncated text with trail notice if applicable.
        """
        if len(text) > self.max_display_chars:
            self._save_full_response(text)
            return text[:self.max_display_chars] + f"\n\n... [Response truncated. Full output saved to {self.save_path}]"
        return text

    def _save_full_response(self, text: str) -> None:
        """
        Save the full LLM response to a file for reference. (EC-OR-01 fallback)

        Args:
            text (str): Full untruncated LLM response.
        """
        import os
        try:
            os.makedirs(os.path.dirname(self.save_path) or '.', exist_ok=True)
            with open(self.save_path, "w", encoding="utf-8") as f:
                f.write(text)
        except Exception as e:
            logger.warning(f"Failed to save full response to {self.save_path}: {e}")
