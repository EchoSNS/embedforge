"""Test dynamic cost tracking enhancements."""

import os
import tempfile
import time
from pathlib import Path
from core.cost_tracker import CostTrackingCallback, CostTracker, get_model_pricing
import core.cost_tracker as _ct


def _fresh_tracker():
    _ct._COST_DB_PATH = Path(tempfile.mktemp(suffix=".db"))
    return CostTracker()


def test_pricing_override():
    os.environ["EMBEDFORGE_COST_OVERRIDES"] = '{"custom-model": {"input": 1.0, "output": 2.0}}'
    try:
        pricing = get_model_pricing()
        assert "custom-model" in pricing
        assert pricing["custom-model"]["input"] == 1.0
        assert "gpt-4o" in pricing  # base table still present
        print("Pricing override OK")
    finally:
        del os.environ["EMBEDFORGE_COST_OVERRIDES"]


def test_usage_metadata_path():
    from langchain_core.outputs import LLMResult, ChatGeneration
    from langchain_core.messages import AIMessage

    tracker = _fresh_tracker()

    msg = AIMessage(
        content="test",
        usage_metadata={"input_tokens": 100, "output_tokens": 50, "total_tokens": 150},
        response_metadata={"model_name": "gpt-5"},
    )
    gen = ChatGeneration(message=msg)
    result = LLMResult(generations=[[gen]], llm_output={})

    cb = CostTrackingCallback(session_id="test-meta", stage="test")
    cb._start_time = time.time() - 1.0
    # Temporarily patch the global tracker
    import core.cost_tracker as ct
    original = ct.cost_tracker
    ct.cost_tracker = tracker
    try:
        cb.on_llm_end(result)
    finally:
        ct.cost_tracker = original

    summary = tracker.get_session_summary("test-meta")
    assert summary is not None
    assert summary["total_input_tokens"] == 100
    assert summary["total_output_tokens"] == 50
    assert summary["total_cost_usd"] > 0
    recent = tracker.get_recent_calls(1)
    assert recent[0]["model"] == "gpt-5"
    print(f"Dynamic tracking OK: ${summary['total_cost_usd']}")


def test_llm_output_fallback():
    from langchain_core.outputs import LLMResult, ChatGeneration
    from langchain_core.messages import AIMessage

    tracker = _fresh_tracker()

    # No usage_metadata, only llm_output
    msg = AIMessage(content="test")
    gen = ChatGeneration(message=msg)
    result = LLMResult(
        generations=[[gen]],
        llm_output={
            "token_usage": {"prompt_tokens": 200, "completion_tokens": 80},
            "model_name": "gpt-4o",
        },
    )

    cb = CostTrackingCallback(session_id="test-fallback", stage="review")
    cb._start_time = time.time() - 0.5
    import core.cost_tracker as ct
    original = ct.cost_tracker
    ct.cost_tracker = tracker
    try:
        cb.on_llm_end(result)
    finally:
        ct.cost_tracker = original

    summary = tracker.get_session_summary("test-fallback")
    assert summary["total_input_tokens"] == 200
    assert summary["total_output_tokens"] == 80
    print(f"Fallback path OK: ${summary['total_cost_usd']}")


if __name__ == "__main__":
    test_pricing_override()
    test_usage_metadata_path()
    test_llm_output_fallback()
    print("\nAll dynamic cost tracking tests passed!")
