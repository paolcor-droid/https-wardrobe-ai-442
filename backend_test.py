#!/usr/bin/env python3
"""
Backend verification test for StyleScan/LUMIÈRE - Run 3
Tests preferences persistence and stylist profile context usage.
VERIFICATION ONLY - NO CODE CHANGES
"""
import json
import requests
import sys
from typing import Dict, Any, List

# Base URL from frontend/.env
BASE_URL = "https://stylescan-v3.preview.emergentagent.com/api"

def test_b_preferences_persistence():
    """
    TEST B: Preferences persistence + reload + mutual-exclusion
    """
    print("\n" + "="*80)
    print("TEST B: Preferences Persistence + Reload + Mutual-Exclusion")
    print("="*80)
    
    # Step 1: PUT /api/profile with full preferences
    profile_data = {
        "favorite_colors": ["navy", "white"],
        "styles": ["minimal"],
        "sizes": {"top": "M", "bottom": "32", "shoe": "9"},
        "budget": "$$",
        "notes": "warm climate, natural fabrics",
        "preferences": {
            "budget_min": 50,
            "budget_max": 250,
            "occasion": "work",
            "categories": ["tops"],
            "climate": "hot",
            "style": "minimal",
            "preferred_fit": "relaxed",
            "preferred_colours": ["navy", "olive"],
            "avoided_colours": ["black"],
            "preferred_retailers": ["zara", "uniqlo", "romanelli-b2b"]
        }
    }
    
    print("\n1. PUT /api/profile with full preferences...")
    try:
        resp = requests.put(f"{BASE_URL}/profile", json=profile_data, timeout=30)
        print(f"   Status: {resp.status_code}")
        
        if resp.status_code != 200:
            print(f"   ❌ FAIL: Expected 200, got {resp.status_code}")
            print(f"   Response: {resp.text}")
            return False
        
        print("   ✅ PUT returned 200 (not 500)")
    except Exception as e:
        print(f"   ❌ FAIL: Exception during PUT: {e}")
        return False
    
    # Step 2: GET /api/profile (first time)
    print("\n2. GET /api/profile (first fetch)...")
    try:
        resp1 = requests.get(f"{BASE_URL}/profile", timeout=30)
        if resp1.status_code != 200:
            print(f"   ❌ FAIL: GET returned {resp1.status_code}")
            return False
        profile1 = resp1.json()
        print("   ✅ First GET successful")
    except Exception as e:
        print(f"   ❌ FAIL: Exception during first GET: {e}")
        return False
    
    # Step 3: GET /api/profile (second time - simulated reload)
    print("\n3. GET /api/profile (second fetch - simulated reload)...")
    try:
        resp2 = requests.get(f"{BASE_URL}/profile", timeout=30)
        if resp2.status_code != 200:
            print(f"   ❌ FAIL: Second GET returned {resp2.status_code}")
            return False
        profile2 = resp2.json()
        print("   ✅ Second GET successful")
    except Exception as e:
        print(f"   ❌ FAIL: Exception during second GET: {e}")
        return False
    
    # Step 4: Verify both responses are identical
    print("\n4. Verifying both responses are identical...")
    # Remove updated_at for comparison as it might differ slightly
    p1_copy = {k: v for k, v in profile1.items() if k != "updated_at"}
    p2_copy = {k: v for k, v in profile2.items() if k != "updated_at"}
    
    if p1_copy != p2_copy:
        print("   ❌ FAIL: Responses differ between first and second GET")
        print(f"   First: {json.dumps(p1_copy, indent=2)}")
        print(f"   Second: {json.dumps(p2_copy, indent=2)}")
        return False
    
    print("   ✅ Both responses are identical")
    
    # Step 5: Verify all fields persisted
    print("\n5. Verifying all fields persisted correctly...")
    
    checks = [
        ("favorite_colors", ["navy", "white"]),
        ("styles", ["minimal"]),
        ("sizes", {"top": "M", "bottom": "32", "shoe": "9"}),
        ("budget", "$$"),
        ("notes", "warm climate, natural fabrics"),
    ]
    
    all_passed = True
    for field, expected in checks:
        actual = profile1.get(field)
        if actual != expected:
            print(f"   ❌ {field}: expected {expected}, got {actual}")
            all_passed = False
        else:
            print(f"   ✅ {field}: {actual}")
    
    # Check preferences fields
    prefs = profile1.get("preferences", {})
    pref_checks = [
        ("budget_min", 50),
        ("budget_max", 250),
        ("occasion", "work"),
        ("categories", ["tops"]),
        ("climate", "hot"),
        ("style", "minimal"),
        ("preferred_fit", "relaxed"),
        ("preferred_colours", ["navy", "olive"]),
        ("avoided_colours", ["black"]),
        ("preferred_retailers", ["zara", "uniqlo", "romanelli-b2b"]),
    ]
    
    print("\n   Preferences fields:")
    for field, expected in pref_checks:
        actual = prefs.get(field)
        if actual != expected:
            print(f"   ❌ preferences.{field}: expected {expected}, got {actual}")
            all_passed = False
        else:
            print(f"   ✅ preferences.{field}: {actual}")
    
    # Step 6: Verify preferred_colours and avoided_colours are disjoint
    print("\n6. Verifying preferred_colours and avoided_colours are disjoint...")
    preferred = set(prefs.get("preferred_colours", []))
    avoided = set(prefs.get("avoided_colours", []))
    intersection = preferred & avoided
    
    if intersection:
        print(f"   ❌ FAIL: Colours appear in both lists: {intersection}")
        all_passed = False
    else:
        print(f"   ✅ Disjoint: preferred={list(preferred)}, avoided={list(avoided)}")
    
    if not all_passed:
        return False
    
    print("\n" + "="*80)
    print("TEST B: ✅ PASS")
    print("="*80)
    return True


def test_c_stylist_profile_context():
    """
    TEST C: Stylist receives saved profile context (ONE chat call only)
    """
    print("\n" + "="*80)
    print("TEST C: Stylist Profile Context Usage")
    print("="*80)
    
    # Step 1: Create conversation
    print("\n1. Creating conversation...")
    try:
        resp = requests.post(f"{BASE_URL}/conversations", timeout=30)
        if resp.status_code != 200:
            print(f"   ❌ FAIL: POST /api/conversations returned {resp.status_code}")
            return False
        convo = resp.json()
        convo_id = convo["id"]
        print(f"   ✅ Conversation created: {convo_id}")
    except Exception as e:
        print(f"   ❌ FAIL: Exception creating conversation: {e}")
        return False
    
    # Step 2: Send chat message (SSE stream)
    print("\n2. Sending chat message (SSE stream)...")
    print("   Message: 'What should I wear this week? Give me two specific pieces.'")
    
    chat_data = {
        "message": "What should I wear this week? Give me two specific pieces."
    }
    
    try:
        resp = requests.post(
            f"{BASE_URL}/conversations/{convo_id}/chat",
            json=chat_data,
            stream=True,
            timeout=120
        )
        
        if resp.status_code != 200:
            print(f"   ❌ FAIL: POST /api/conversations/{convo_id}/chat returned {resp.status_code}")
            print(f"   Response: {resp.text}")
            return False
        
        print("   ✅ SSE stream started")
        
        # Collect streamed response
        full_text = ""
        done_payload = None
        
        print("\n   Streaming response:")
        print("   " + "-"*76)
        
        for line in resp.iter_lines(decode_unicode=True):
            if line.startswith("data: "):
                data_str = line[6:]  # Remove "data: " prefix
                try:
                    data = json.loads(data_str)
                    if "delta" in data:
                        full_text += data["delta"]
                        # Print deltas inline
                        print(data["delta"], end="", flush=True)
                    elif "done" in data and data["done"]:
                        done_payload = data
                        print()  # New line after streaming
                        break
                except json.JSONDecodeError:
                    continue
        
        print("   " + "-"*76)
        
        if not done_payload:
            print("   ❌ FAIL: No done event received")
            return False
        
        print(f"\n   ✅ Streaming complete")
        print(f"   Done payload: {json.dumps(done_payload, indent=2)}")
        
    except Exception as e:
        print(f"   ❌ FAIL: Exception during chat: {e}")
        return False
    
    # Step 3: Verify provider in done payload
    print("\n3. Verifying provider in done payload...")
    provider = done_payload.get("provider")
    if provider != "claude":
        print(f"   ❌ FAIL: Expected provider='claude', got '{provider}'")
        return False
    print(f"   ✅ Provider: {provider}")
    
    # Step 4: Analyze response for profile context
    print("\n4. Analyzing response for profile context...")
    
    full_text_lower = full_text.lower()
    
    # Check for hot climate indicators (lightweight/breathable fabrics)
    hot_climate_keywords = [
        "linen", "cotton", "lightweight", "breathable", "light", "airy",
        "cool", "moisture-wicking", "natural fabric", "breathable fabric"
    ]
    
    hot_climate_found = []
    for keyword in hot_climate_keywords:
        if keyword in full_text_lower:
            hot_climate_found.append(keyword)
    
    # Check for preferred colours (navy, olive) or palette reference
    colour_keywords = ["navy", "olive", "neutral", "warm", "palette"]
    colour_found = []
    for keyword in colour_keywords:
        if keyword in full_text_lower:
            colour_found.append(keyword)
    
    # Check for avoided heavy items (should NOT be recommended)
    heavy_items = ["heavy jacket", "wool coat", "puffer", "blazer", "thick sweater", "heavy coat"]
    heavy_found = []
    for item in heavy_items:
        if item in full_text_lower:
            heavy_found.append(item)
    
    # Check for black (should be avoided)
    black_mentioned = "black" in full_text_lower
    
    print("\n   Analysis:")
    print(f"   Hot climate indicators found: {hot_climate_found if hot_climate_found else 'None'}")
    print(f"   Colour references found: {colour_found if colour_found else 'None'}")
    print(f"   Heavy items mentioned: {heavy_found if heavy_found else 'None (good!)'}")
    print(f"   'Black' mentioned: {'Yes (concerning)' if black_mentioned else 'No (good!)'}")
    
    # Evaluation
    print("\n5. Evaluation:")
    
    passed = True
    
    if not hot_climate_found:
        print("   ⚠️  WARNING: No explicit hot climate indicators found")
        print("      (Expected lightweight/breathable fabric mentions)")
        # Not a hard fail, but concerning
    else:
        print(f"   ✅ Hot climate context reflected: {', '.join(hot_climate_found)}")
    
    if colour_found:
        print(f"   ✅ Colour preferences/palette referenced: {', '.join(colour_found)}")
    else:
        print("   ⚠️  WARNING: No colour preferences or palette mentioned")
    
    if heavy_found:
        print(f"   ❌ FAIL: Heavy items recommended (inappropriate for hot climate): {', '.join(heavy_found)}")
        passed = False
    else:
        print("   ✅ No heavy jackets/wool coats/puffers/blazers recommended")
    
    if black_mentioned:
        print("   ⚠️  WARNING: 'Black' mentioned (should be avoided per preferences)")
        # Not a hard fail if it's in a cautionary context
    else:
        print("   ✅ 'Black' not mentioned (correctly avoided)")
    
    # Print full response for manual review
    print("\n6. Full response for manual review:")
    print("   " + "="*76)
    print(f"   {full_text}")
    print("   " + "="*76)
    
    if not passed:
        print("\n" + "="*80)
        print("TEST C: ❌ FAIL")
        print("="*80)
        return False
    
    # If we have at least some hot climate indicators and no heavy items, consider it a pass
    if hot_climate_found or colour_found:
        print("\n" + "="*80)
        print("TEST C: ✅ PASS")
        print("="*80)
        return True
    else:
        print("\n" + "="*80)
        print("TEST C: ⚠️  PARTIAL (profile context not clearly reflected)")
        print("="*80)
        return False


def main():
    print("\n" + "="*80)
    print("StyleScan/LUMIÈRE Backend Verification - Run 3")
    print("Testing preferences persistence and stylist profile context")
    print("="*80)
    
    results = {}
    
    # Run TEST B
    results["B"] = test_b_preferences_persistence()
    
    # Run TEST C (only if TEST B passed, as it depends on saved preferences)
    if results["B"]:
        results["C"] = test_c_stylist_profile_context()
    else:
        print("\n⚠️  Skipping TEST C (depends on TEST B)")
        results["C"] = None
    
    # Summary
    print("\n" + "="*80)
    print("FINAL SUMMARY")
    print("="*80)
    
    print(f"\nTEST B (Preferences Persistence): {'✅ PASS' if results['B'] else '❌ FAIL'}")
    if results["C"] is not None:
        print(f"TEST C (Stylist Profile Context): {'✅ PASS' if results['C'] else '❌ FAIL'}")
    else:
        print("TEST C (Stylist Profile Context): ⚠️  SKIPPED (TEST B failed)")
    
    # Exit code
    if results["B"] and results.get("C"):
        print("\n✅ All tests PASSED")
        sys.exit(0)
    else:
        print("\n❌ Some tests FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()
