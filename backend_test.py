#!/usr/bin/env python3
"""
Backend API Testing Script for StyleScan/LUMIÈRE
Run 4: Selfie skin-analysis pipeline verification
"""

import os
import sys
import json
import time
import requests
from pathlib import Path

# Base URL from frontend/.env
BASE_URL = "https://stylescan-v3.preview.emergentagent.com"
API_BASE = f"{BASE_URL}/api"

# Test image
TEST_IMAGE = "/tmp/face_a.jpg"

# Global profile ID
PROFILE_ID = "default"

def print_section(title):
    """Print a section header"""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")

def print_result(test_name, status, details=""):
    """Print test result"""
    symbol = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
    print(f"{symbol} {test_name}: {status}")
    if details:
        print(f"   {details}")

def test_upload_image(image_path):
    """Test 1: Upload image via POST /api/upload"""
    print_section("TEST 1: Upload Image")
    
    if not os.path.exists(image_path):
        print_result("Upload Image", "FAIL", f"Image not found: {image_path}")
        return None
    
    try:
        with open(image_path, 'rb') as f:
            files = {'file': ('face_a.jpg', f, 'image/jpeg')}
            response = requests.post(f"{API_BASE}/upload", files=files, timeout=30)
        
        print(f"HTTP Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            path = data.get('path', '')
            print(f"Response: {json.dumps(data, indent=2)}")
            
            if path.startswith('stylescan/'):
                print_result("Upload Image", "PASS", f"Path: {path}")
                return path
            else:
                print_result("Upload Image", "FAIL", f"Path does not start with 'stylescan/': {path}")
                return None
        else:
            print(f"Response Body: {response.text}")
            print_result("Upload Image", "FAIL", f"HTTP {response.status_code}")
            return None
            
    except Exception as e:
        print_result("Upload Image", "FAIL", f"Exception: {str(e)}")
        return None

def test_skin_analysis(image_path, provider="claude"):
    """Test 2: Analyze skin via POST /api/skin-analysis"""
    print_section(f"TEST 2: Skin Analysis (provider={provider})")
    
    try:
        payload = {
            "image_path": image_path,
            "provider": provider
        }
        print(f"Request payload: {json.dumps(payload, indent=2)}")
        
        start_time = time.time()
        response = requests.post(f"{API_BASE}/skin-analysis", json=payload, timeout=120)
        elapsed = time.time() - start_time
        
        print(f"HTTP Status: {response.status_code}")
        print(f"Time elapsed: {elapsed:.1f}s")
        
        if response.status_code == 200:
            data = response.json()
            
            # Check required fields
            required_fields = ['undertone', 'depth', 'chroma', 'contrast', 'season', 
                             'analysis_quality', 'analyzed_with']
            missing_fields = [f for f in required_fields if f not in data]
            
            if missing_fields:
                print_result("Skin Analysis", "FAIL", f"Missing fields: {missing_fields}")
                return None
            
            # Check analysis_quality sub-fields
            aq = data.get('analysis_quality', {})
            aq_fields = ['lighting_quality', 'face_visibility', 'confidence']
            missing_aq = [f for f in aq_fields if f not in aq]
            
            if missing_aq:
                print_result("Skin Analysis", "FAIL", f"Missing analysis_quality fields: {missing_aq}")
                return None
            
            # Check palette groups
            palette_groups = ['best_neutrals', 'best_accents', 'statement_colours', 'caution_colours']
            missing_groups = [g for g in palette_groups if g not in data]
            
            if missing_groups:
                print_result("Skin Analysis", "FAIL", f"Missing palette groups: {missing_groups}")
                return None
            
            # Check each palette group has items with name+hex
            for group in palette_groups:
                items = data.get(group, [])
                if not items:
                    print_result("Skin Analysis", "FAIL", f"Empty palette group: {group}")
                    return None
                
                for item in items:
                    if 'name' not in item or 'hex' not in item:
                        print_result("Skin Analysis", "FAIL", f"Palette item missing name/hex in {group}")
                        return None
            
            # Print key values
            print(f"\nKey Analysis Values:")
            print(f"  undertone: {data['undertone']}")
            print(f"  depth: {data['depth']}")
            print(f"  chroma: {data['chroma']}")
            print(f"  contrast: {data['contrast']}")
            print(f"  season: {data['season']}")
            print(f"  analyzed_with: {data['analyzed_with']}")
            print(f"\nAnalysis Quality:")
            print(f"  lighting_quality: {aq['lighting_quality']}")
            print(f"  face_visibility: {aq['face_visibility']}")
            print(f"  confidence: {aq['confidence']}")
            print(f"\nPalette Groups:")
            for group in palette_groups:
                items = data[group]
                print(f"  {group}: {len(items)} items")
                for item in items[:2]:  # Show first 2 items
                    print(f"    - {item['name']} ({item['hex']})")
            
            print_result("Skin Analysis", "PASS", f"All fields present and valid")
            return data
            
        else:
            print(f"Response Body: {response.text}")
            print_result("Skin Analysis", "FAIL", f"HTTP {response.status_code}")
            return None
            
    except Exception as e:
        print_result("Skin Analysis", "FAIL", f"Exception: {str(e)}")
        return None

def test_profile_updated(expected_image_path):
    """Test 3: Check profile.skin is populated"""
    print_section("TEST 3: Profile Updated")
    
    try:
        response = requests.get(f"{API_BASE}/profile", timeout=30)
        
        print(f"HTTP Status: {response.status_code}")
        
        if response.status_code == 200:
            profile = response.json()
            skin = profile.get('skin')
            
            if not skin:
                print_result("Profile Updated", "FAIL", "profile.skin is empty")
                return False
            
            image_path = skin.get('image_path')
            analyzed_at = skin.get('analyzed_at')
            
            print(f"\nProfile Skin Data:")
            print(f"  image_path: {image_path}")
            print(f"  analyzed_at: {analyzed_at}")
            print(f"  undertone: {skin.get('undertone')}")
            print(f"  depth: {skin.get('depth')}")
            print(f"  season: {skin.get('season')}")
            
            if image_path != expected_image_path:
                print_result("Profile Updated", "FAIL", 
                           f"image_path mismatch: expected {expected_image_path}, got {image_path}")
                return False
            
            if not analyzed_at:
                print_result("Profile Updated", "FAIL", "analyzed_at not set")
                return False
            
            print_result("Profile Updated", "PASS", 
                        f"profile.skin populated correctly with image_path={image_path}")
            return True
            
        else:
            print(f"Response Body: {response.text}")
            print_result("Profile Updated", "FAIL", f"HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print_result("Profile Updated", "FAIL", f"Exception: {str(e)}")
        return False

def test_fresh_analysis():
    """Test 4: Fresh analysis (not cached) - upload same image again"""
    print_section("TEST 4: Fresh Analysis (Not Cached)")
    
    # Get current profile state
    try:
        response = requests.get(f"{API_BASE}/profile", timeout=30)
        if response.status_code != 200:
            print_result("Fresh Analysis", "FAIL", "Cannot get initial profile state")
            return False
        
        initial_profile = response.json()
        initial_skin = initial_profile.get('skin', {})
        initial_path = initial_skin.get('image_path')
        initial_analyzed_at = initial_skin.get('analyzed_at')
        
        print(f"Initial state:")
        print(f"  image_path: {initial_path}")
        print(f"  analyzed_at: {initial_analyzed_at}")
        
    except Exception as e:
        print_result("Fresh Analysis", "FAIL", f"Cannot get initial profile: {str(e)}")
        return False
    
    # Upload same image again
    print(f"\nUploading {TEST_IMAGE} again...")
    new_path = test_upload_image(TEST_IMAGE)
    
    if not new_path:
        print_result("Fresh Analysis", "FAIL", "Second upload failed")
        return False
    
    if new_path == initial_path:
        print_result("Fresh Analysis", "FAIL", 
                    f"New path same as old path: {new_path} (should be different)")
        return False
    
    print(f"New path: {new_path} (different from {initial_path} ✓)")
    
    # Analyze with new path
    print(f"\nAnalyzing with new path...")
    analysis = test_skin_analysis(new_path, provider="claude")
    
    if not analysis:
        print_result("Fresh Analysis", "FAIL", "Second analysis failed")
        return False
    
    # Check profile updated to new path
    print(f"\nChecking profile updated to new path...")
    try:
        response = requests.get(f"{API_BASE}/profile", timeout=30)
        if response.status_code != 200:
            print_result("Fresh Analysis", "FAIL", "Cannot get updated profile")
            return False
        
        updated_profile = response.json()
        updated_skin = updated_profile.get('skin', {})
        updated_path = updated_skin.get('image_path')
        updated_analyzed_at = updated_skin.get('analyzed_at')
        
        print(f"Updated state:")
        print(f"  image_path: {updated_path}")
        print(f"  analyzed_at: {updated_analyzed_at}")
        
        if updated_path != new_path:
            print_result("Fresh Analysis", "FAIL", 
                        f"Profile not updated to new path: expected {new_path}, got {updated_path}")
            return False
        
        if updated_path == initial_path:
            print_result("Fresh Analysis", "FAIL", 
                        f"Profile still has old path: {updated_path}")
            return False
        
        if updated_analyzed_at == initial_analyzed_at:
            print_result("Fresh Analysis", "FAIL", 
                        f"analyzed_at not changed: {updated_analyzed_at}")
            return False
        
        print_result("Fresh Analysis", "PASS", 
                    f"Fresh analysis confirmed: new path {new_path}, analyzed_at changed")
        return True
        
    except Exception as e:
        print_result("Fresh Analysis", "FAIL", f"Exception: {str(e)}")
        return False

def test_regression():
    """Test 5: Regression - Stylist and Try-On still work"""
    print_section("TEST 5: Regression Tests")
    
    results = {}
    
    # Test Stylist: Create conversation
    try:
        response = requests.post(f"{API_BASE}/conversations", json={}, timeout=30)
        print(f"POST /api/conversations: HTTP {response.status_code}")
        
        if response.status_code == 200:
            conv_data = response.json()
            conv_id = conv_data.get('id')
            
            if conv_id:
                # Test chat
                chat_payload = {"message": "Suggest one summer top."}
                response = requests.post(
                    f"{API_BASE}/conversations/{conv_id}/chat",
                    json=chat_payload,
                    timeout=60,
                    stream=True
                )
                print(f"POST /api/conversations/{conv_id}/chat: HTTP {response.status_code}")
                
                if response.status_code == 200:
                    # Check SSE streaming
                    chunks = []
                    for line in response.iter_lines():
                        if line:
                            chunks.append(line.decode('utf-8'))
                            if len(chunks) >= 5:  # Just check first few chunks
                                break
                    
                    if chunks:
                        print_result("Stylist Chat", "PASS", f"SSE streaming works, received {len(chunks)} chunks")
                        results['stylist'] = True
                    else:
                        print_result("Stylist Chat", "FAIL", "No SSE chunks received")
                        results['stylist'] = False
                else:
                    print(f"Response: {response.text}")
                    print_result("Stylist Chat", "FAIL", f"HTTP {response.status_code}")
                    results['stylist'] = False
            else:
                print_result("Stylist Chat", "FAIL", "No conversation ID returned")
                results['stylist'] = False
        else:
            print(f"Response: {response.text}")
            print_result("Stylist Chat", "FAIL", f"HTTP {response.status_code}")
            results['stylist'] = False
            
    except Exception as e:
        print_result("Stylist Chat", "FAIL", f"Exception: {str(e)}")
        results['stylist'] = False
    
    # Test Try-On: GET /api/tryons
    try:
        response = requests.get(f"{API_BASE}/tryons", timeout=30)
        print(f"\nGET /api/tryons: HTTP {response.status_code}")
        
        if response.status_code == 200:
            tryons = response.json()
            print_result("Try-On Endpoint", "PASS", f"Returns {len(tryons)} try-ons")
            results['tryon'] = True
        else:
            print(f"Response: {response.text}")
            print_result("Try-On Endpoint", "FAIL", f"HTTP {response.status_code}")
            results['tryon'] = False
            
    except Exception as e:
        print_result("Try-On Endpoint", "FAIL", f"Exception: {str(e)}")
        results['tryon'] = False
    
    return all(results.values())

def main():
    """Main test runner"""
    print("\n" + "="*80)
    print("  StyleScan/LUMIÈRE Backend Verification - Run 4")
    print("  Selfie Skin-Analysis Pipeline")
    print("="*80)
    print(f"\nBase URL: {BASE_URL}")
    print(f"API Base: {API_BASE}")
    print(f"Test Image: {TEST_IMAGE}")
    print(f"Profile ID: {PROFILE_ID}")
    
    results = {}
    
    # Test 1: Upload image
    path1 = test_upload_image(TEST_IMAGE)
    results['upload'] = path1 is not None
    
    if not path1:
        print("\n❌ Cannot proceed without successful upload")
        return False
    
    # Test 2: Analyze skin
    analysis1 = test_skin_analysis(path1, provider="claude")
    results['analysis'] = analysis1 is not None
    
    if not analysis1:
        print("\n❌ Cannot proceed without successful analysis")
        return False
    
    # Test 3: Profile updated
    results['profile_updated'] = test_profile_updated(path1)
    
    # Test 4: Fresh analysis (not cached)
    results['fresh_analysis'] = test_fresh_analysis()
    
    # Test 5: Regression
    results['regression'] = test_regression()
    
    # Final summary
    print_section("FINAL SUMMARY")
    
    test_names = {
        'upload': 'TEST 1: Upload Image',
        'analysis': 'TEST 2: Skin Analysis',
        'profile_updated': 'TEST 3: Profile Updated',
        'fresh_analysis': 'TEST 4: Fresh Analysis (Not Cached)',
        'regression': 'TEST 5: Regression Tests'
    }
    
    for key, name in test_names.items():
        status = "PASS" if results.get(key, False) else "FAIL"
        print_result(name, status)
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    
    print(f"\n{'='*80}")
    print(f"  OVERALL: {passed}/{total} tests passed")
    print(f"{'='*80}\n")
    
    return all(results.values())

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
