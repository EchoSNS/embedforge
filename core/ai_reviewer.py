"""
AI Reviewer — automated code review of generated output.

Reviews generated code for correctness, completeness, and adherence
to the SDK's architecture rules before presenting to the user.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from langchain_core.messages import HumanMessage, SystemMessage

from config.llm_config import get_llm
from plugins.base import PluginRegistry

logger = logging.getLogger(__name__)


REVIEW_SYSTEM_PROMPT = """You are a senior embedded systems code reviewer.
Review the generated code for:
1. Correctness — does it implement the requirements?
2. Completeness — are all required functions, ISRs, and init sequences present?
3. SDK compliance — does it follow the SDK's architecture rules and naming conventions?
4. Safety — are there potential runtime issues (null pointer, uninitialized, race conditions)?

Output your review as JSON:
{
  "verdict": "pass" | "needs_fixes",
  "score": 0-100,
  "issues": [{"severity": "error"|"warning"|"info", "location": "file:line", "message": "..."}],
  "summary": "one paragraph summary"
}
"""


@dataclass
class ReviewIssue:
    severity: str
    location: str
    message: str


@dataclass
class ReviewResult:
    verdict: str
    score: int
    issues: List[ReviewIssue] = field(default_factory=list)
    summary: str = ""


class AIReviewer:
    """
    LLM-powered code review of generated files.

    Uses architecture rules and requirements context to evaluate output quality.
    """

    def __init__(self, registry: PluginRegistry, session_id: str = "") -> None:
        self._registry = registry
        self._session_id = session_id

    def review(
        self,
        files: Dict[str, str],
        requirements: str,
        architecture_rules: str = "",
    ) -> ReviewResult:
        """
        Review generated code against requirements and SDK rules.

        Args:
            files: generated source files (filename → content)
            requirements: the original requirement text
            architecture_rules: SDK rules text for compliance checking
        """
        if not architecture_rules:
            rules_pack = self._registry.get_architecture_rules()
            architecture_rules = rules_pack.get_rules_text()

        logger.info("Starting AI review of %d file(s)", len(files))
        file_block = "\n".join(
            f"--- {name} ---\n{content}" for name, content in files.items()
        )

        user_prompt = (
            f"REQUIREMENTS:\n{requirements}\n\n"
            f"SDK RULES:\n{architecture_rules}\n\n"
            f"GENERATED CODE:\n{file_block}\n\n"
            f"Review this code."
        )

        llm = get_llm(session_id=self._session_id, stage="review")

        try:
            response = llm.invoke([
                SystemMessage(content=REVIEW_SYSTEM_PROMPT),
                HumanMessage(content=user_prompt),
            ])
            result = self._parse_review(response.content)
            logger.info("AI review complete: verdict=%s, score=%d, issues=%d", result.verdict, result.score, len(result.issues))
            return result
        except Exception as e:
            logger.error(f"AI review failed: {e}")
            return ReviewResult(verdict="error", score=0, summary=f"Review failed: {e}")

    def _parse_review(self, response: str) -> ReviewResult:
        import json

        try:
            # Extract JSON from response (may be wrapped in markdown)
            json_str = response
            if "```" in response:
                start = response.find("{")
                end = response.rfind("}") + 1
                json_str = response[start:end]

            data = json.loads(json_str)
            issues = [
                ReviewIssue(
                    severity=i.get("severity", "info"),
                    location=i.get("location", ""),
                    message=i.get("message", ""),
                )
                for i in data.get("issues", [])
            ]
            return ReviewResult(
                verdict=data.get("verdict", "needs_fixes"),
                score=data.get("score", 50),
                issues=issues,
                summary=data.get("summary", ""),
            )
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Failed to parse review JSON: {e}")
            return ReviewResult(
                verdict="needs_fixes",
                score=50,
                summary=response[:500],
            )
