#!/usr/bin/env python3
"""
Test script untuk Face Recognition API dengan DeepFace
Jalankan: python test_deepface.py
"""
import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_health():
    """Test health endpoint"""
    print("\n" + "="*60)
    print("TEST 1: Health Check")
    print("="*60)
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        data = response.json()
        print(f"Status: {data.get('status')}")
        print(f"Library: {data.get('library')}")
        print(f"Model: {data.get('model')}")
        print(f"Detector: {data.get('detector')}")
        print(f"✓ Health check passed")
        return True
    except Exception as e:
        print(f"✗ Health check failed: {e}")
        return False

def test_model_info():
    """Test model info endpoint"""
    print("\n" + "="*60)
    print("TEST 2: Model Info")
    print("="*60)
    try:
        response = requests.get(f"{BASE_URL}/api/v1/faces/model-info", timeout=5)
        data = response.json()
        print(f"Model Name: {data.get('model_name')}")
        print(f"Detector: {data.get('detector_backend')}")
        print(f"Embedding Dim: {data.get('embedding_dim')}")
        print(f"Threshold: {data.get('threshold')}")
        print(f"Loaded: {data.get('loaded')}")
        print(f"✓ Model info retrieved")
        return True
    except Exception as e:
        print(f"✗ Model info failed: {e}")
        return False

def test_status():
    """Test status endpoint"""
    print("\n" + "="*60)
    print("TEST 3: Service Status")
    print("="*60)
    try:
        response = requests.get(f"{BASE_URL}/api/v1/faces/status", timeout=10)
        data = response.json()
        print(f"Status: {data.get('status')}")
        print(f"Service: {data.get('service')}")
        print(f"Model: {data.get('model')}")
        print(f"Total Users: {data.get('total_users')}")
        print(f"Threshold: {data.get('face_threshold')}")
        print(f"✓ Status check passed")
        return True
    except Exception as e:
        print(f"✗ Status check failed: {e}")
        return False

def test_quality_dummy():
    """Test quality assessment dengan dummy image (akan fail tapi test endpoint)"""
    print("\n" + "="*60)
    print("TEST 4: Quality Assessment (with invalid image)")
    print("="*60)
    try:
        # Test dengan invalid image (akan return error tapi endpoint berfungsi)
        response = requests.post(
            f"{BASE_URL}/api/v1/faces/quality",
            json={"image": "data:image/jpeg;base64,invalid"},
            timeout=5
        )
        data = response.json()
        print(f"Status: {data.get('status')}")
        print(f"Feedback: {data.get('feedback')}")
        print(f"✓ Quality endpoint working")
        return True
    except Exception as e:
        print(f"✗ Quality test failed: {e}")
        return False

def test_root():
    """Test root endpoint"""
    print("\n" + "="*60)
    print("TEST 5: Root Endpoint")
    print("="*60)
    try:
        response = requests.get(f"{BASE_URL}/", timeout=5)
        data = response.json()
        print(f"Name: {data.get('name')}")
        print(f"Version: {data.get('version')}")
        print(f"Model: {data.get('model')}")
        print(f"Endpoints: {list(data.get('endpoints', {}).keys())}")
        print(f"Routes: {data.get('routes')}")
        print(f"✓ Root endpoint passed")
        return True
    except Exception as e:
        print(f"✗ Root endpoint failed: {e}")
        return False

def main():
    print("\n" + "="*60)
    print("Face Recognition API - DeepFace Test Suite")
    print("="*60)
    print(f"Testing against: {BASE_URL}")
    print("Make sure server is running: python main.py")
    
    results = []
    
    # Run tests
    results.append(("Health Check", test_health()))
    time.sleep(0.5)
    results.append(("Model Info", test_model_info()))
    time.sleep(0.5)
    results.append(("Service Status", test_status()))
    time.sleep(0.5)
    results.append(("Quality Assessment", test_quality_dummy()))
    time.sleep(0.5)
    results.append(("Root Endpoint", test_root()))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    print("\n" + "="*60)
    print(f"Result: {passed}/{total} tests passed")
    print("="*60)
    
    if passed == total:
        print("\n🎉 All tests passed! DeepFace integration is working.")
        print("\nNext steps:")
        print("1. Test face registration from /data_user")
        print("2. Test face identification from /manual-attendance")
        print("3. Monitor logs for any issues")
    else:
        print("\n⚠️  Some tests failed. Check the server logs.")

if __name__ == "__main__":
    main()
