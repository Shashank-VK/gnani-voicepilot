"""Tests for Kirana catalog tool, parsing, SafeCalculator order totals, and Hinglish agent responses."""

import pytest

from voicepilot.adapters.stt.mock import MockSTTAdapter
from voicepilot.adapters.tts.mock import MockTTSAdapter
from voicepilot.agent.graph import KIRANA_PERSONA, AgentTurnState, VoicePilotGraph
from voicepilot.agent.tools import KiranaCatalog


def test_catalog_contains_exact_14_items():
    """Verify all 14 required synthetic catalog items exist with positive price and stock."""
    expected_items = {
        "atta": ("kilo", 55, 25),
        "chawal": ("kilo", 65, 30),
        "toor daal": ("kilo", 170, 12),
        "sarso tel": ("litre", 145, 18),
        "chini": ("kilo", 45, 20),
        "namak": ("packet", 28, 40),
        "sabun": ("piece", 35, 60),
        "doodh": ("litre", 56, 10),
        "anda": ("piece", 7, 120),
        "biscuit": ("packet", 25, 50),
        "chai patti": ("packet", 140, 22),
        "masala": ("packet", 60, 30),
        "besan": ("kilo", 70, 15),
        "poha": ("kilo", 48, 18),
    }

    assert len(KiranaCatalog.ITEMS) == 14
    for name, (unit, price, stock) in expected_items.items():
        found = KiranaCatalog.find_item(name)
        assert found is not None, f"Item {name} not found in catalog"
        assert found["name"] == name
        assert found["unit"] == unit
        assert found["price"] == price
        assert found["stock"] == stock


def test_find_item_canonical_and_aliases():
    """Verify lookup by canonical name, Hinglish aliases, and case-insensitivity."""
    # Aliases
    assert KiranaCatalog.find_item("tel")["name"] == "sarso tel"
    assert KiranaCatalog.find_item("oil")["name"] == "sarso tel"
    assert KiranaCatalog.find_item("mustard oil")["name"] == "sarso tel"
    assert KiranaCatalog.find_item("wheat flour")["name"] == "atta"
    assert KiranaCatalog.find_item("eggs")["name"] == "anda"
    assert KiranaCatalog.find_item("daal")["name"] == "toor daal"
    assert KiranaCatalog.find_item("sugar")["name"] == "chini"
    assert KiranaCatalog.find_item("rice")["name"] == "chawal"
    assert KiranaCatalog.find_item("garam masala")["name"] == "masala"
    assert KiranaCatalog.find_item("tea")["name"] == "chai patti"

    # Case insensitivity
    assert KiranaCatalog.find_item("ATTA")["name"] == "atta"
    assert KiranaCatalog.find_item("SaRsO tEl")["name"] == "sarso tel"


def test_find_item_not_found():
    """Non-existent items return None."""
    assert KiranaCatalog.find_item("nonexistent_item") is None
    assert KiranaCatalog.find_item("") is None
    assert KiranaCatalog.find_item(None) is None


def test_catalog_lookup_item_in_stock():
    """Lookup produces Hinglish price and stock availability."""
    lookup_atta = KiranaCatalog.lookup("atta ka daam?")
    assert "₹55" in lookup_atta
    assert "kilo" in lookup_atta
    assert "stock mein hai" in lookup_atta
    assert "25" in lookup_atta

    lookup_doodh = KiranaCatalog.lookup("doodh stock?")
    assert "₹56" in lookup_doodh
    assert "litre" in lookup_doodh
    assert "stock mein hai" in lookup_doodh
    assert "10" in lookup_doodh


def test_catalog_lookup_with_quantity():
    """Lookup mentioning a specific quantity includes the computed subtotal."""
    lookup_res = KiranaCatalog.lookup("Bhaiya, 2 kilo atta kitne ka hai?")
    assert "₹55" in lookup_res
    assert "110" in lookup_res
    assert "stock mein hai" in lookup_res


def test_catalog_lookup_unknown_item():
    """Lookup for items outside catalog yields polite Hinglish message."""
    unknown = KiranaCatalog.lookup("bhaiya chocolate kitne ka hai?")
    assert "catalog mein nahi mila" in unknown.lower() or "nahi mila" in unknown.lower()


def test_parse_order_single_items():
    """parse_order extracts quantity, unit, and item for canonical patterns."""
    lines_atta = KiranaCatalog.parse_order("2 kilo atta")
    assert len(lines_atta) == 1
    assert lines_atta[0][0] == 2
    assert lines_atta[0][1] == "kilo"
    assert lines_atta[0][2]["name"] == "atta"

    lines_tel = KiranaCatalog.parse_order("1 litre tel")
    assert len(lines_tel) == 1
    assert lines_tel[0][0] == 1
    assert lines_tel[0][1] == "litre"
    assert lines_tel[0][2]["name"] == "sarso tel"

    lines_biscuit = KiranaCatalog.parse_order("3 packet biscuit")
    assert len(lines_biscuit) == 1
    assert lines_biscuit[0][0] == 3
    assert lines_biscuit[0][1] == "packet"
    assert lines_biscuit[0][2]["name"] == "biscuit"

    # Digits only, unit optional pattern
    lines_anda = KiranaCatalog.parse_order("2 anda")
    assert len(lines_anda) == 1
    assert lines_anda[0][0] == 2
    assert lines_anda[0][1] == "piece"
    assert lines_anda[0][2]["name"] == "anda"


def test_parse_order_multi_items():
    """parse_order handles multi-item order sentences."""
    lines = KiranaCatalog.parse_order("2 kilo atta aur 1 litre tel le lo, total kitna hua?")
    assert len(lines) == 2
    assert lines[0][0] == 2
    assert lines[0][2]["name"] == "atta"
    assert lines[1][0] == 1
    assert lines[1][2]["name"] == "sarso tel"


def test_parse_order_empty():
    """Non-order text returns empty list."""
    assert KiranaCatalog.parse_order("namaste bhaiya") == []
    assert KiranaCatalog.parse_order("") == []


def test_order_total_safe_calculator():
    """order_total computes line totals via SafeCalculator expression."""
    lines = KiranaCatalog.parse_order("2 kilo atta aur 1 litre tel")
    total = KiranaCatalog.order_total(lines)
    # 2*55 + 1*145 == 255
    assert total == 255.0

    lines_single = KiranaCatalog.parse_order("3 packet biscuit")
    assert KiranaCatalog.order_total(lines_single) == 75.0

    assert KiranaCatalog.order_total([]) == 0.0


def test_kirana_persona_constant():
    """Verify KIRANA_PERSONA constant defines synthetic Hinglish store assistant."""
    assert "kirana" in KIRANA_PERSONA.lower()
    assert "hinglish" in KIRANA_PERSONA.lower()
    assert "₹" in KIRANA_PERSONA
    assert "synthetic" in KIRANA_PERSONA.lower()


@pytest.mark.asyncio
async def test_graph_intent_classification():
    """Verify classification into kirana_order, kirana_lookup, calculation, and general."""
    graph = VoicePilotGraph(MockSTTAdapter(), MockTTSAdapter())

    # Order intent
    turn_order = await graph.node_classify_intent(
        {"raw_transcript": "2 kilo atta aur 1 litre tel le lo"}
    )
    assert turn_order["intent"] == "kirana_order"
    assert turn_order["tool_called"] == "catalog_order"

    turn_order_chahiye = await graph.node_classify_intent({"raw_transcript": "atta chahiye"})
    assert turn_order_chahiye["intent"] == "kirana_order"

    # Lookup intent
    turn_lookup = await graph.node_classify_intent(
        {"raw_transcript": "Bhaiya, 2 kilo atta kitne ka hai?"}
    )
    assert turn_lookup["intent"] == "kirana_lookup"
    assert turn_lookup["tool_called"] == "catalog_lookup"

    turn_stock = await graph.node_classify_intent({"raw_transcript": "Doodh hai kya stock mein?"})
    assert turn_stock["intent"] == "kirana_lookup"
    assert turn_stock["tool_called"] == "catalog_lookup"

    # Calculation intent
    turn_calc = await graph.node_classify_intent({"raw_transcript": "calculate 25 * 4"})
    assert turn_calc["intent"] == "calculation"
    assert turn_calc["tool_called"] == "calculator"

    # General intent
    turn_general = await graph.node_classify_intent({"raw_transcript": "Namaste bhaiya"})
    assert turn_general["intent"] == "general"
    assert turn_general.get("tool_called") is None


@pytest.mark.asyncio
async def test_graph_execute_tool_catalog_order():
    """Verify execute_tool catalog_order returns structured 'lines|total'."""
    graph = VoicePilotGraph(MockSTTAdapter(), MockTTSAdapter())
    state: AgentTurnState = {
        "tool_called": "catalog_order",
        "tool_input": "2 kilo atta aur 1 litre tel le lo",
    }
    res = await graph.node_execute_tool(state)
    tool_result = res["tool_result"]
    assert "|" in tool_result
    lines_part, total_part = tool_result.split("|", 1)
    assert "2 kilo atta @ ₹55 = ₹110" in lines_part
    assert "1 litre tel @ ₹145 = ₹145" in lines_part
    assert total_part == "255"


@pytest.mark.asyncio
async def test_graph_generate_response_order_confirmation():
    """Verify generate_response converts structured tool_result into Hinglish confirmation."""
    graph = VoicePilotGraph(MockSTTAdapter(), MockTTSAdapter())
    state: AgentTurnState = {
        "intent": "kirana_order",
        "tool_called": "catalog_order",
        "tool_result": "2 kilo atta @ ₹55 = ₹110; 1 litre tel @ ₹145 = ₹145|255",
        "raw_transcript": "2 kilo atta aur 1 litre tel le lo",
    }
    res = await graph.node_generate_response(state)
    expected = "Aapka order: 2 kilo atta ₹110 + 1 litre tel ₹145 = kul ₹255. Confirm karun?"
    assert res["response_text"] == expected


@pytest.mark.asyncio
async def test_graph_generate_response_fallback_hinglish():
    """Verify general fallback produces Hinglish kirana dukaan response."""
    graph = VoicePilotGraph(MockSTTAdapter(), MockTTSAdapter())
    state: AgentTurnState = {
        "intent": "general",
        "raw_transcript": "hello",
    }
    res = await graph.node_generate_response(state)
    assert "kirana dukaan" in res["response_text"]
    assert "atta" in res["response_text"]
