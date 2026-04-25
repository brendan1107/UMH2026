# test_stubs.py
# Run with: python -m app.ai.test.test_stubs

import asyncio, json
from app.ai.schemas import BusinessCase
from app.ai.context_builder import ContextBuilder
from app.ai.memory_manager import MemoryManager
from app.ai.response_parser import ResponseParser


def make_case(num_messages=5) -> BusinessCase:
    """Helper — makes a fake case with N messages."""
    return BusinessCase(
        id="test-001",
        idea="RM15 Nasi Lemak cafe in SS15",
        location="SS15, Subang Jaya",
        budget_myr=30000,
        phase="EVIDENCE",
        fact_sheet={
            "competitor_count": 6,
            "avg_competitor_rating": 4.1,
            "estimated_footfall_lunch": 90,
        },
        messages=[
            {"role": "user", "content": f"message {i}"}
            for i in range(num_messages)
        ],
    )


# ── ContextBuilder tests ────────────────────────────────────

def test_context_builder_short():
    print("── ContextBuilder: short history (no trim) ──")
    case = make_case(num_messages=5)
    cb = ContextBuilder()
    result = cb.build_context(case)
    assert len(result) == 5
    print(f"PASS ✓ — {len(result)} messages kept (no trim needed)\n")


def test_context_builder_long():
    print("── ContextBuilder: long history (should trim to 20) ──")
    case = make_case(num_messages=50)
    cb = ContextBuilder()
    result = cb.build_context(case)
    assert len(result) == 20, f"Expected 20, got {len(result)}"
    assert result[0] == case.messages[0], "First message (brief) should be preserved"
    print(f"PASS ✓ — trimmed 50 → {len(result)} messages, first message preserved\n")


def test_context_truncate_facts():
    print("── ContextBuilder: truncate oversized fact sheet ──")
    cb = ContextBuilder()
    big_facts = {f"fact_{i}": "x" * 100 for i in range(30)}
    context = {"fact_sheet": big_facts}
    result = cb.truncate_context(context, max_tokens=2000)
    fact_str = json.dumps(result["fact_sheet"])
    assert len(fact_str) <= 2000, f"Fact sheet too large: {len(fact_str)} chars"
    print(f"PASS ✓ — fact sheet truncated to {len(fact_str)} chars\n")


# ── MemoryManager tests ─────────────────────────────────────

async def test_memory_summary():
    print("── MemoryManager: summarize_conversation ──")
    case = make_case()
    mm = MemoryManager()
    summary = await mm.summarize_conversation(case)
    assert "SS15" in summary
    assert "competitor_count" in summary
    assert "confirmed_rent_myr" in summary  # should appear as missing
    print(f"PASS ✓ — summary generated:\n{summary}\n")


async def test_memory_get_structured():
    print("── MemoryManager: get_structured_memory ──")
    case = make_case()
    mm = MemoryManager()
    memory = await mm.get_structured_memory(case)
    assert memory["phase"] == "EVIDENCE"
    assert "competitor_count" in memory["facts_collected"]
    assert "confirmed_rent_myr" in memory["facts_missing"]
    print(f"PASS ✓ — structured memory: {json.dumps(memory, indent=2)}\n")


async def test_memory_update():
    print("── MemoryManager: update_memory (no overwrite) ──")
    case = make_case()
    mm = MemoryManager()
    original_rating = case.fact_sheet["avg_competitor_rating"]

    case = await mm.update_memory(case, {
        "avg_competitor_rating": 9.9,   # should NOT overwrite
        "confirmed_rent_myr": 3200,     # should be added
    })
    assert case.fact_sheet["avg_competitor_rating"] == original_rating, "Should not overwrite existing fact"
    assert case.fact_sheet["confirmed_rent_myr"] == 3200, "New fact should be added"
    print(f"PASS ✓ — existing fact protected, new fact added\n")


# ── ResponseParser tests ────────────────────────────────────

def test_parser_clean_json():
    print("── ResponseParser: clean JSON ──")
    rp = ResponseParser()
    raw = '{"type": "verdict", "decision": "GO"}'
    result = rp.parse_ai_response(raw)
    assert result["type"] == "verdict"
    print(f"PASS ✓ — clean JSON parsed\n")


def test_parser_fenced_json():
    print("── ResponseParser: fenced ```json block ──")
    rp = ResponseParser()
    raw = '```json\n{"type": "clarify", "question": "hello?"}\n```'
    result = rp.parse_ai_response(raw)
    assert result["type"] == "clarify"
    print(f"PASS ✓ — fenced JSON stripped and parsed\n")


def test_parser_extract_facts():
    print("── ResponseParser: extract_facts ──")
    rp = ResponseParser()
    parsed = {"extracted_facts": [{"key": "rent", "value": 3200}]}
    facts = rp.extract_facts(parsed)
    assert len(facts) == 1
    assert facts[0]["key"] == "rent"
    print(f"PASS ✓ — facts extracted: {facts}\n")


def test_parser_extract_empty():
    print("── ResponseParser: extract from response with no facts ──")
    rp = ResponseParser()
    parsed = {"type": "clarify"}
    assert rp.extract_facts(parsed) == []
    assert rp.extract_tasks(parsed) == []
    assert rp.extract_recommendation(parsed) is None
    print(f"PASS ✓ — empty extractions handled correctly\n")


# ── Run all ─────────────────────────────────────────────────

if __name__ == "__main__":
    passed = 0
    failed = 0

    sync_tests = [
        test_context_builder_short,
        test_context_builder_long,
        test_context_truncate_facts,
        test_parser_clean_json,
        test_parser_fenced_json,
        test_parser_extract_facts,
        test_parser_extract_empty,
    ]

    async_tests = [
        test_memory_summary,
        test_memory_get_structured,
        test_memory_update,
    ]

    for t in sync_tests:
        try:
            t()
            passed += 1
        except Exception as e:
            print(f"FAIL ✗ — {t.__name__}: {e}\n")
            failed += 1

    for t in async_tests:
        try:
            asyncio.run(t())
            passed += 1
        except Exception as e:
            print(f"FAIL ✗ — {t.__name__}: {e}\n")
            failed += 1

    print(f"Results: {passed}/{passed + failed} passed")