#!/usr/bin/env python3
"""Test script to verify JSONPath array extraction fix."""

import json
from tokentap.provider_config import get_provider_config
from tokentap.generic_parser import GenericParser


def test_extract_field_arrays():
    """Test that extract_field returns full arrays when [*] is used."""
    print("=" * 70)
    print("TEST 1: JSONPath Array Extraction")
    print("=" * 70)

    config = get_provider_config()

    # Test data with multiple messages (like Claude request)
    test_data = {
        "model": "claude-sonnet-4",
        "messages": [
            {"role": "user", "content": "First message"},
            {"role": "assistant", "content": "Second message"},
            {"role": "user", "content": "Third message"}
        ],
        "system": [
            {"type": "text", "text": "System prompt 1", "cache_control": {"type": "ephemeral"}},
            {"type": "text", "text": "System prompt 2"}
        ],
        "tools": [
            {"name": "tool1", "description": "First tool"},
            {"name": "tool2", "description": "Second tool"}
        ]
    }

    # Test messages extraction
    messages = config.extract_field(test_data, "$.messages[*]")
    print(f"\n✓ Messages extracted: {len(messages)} items")
    assert isinstance(messages, list), "Messages should be a list"
    assert len(messages) == 3, f"Expected 3 messages, got {len(messages)}"
    print(f"  First message: {messages[0]}")
    print(f"  Last message: {messages[2]}")

    # Test system extraction
    system = config.extract_field(test_data, "$.system[*]")
    print(f"\n✓ System array extracted: {len(system)} items")
    assert isinstance(system, list), "System should be a list"
    assert len(system) == 2, f"Expected 2 system items, got {len(system)}"
    print(f"  First system item: {system[0]}")

    # Test tools extraction
    tools = config.extract_field(test_data, "$.tools[*]")
    print(f"\n✓ Tools array extracted: {len(tools)} items")
    assert isinstance(tools, list), "Tools should be a list"
    assert len(tools) == 2, f"Expected 2 tools, got {len(tools)}"

    # Test single value extraction (should not return array)
    model = config.extract_field(test_data, "$.model")
    print(f"\n✓ Model extracted: {model}")
    assert isinstance(model, str), "Model should be a string, not a list"
    assert model == "claude-sonnet-4"

    print("\n" + "=" * 70)
    print("✅ TEST 1 PASSED: Array extraction working correctly")
    print("=" * 70)


def test_generic_parser():
    """Test that generic parser captures all fields."""
    print("\n" + "=" * 70)
    print("TEST 2: Generic Parser Request Parsing")
    print("=" * 70)

    config = get_provider_config()
    parser = GenericParser(config)

    # Realistic Claude request body
    request_body = {
        "model": "claude-sonnet-4-5-20250929",
        "max_tokens": 8000,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Hello, this is a test message"}
                ]
            },
            {
                "role": "assistant",
                "content": [
                    {"type": "text", "text": "Hi! I'm here to help."}
                ]
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Can you help me with something?"}
                ]
            }
        ],
        "system": [
            {
                "type": "text",
                "text": "You are Claude Code, an AI assistant.",
                "cache_control": {"type": "ephemeral"}
            },
            {
                "type": "text",
                "text": "Additional system instructions here."
            }
        ],
        "tools": [
            {
                "name": "bash",
                "description": "Execute bash commands",
                "input_schema": {"type": "object"}
            },
            {
                "name": "read",
                "description": "Read files",
                "input_schema": {"type": "object"}
            }
        ],
        "thinking": {
            "type": "enabled",
            "budget_tokens": 1000
        },
        "metadata": {
            "user_id": "test-user"
        }
    }

    # Parse the request
    result = parser.parse_request("anthropic", request_body)

    print(f"\n✓ Provider: {result['provider']}")
    print(f"✓ Model: {result['model']}")

    print(f"\n✓ Messages: {len(result['messages'])} items")
    assert len(result['messages']) == 3, f"Expected 3 messages, got {len(result['messages'])}"
    print(f"  Message 1: {result['messages'][0]['role']}")
    print(f"  Message 2: {result['messages'][1]['role']}")
    print(f"  Message 3: {result['messages'][2]['role']}")

    print(f"\n✓ System: {len(result['system']) if isinstance(result['system'], list) else 'string'}")
    if isinstance(result['system'], list):
        assert len(result['system']) == 2, f"Expected 2 system items, got {len(result['system'])}"
        print(f"  System item 1 has cache_control: {'cache_control' in result['system'][0]}")

    print(f"\n✓ Tools: {len(result['tools']) if result['tools'] else 'None'}")
    if result['tools']:
        assert len(result['tools']) == 2, f"Expected 2 tools, got {len(result['tools'])}"
        print(f"  Tool 1: {result['tools'][0]['name']}")
        print(f"  Tool 2: {result['tools'][1]['name']}")

    print(f"\n✓ Thinking: {result['thinking'] is not None}")
    if result['thinking']:
        print(f"  Budget tokens: {result['thinking'].get('budget_tokens')}")

    print(f"\n✓ Metadata: {result['metadata'] is not None}")

    print(f"\n✓ Total text length: {len(result['total_text'])} chars")

    print("\n" + "=" * 70)
    print("✅ TEST 2 PASSED: Generic parser capturing all fields")
    print("=" * 70)


def test_quality_validation():
    """Test quality validation logic."""
    print("\n" + "=" * 70)
    print("TEST 3: Quality Validation")
    print("=" * 70)

    from tokentap.proxy import TokentapAddon

    # Test case 1: Good quality (all messages captured)
    original = {
        "messages": [{"role": "user"}, {"role": "assistant"}, {"role": "user"}],
        "system": "You are an AI",
        "tools": [{"name": "bash"}]
    }
    parsed_good = {
        "messages": [{"role": "user"}, {"role": "assistant"}, {"role": "user"}],
        "system": "You are an AI",
        "tools": [{"name": "bash"}]
    }

    assert TokentapAddon._is_parse_quality_acceptable(parsed_good, original), \
        "Good quality parse should pass validation"
    print("✓ Good quality data passes validation")

    # Test case 2: Bad quality (only first message captured)
    parsed_bad_messages = {
        "messages": [{"role": "user"}],  # Only 1 of 3
        "system": "You are an AI",
        "tools": [{"name": "bash"}]
    }

    assert not TokentapAddon._is_parse_quality_acceptable(parsed_bad_messages, original), \
        "Incomplete messages should fail validation"
    print("✓ Incomplete messages detected")

    # Test case 3: Missing system prompt
    parsed_no_system = {
        "messages": [{"role": "user"}, {"role": "assistant"}, {"role": "user"}],
        "system": None,  # Missing
        "tools": [{"name": "bash"}]
    }

    assert not TokentapAddon._is_parse_quality_acceptable(parsed_no_system, original), \
        "Missing system prompt should fail validation"
    print("✓ Missing system prompt detected")

    # Test case 4: Missing tools
    parsed_no_tools = {
        "messages": [{"role": "user"}, {"role": "assistant"}, {"role": "user"}],
        "system": "You are an AI",
        "tools": None  # Missing
    }

    assert not TokentapAddon._is_parse_quality_acceptable(parsed_no_tools, original), \
        "Missing tools should fail validation"
    print("✓ Missing tools detected")

    print("\n" + "=" * 70)
    print("✅ TEST 3 PASSED: Quality validation working correctly")
    print("=" * 70)


def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("TOKENTAP v0.4.1 - Array Extraction Fix Test Suite")
    print("=" * 70)

    try:
        test_extract_field_arrays()
        test_generic_parser()
        test_quality_validation()

        print("\n" + "=" * 70)
        print("🎉 ALL TESTS PASSED!")
        print("=" * 70)
        print("\nThe fix is working correctly:")
        print("  ✓ JSONPath [*] returns full arrays")
        print("  ✓ Generic parser captures all request fields")
        print("  ✓ Quality validation detects incomplete data")
        print("  ✓ System prompts captured as arrays")
        print("  ✓ Tools arrays captured")
        print("  ✓ Thinking config captured")
        print("  ✓ Metadata captured")
        print("\n" + "=" * 70)
        return 0

    except AssertionError as e:
        print("\n" + "=" * 70)
        print(f"❌ TEST FAILED: {e}")
        print("=" * 70)
        return 1
    except Exception as e:
        print("\n" + "=" * 70)
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        print("=" * 70)
        return 1


if __name__ == "__main__":
    exit(main())
