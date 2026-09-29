#!/usr/bin/env python3
"""
Backend test suite for StyleScan OpenAI provider selection feature.
Tests the newly added OpenAI/ChatGPT provider alongside existing Claude integration.
"""
import json
import time
import requests
from pathlib import Path

# Base URL from frontend/.env EXPO_PUBLIC_BACKEND_URL
BASE_URL = "https://stylescan-v3.preview.emergentagent.com/api"
TEST_SELFIE = "/tmp/test_selfie.jpg"
REUSABLE_IMAGE_PATH = "stylescan/uploads/anon/4f74fe38-08b7-4744-be4e-15918a0b5b82.jpg"

# Test results tracking
results = {
    "passed": [],
    "failed": [],
    "warnings": []
}

def log_pass(test_name):
    print(f"✅ PASS: {test_name}")
    results["passed"].append(test_name)

def log_fail(test_name, error):
    print(f"❌ FAIL: {test_name}")
    print(f"   Error: {error}")
    results["failed"].append({"test": test_name, "error": str(error)})

def log_warning(test_name, warning):
    print(f"⚠️  WARNING: {test_name}")
    print(f"   {warning}")
    results["warnings"].append({"test": test_name, "warning": str(warning)})

def print_section(title):
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")

# ============================================================================
# Test 1: GET /api/models
# ============================================================================
def test_models_endpoint():
    print_section("TEST 1: GET /api/models - Provider List")
    try:
        response = requests.get(f"{BASE_URL}/models", timeout=10)
        response.raise_for_status()
        data = response.json()
        
        print(f"Response: {json.dumps(data, indent=2)}")
        
        # Check default
        if data.get("default") != "claude":
            log_fail("GET /api/models - default provider", f"Expected default='claude', got '{data.get('default')}'")
            return False
        
        # Check providers list
        providers = data.get("providers", [])
        if not isinstance(providers, list):
            log_fail("GET /api/models - providers list", "providers is not a list")
            return False
        
        # Find claude and openai
        claude_found = False
        openai_found = False
        
        for p in providers:
            if p.get("id") == "claude":
                claude_found = True
                if p.get("model") != "claude-sonnet-5":
                    log_fail("GET /api/models - claude model", f"Expected model='claude-sonnet-5', got '{p.get('model')}'")
                    return False
            elif p.get("id") == "openai":
                openai_found = True
                if p.get("model") != "gpt-5.6-sol":
                    log_fail("GET /api/models - openai model", f"Expected model='gpt-5.6-sol', got '{p.get('model')}'")
                    return False
        
        if not claude_found:
            log_fail("GET /api/models - claude provider", "Claude provider not found in providers list")
            return False
        
        if not openai_found:
            log_fail("GET /api/models - openai provider", "OpenAI provider not found in providers list")
            return False
        
        log_pass("GET /api/models returns correct default and providers")
        return True
        
    except Exception as e:
        log_fail("GET /api/models", str(e))
        return False

# ============================================================================
# Test 2: Stylist Chat Provider Selection
# ============================================================================
def test_chat_provider_selection():
    print_section("TEST 2: Stylist Chat Provider Selection")
    
    # Test with provider=openai
    print("\n--- Testing with provider='openai' ---")
    success_openai = test_chat_with_provider("openai", "In one short sentence, suggest a neutral capsule top.")
    
    # Test with provider=claude
    print("\n--- Testing with provider='claude' ---")
    success_claude = test_chat_with_provider("claude", "In one short sentence, suggest a versatile jacket.")
    
    # Test with no provider (default)
    print("\n--- Testing with NO provider (should default to claude) ---")
    success_default = test_chat_with_provider(None, "In one short sentence, suggest comfortable shoes.")
    
    return success_openai and success_claude and success_default

def test_chat_with_provider(provider, message):
    try:
        # Create conversation
        response = requests.post(f"{BASE_URL}/conversations", timeout=10)
        response.raise_for_status()
        conversation = response.json()
        conv_id = conversation["id"]
        print(f"Created conversation: {conv_id}")
        
        # Send chat message with SSE streaming
        payload = {"message": message}
        if provider is not None:
            payload["provider"] = provider
        
        print(f"Sending message with payload: {json.dumps(payload)}")
        
        response = requests.post(
            f"{BASE_URL}/conversations/{conv_id}/chat",
            json=payload,
            stream=True,
            timeout=120  # LLM calls can take 10-60s
        )
        response.raise_for_status()
        
        # Parse SSE stream
        deltas = []
        done_payload = None
        
        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                if line_str.startswith('data: '):
                    data_str = line_str[6:]  # Remove 'data: ' prefix
                    try:
                        event_data = json.loads(data_str)
                        if 'delta' in event_data:
                            deltas.append(event_data['delta'])
                        elif event_data.get('done'):
                            done_payload = event_data
                            break
                        elif 'error' in event_data:
                            log_fail(f"Chat with provider={provider}", f"Stream error: {event_data['error']}")
                            return False
                    except json.JSONDecodeError:
                        continue
        
        if not done_payload:
            log_fail(f"Chat with provider={provider}", "No done event received")
            return False
        
        print(f"Done payload: {json.dumps(done_payload, indent=2)}")
        
        # Verify provider in done payload
        expected_provider = provider if provider else "claude"
        if done_payload.get("provider") != expected_provider:
            log_fail(
                f"Chat with provider={provider}",
                f"Expected provider='{expected_provider}' in done payload, got '{done_payload.get('provider')}'"
            )
            return False
        
        # Verify message was persisted
        response = requests.get(f"{BASE_URL}/conversations/{conv_id}/messages", timeout=10)
        response.raise_for_status()
        messages = response.json()
        
        # Should have user message + assistant message
        if len(messages) < 2:
            log_fail(f"Chat with provider={provider}", f"Expected at least 2 messages, got {len(messages)}")
            return False
        
        assistant_msg = [m for m in messages if m["role"] == "assistant"]
        if not assistant_msg:
            log_fail(f"Chat with provider={provider}", "No assistant message found in persisted messages")
            return False
        
        print(f"Assistant message persisted: {assistant_msg[0]['content'][:100]}...")
        
        log_pass(f"Chat with provider={provider or 'default'} - SSE streaming and persistence")
        return True
        
    except Exception as e:
        log_fail(f"Chat with provider={provider}", str(e))
        return False

# ============================================================================
# Test 3: Skin Analysis Provider Selection (MOST IMPORTANT)
# ============================================================================
def test_skin_analysis_providers():
    print_section("TEST 3: Skin/Colour Analysis Provider Selection")
    
    # Use the reusable image path so both providers analyze the SAME selfie
    image_path = REUSABLE_IMAGE_PATH
    print(f"Using image path: {image_path}")
    
    # Test with provider=claude
    print("\n--- Analyzing with provider='claude' ---")
    claude_result = analyze_skin(image_path, "claude")
    
    # Test with provider=openai
    print("\n--- Analyzing with provider='openai' ---")
    openai_result = analyze_skin(image_path, "openai")
    
    if not claude_result or not openai_result:
        return False
    
    # Print side-by-side comparison
    print("\n" + "="*80)
    print("  SIDE-BY-SIDE COMPARISON: Claude vs OpenAI")
    print("="*80)
    
    print("\n--- CLAUDE ANALYSIS ---")
    print_analysis_result(claude_result)
    
    print("\n--- OPENAI ANALYSIS ---")
    print_analysis_result(openai_result)
    
    # Verify both have deterministic palette groups
    print("\n--- Verifying Deterministic Palette Groups ---")
    
    palette_groups = ["best_neutrals", "best_accents", "statement_colours", "caution_colours"]
    
    for provider_name, result in [("claude", claude_result), ("openai", openai_result)]:
        print(f"\nChecking {provider_name} palette groups:")
        for group in palette_groups:
            if group not in result:
                log_fail(f"Skin analysis {provider_name} - palette", f"Missing palette group: {group}")
                return False
            
            items = result[group]
            if not isinstance(items, list) or len(items) == 0:
                log_fail(f"Skin analysis {provider_name} - palette", f"Palette group {group} is empty")
                return False
            
            # Check each item has name and hex
            for item in items:
                if "name" not in item or "hex" not in item:
                    log_fail(f"Skin analysis {provider_name} - palette", f"Palette item in {group} missing name or hex")
                    return False
            
            print(f"  ✓ {group}: {len(items)} items with name+hex")
    
    log_pass("Skin analysis with both providers - deterministic palette verified")
    return True

def analyze_skin(image_path, provider):
    try:
        payload = {
            "image_path": image_path,
            "provider": provider
        }
        
        print(f"Sending skin analysis request with provider={provider}...")
        start_time = time.time()
        
        response = requests.post(
            f"{BASE_URL}/skin-analysis",
            json=payload,
            timeout=120  # LLM calls can take 10-60s
        )
        
        elapsed = time.time() - start_time
        print(f"Analysis completed in {elapsed:.1f}s")
        
        response.raise_for_status()
        result = response.json()
        
        # Verify analyzed_with matches requested provider
        if result.get("analyzed_with") != provider:
            log_fail(
                f"Skin analysis provider={provider}",
                f"Expected analyzed_with='{provider}', got '{result.get('analyzed_with')}'"
            )
            return None
        
        return result
        
    except Exception as e:
        log_fail(f"Skin analysis provider={provider}", str(e))
        return None

def print_analysis_result(result):
    print(f"  undertone: {result.get('undertone')}")
    print(f"  depth: {result.get('depth')}")
    print(f"  chroma: {result.get('chroma')}")
    print(f"  contrast: {result.get('contrast')}")
    print(f"  season: {result.get('season')}")
    print(f"  analyzed_with: {result.get('analyzed_with')}")
    print(f"  summary: {result.get('summary')}")
    
    quality = result.get('analysis_quality', {})
    print(f"  analysis_quality:")
    print(f"    lighting_quality: {quality.get('lighting_quality')}")
    print(f"    face_visibility: {quality.get('face_visibility')}")
    print(f"    confidence: {quality.get('confidence')}")
    
    print(f"  Palette groups:")
    for group in ["best_neutrals", "best_accents", "statement_colours", "caution_colours"]:
        items = result.get(group, [])
        print(f"    {group}: {len(items)} items")
        for item in items[:3]:  # Show first 3
            print(f"      - {item.get('name')}: {item.get('hex')}")

# ============================================================================
# Test 4: Regression Tests
# ============================================================================
def test_regression_endpoints():
    print_section("TEST 4: Regression Tests")
    
    # Test GET /api/catalogue/providers
    try:
        response = requests.get(f"{BASE_URL}/catalogue/providers", timeout=10)
        response.raise_for_status()
        data = response.json()
        print(f"GET /api/catalogue/providers: {json.dumps(data, indent=2)}")
        log_pass("GET /api/catalogue/providers")
    except Exception as e:
        log_fail("GET /api/catalogue/providers", str(e))
        return False
    
    # Test GET /api/profile
    try:
        response = requests.get(f"{BASE_URL}/profile", timeout=10)
        response.raise_for_status()
        data = response.json()
        print(f"GET /api/profile: id={data.get('id')}, updated_at={data.get('updated_at')}")
        log_pass("GET /api/profile")
    except Exception as e:
        log_fail("GET /api/profile", str(e))
        return False
    
    return True

# ============================================================================
# Main Test Runner
# ============================================================================
def main():
    print("\n" + "="*80)
    print("  StyleScan Backend Tests - OpenAI Provider Selection")
    print("="*80)
    print(f"Base URL: {BASE_URL}")
    print(f"Test selfie: {TEST_SELFIE}")
    print(f"Reusable image: {REUSABLE_IMAGE_PATH}")
    
    # Run all tests
    test_models_endpoint()
    test_chat_provider_selection()
    test_skin_analysis_providers()
    test_regression_endpoints()
    
    # Print summary
    print("\n" + "="*80)
    print("  TEST SUMMARY")
    print("="*80)
    print(f"✅ Passed: {len(results['passed'])}")
    print(f"❌ Failed: {len(results['failed'])}")
    print(f"⚠️  Warnings: {len(results['warnings'])}")
    
    if results['failed']:
        print("\nFailed tests:")
        for fail in results['failed']:
            print(f"  - {fail['test']}: {fail['error']}")
    
    if results['warnings']:
        print("\nWarnings:")
        for warn in results['warnings']:
            print(f"  - {warn['test']}: {warn['warning']}")
    
    print("\n" + "="*80)
    
    return len(results['failed']) == 0

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
