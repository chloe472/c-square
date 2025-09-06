import requests
import json
import time

def test_small_case():
    """Test the small case"""
    print("=== Testing Small Case ===")
    
    with open('small_test.json', 'r') as f:
        test_data = json.load(f)
    
    try:
        start_time = time.time()
        response = requests.post(
            'http://127.0.0.1:8080/ticketing-agent',
            headers={'Content-Type': 'application/json'},
            json=test_data,
            timeout=30
        )
        end_time = time.time()
        
        print(f"Status Code: {response.status_code}")
        print(f"Client-side time: {end_time - start_time:.3f} seconds")
        
        if response.status_code == 200:
            result = response.json()
            expected = {"CUSTOMER_A": "CONCERT_1", "CUSTOMER_B": "CONCERT_2"}
            if result == expected:
                print("✅ Small test PASSED")
                return True
            else:
                print("❌ Results don't match expected")
                return False
        else:
            print(f"❌ Server Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

def test_large_case():
    """Test the large case (1000 customers, 100 concerts)"""
    print("\n=== Testing Large Case (1000×100 = 100,000 calculations) ===")
    
    try:
        with open('large_test.json', 'r') as f:
            test_data = json.load(f)
    except FileNotFoundError:
        print("❌ large_test.json not found. Run 'python generate_tests.py' first.")
        return False
    
    print(f"Loaded {len(test_data['customers'])} customers and {len(test_data['concerts'])} concerts")
    print("Starting performance test...")
    
    try:
        start_time = time.time()
        response = requests.post(
            'http://127.0.0.1:8080/ticketing-agent',
            headers={'Content-Type': 'application/json'},
            json=test_data,
            timeout=30  # 30 second timeout
        )
        end_time = time.time()
        
        print(f"Status Code: {response.status_code}")
        print(f"Client-side time: {end_time - start_time:.3f} seconds")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Successfully assigned {len(result)} customers to concerts")
            
            # Performance benchmarks
            client_time = end_time - start_time
            if client_time < 2.0:
                print("🚀 EXCELLENT performance - under 2 seconds!")
            elif client_time < 5.0:
                print("✅ GOOD performance - under 5 seconds")
            elif client_time < 10.0:
                print("⚠️  ACCEPTABLE performance - under 10 seconds")
            else:
                print("❌ SLOW performance - over 10 seconds")
            
            return True
        else:
            print(f"❌ Server Error: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print("❌ TIMEOUT ERROR - Request took longer than 30 seconds")
        print("Your optimization may not be sufficient for this dataset size")
        return False
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

def test_medium_case():
    """Test medium case first (100 customers, 20 concerts)"""
    print("\n=== Testing Medium Case (100×20 = 2,000 calculations) ===")
    
    # Generate medium test on the fly
    medium_test = {
        "customers": [
            {
                "name": f"CUSTOMER_{i+1}",
                "vip_status": False,
                "location": [i % 10, i % 10],
                "credit_card": f"CARD_{(i % 5) + 1}"
            } for i in range(100)
        ],
        "concerts": [
            {
                "name": f"CONCERT_{i+1}",
                "booking_center_location": [i % 10, i % 10]
            } for i in range(20)
        ],
        "priority": {f"CARD_{i}": f"CONCERT_{i}" for i in range(1, 6)}
    }
    
    try:
        start_time = time.time()
        response = requests.post(
            'http://127.0.0.1:8080/ticketing-agent',
            headers={'Content-Type': 'application/json'},
            json=medium_test,
            timeout=30
        )
        end_time = time.time()
        
        print(f"Status Code: {response.status_code}")
        print(f"Client-side time: {end_time - start_time:.3f} seconds")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Medium test PASSED - {len(result)} assignments")
            return True
        else:
            print(f"❌ Medium test FAILED: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Performance Testing Suite")
    print("=" * 50)
    
    # Test in order of increasing difficulty
    success_small = test_small_case()
    if success_small:
        success_medium = test_medium_case()
        if success_medium:
            success_large = test_large_case()
            
            if success_large:
                print("\n🎉 ALL TESTS PASSED!")
                print("Your optimization successfully handles the maximum constraints!")
            else:
                print("\n⚠️  Large test failed - optimization may need improvement")
        else:
            print("\n❌ Medium test failed - check your code")
    else:
        print("\n❌ Small test failed - fix basic issues first")