"""
LLM Provider abstraction.

Provides a unified interface for:
  - Ollama  (default, local)
  - OpenAI-compatible APIs (via env vars)
  - Demo/mock mode (deterministic responses, no network)

Implementation pending.
"""

import json
import logging
import aiohttp
from typing import TYPE_CHECKING, Any, Dict

if TYPE_CHECKING:
    from app.config import LLMConfig

logger = logging.getLogger(__name__)


class LLMProvider:
    """
    Unified LLM interface.

    In demo mode, returns deterministic canned responses.
    Otherwise delegates to Ollama or OpenAI-compatible endpoints.
    """

    def __init__(self, config: "LLMConfig", demo_mode: bool = True) -> None:
        self.config = config
        self.demo_mode = demo_mode
        logger.info(
            "LLMProvider initialised  provider=%s  demo=%s",
            config.provider,
            demo_mode,
        )

    async def generate(self, prompt: str, system_prompt: str = "") -> str:
        """Generate a text completion."""
        if self.demo_mode:
            return self._mock_generate(prompt, system_prompt)

        return await self._call_real_llm(prompt, system_prompt, structured=False)

    async def generate_structured(
        self, prompt: str, system_prompt: str = ""
    ) -> dict[str, Any]:
        """Generate a structured (JSON) completion."""
        if self.demo_mode:
            result = self._mock_generate_structured(prompt, system_prompt)
            # Ensure we return a dict
            if isinstance(result, str):
                try:
                    return json.loads(result)
                except json.JSONDecodeError:
                    return {}
            return result

        res = await self._call_real_llm(prompt, system_prompt, structured=True)
        try:
            return json.loads(res)
        except json.JSONDecodeError:
            logger.error(f"Failed to parse JSON from LLM: {res}")
            return {}

    def _mock_generate(self, prompt: str, system_prompt: str) -> str:
        combined = (prompt + " " + system_prompt).lower()
        if "product" in combined and "analysis" in combined:
            return "The product is highly competitive in its segment with a strong positive sentiment. Its unique features align well with the target demographic, suggesting a high potential for conversion."
        if "anomalies" in combined or "monitoring" in combined:
            return "No significant anomalies detected. Engagement is steady, though CTR is slightly below optimal on weekends."
        if "segment" in combined:
            return "Young, tech-savvy professionals seeking high-performance products."
        return "Generic deterministic response for demo mode."

    def _mock_generate_structured(self, prompt: str, system_prompt: str) -> dict[str, Any]:
        combined = (prompt + " " + system_prompt).lower()

        # ── Optimization Mock ────────────────────────────────────────────────
        # Keyed on 'specialist' — unique to OptimizationAgent's system_prompt.
        # Must be checked FIRST because metrics.model_dump() contains 'campaign_id'
        # which would otherwise match the campaign generation branch.
        if "specialist" in combined:
            if "iteration: 0" in combined:
                return {
                    "campaign_id": "mock_id",
                    "decision": "optimize",
                    "reason": "Conversion rate is low. Switch to a more urgent CTA.",
                    "suggested_changes": {
                        "cta": "Buy Now and Save!",
                        "subject_line": "Last Chance – 20% Off Today Only!",
                    },
                    "predicted_lift": 0.08,
                    "iteration": 1,
                }
            return {
                "campaign_id": "mock_id",
                "decision": "stop",
                "reason": "Second iteration complete. Accepting current performance.",
                "suggested_changes": {},
                "predicted_lift": 0.0,
                "iteration": 2,
            }

        # ── Campaign Generation Mock ─────────────────────────────────────────
        # Keyed on 'copywriter' — unique to CampaignGenerationAgent's system_prompt.
        if "copywriter" in combined:
            if "optimization feedback" in combined or "buy now" in combined:
                return {
                    "subject_line": "Last Chance – 20% Off Today Only!",
                    "headline": "Urgently Upgrade Your Setup",
                    "body": (
                        "Based on your feedback, we've improved our offer. "
                        "This is your last chance to get 20% off."
                    ),
                    "cta": "Buy Now and Save!",
                    "channel": "email",
                }
            return {
                "subject_line": "Exclusive Offer on Our Top Product!",
                "headline": "Upgrade Your Workflow Today",
                "body": (
                    "Hi there, based on your previous interests, we think you'll love "
                    "our latest offering. It has all the features you need to succeed."
                ),
                "cta": "Shop Now",
                "channel": "email",
            }

        # ── Planner Mock ─────────────────────────────────────────────────────
        if "plan" in combined or "goal" in combined:
            return {
                "goal": {"goal_text": "Mock goal", "budget": 1000.0, "channels": ["email"]},
                "steps": [
                    {"step_name": "Identify Product", "agent": "product_analysis", "description": "Find top product", "depends_on": []},
                    {"step_name": "Segment", "agent": "customer_segmentation", "description": "Find target audience", "depends_on": ["Identify Product"]},
                    {"step_name": "Generate", "agent": "campaign_generation", "description": "Create campaign", "depends_on": ["Segment"]},
                    {"step_name": "Execute", "agent": "execution", "description": "Send campaign", "depends_on": ["Generate"]},
                    {"step_name": "Monitor", "agent": "monitoring", "description": "Check results", "depends_on": ["Execute"]},
                    {"step_name": "Optimize", "agent": "optimization", "description": "Decide next steps", "depends_on": ["Monitor"]},
                ],
            }

        return {}




    async def _call_real_llm(self, prompt: str, system_prompt: str, structured: bool) -> str:
        """Boilerplate for calling Ollama or OpenAI based on config."""
        if self.config.provider == "ollama":
            url = f"{self.config.base_url}/api/generate"
            payload = {
                "model": self.config.model_name,
                "prompt": f"{system_prompt}\n\n{prompt}",
                "stream": False
            }
            if structured:
                payload["format"] = "json"
                
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(url, json=payload) as response:
                        if response.status == 200:
                            data = await response.json()
                            return data.get("response", "")
                        else:
                            logger.error(f"Ollama error: {response.status}")
                            return "{}" if structured else ""
            except Exception as e:
                logger.error(f"Failed to connect to Ollama: {e}")
                return "{}" if structured else ""
        
        elif self.config.provider == "openai":
            # Boilerplate for OpenAI (assuming api_key is in config)
            # In a real scenario, we'd use the openai package
            logger.warning("OpenAI integration requires 'openai' package. Returning empty.")
            return "{}" if structured else ""
            
        return "{}" if structured else ""
