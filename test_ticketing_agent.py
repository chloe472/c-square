import requests
import json

def test_ticketing_agent():
    """Test the ticketing agent endpoint"""
    url = "http://localhost:8080/ticketing-agent"
    
    test_data = {
        "customers": [
            {
                "name": "CUSTOMER_A",
                "vip_status": False,
                "location": [1, 1],
                "credit_card": "CREDIT_CARD_1"
            },
            {
                "name": "CUSTOMER_B", 
                "vip_status": False,
                "location": [2, -3],
                "credit_card": "CREDIT_CARD_2"
            }
        ],
        "concerts": [
            {
                "name": "CONCERT_1",
                "booking_center_location": [1, 5]
            },
            {
                "name": "CONCERT_2",
                "booking_center_location": [-5, -3]
            }
        ],
        "priority": {
            "CREDIT_CARD_1": "CONCERT_1",
            "CREDIT_CARD_2": "CONCERT_2"
        }
    }
    
    headers = {'Content-Type': 'application/json'}
    
    try:
        print("Testing ticketing agent endpoint...")
        response = requests.post(url, json=test_data, headers=headers)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        
        expected = {
            "CUSTOMER_A": "CONCERT_1",
            "CUSTOMER_B": "CONCERT_2"
        }
        
        if response.status_code == 200 and response.json() == expected:
            print("Ticketing Agent Test PASSED!")
        else:
            print("Ticketing Agent Test FAILED!")
            print(f"Expected: {expected}")
            print(f"Got: {response.json()}")
            
    except requests.exceptions.ConnectionError:
        print("Connection failed. Make sure the server is running on port 8080")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    test_ticketing_agent()
