import json
import random

def generate_large_test_case():
    """Generate a large test case (1000 customers, 100 concerts) - maximum constraints"""
    
    print("Generating large test case...")
    
    customers = []
    for i in range(1000):  # Maximum customer count
        customers.append({
            "name": f"CUSTOMER_{i+1}",
            "vip_status": random.choice([True, False]),
            "location": [random.randint(-1000, 1000), random.randint(-1000, 1000)],
            "credit_card": f"CARD_{random.randint(1, 20)}"
        })
        
        if i % 100 == 0:
            print(f"Generated {i} customers...")
    
    concerts = []
    for i in range(100):  # Maximum concert count
        concerts.append({
            "name": f"CONCERT_{i+1}",
            "booking_center_location": [random.randint(-1000, 1000), random.randint(-1000, 1000)]
        })
    
    priority = {}
    for i in range(1, 21):  # 20 different cards with priorities
        priority[f"CARD_{i}"] = f"CONCERT_{random.randint(1, 100)}"
    
    test_case = {
        "customers": customers,
        "concerts": concerts,
        "priority": priority
    }
    
    return test_case

def save_large_test():
    """Generate and save large test case"""
    large_test = generate_large_test_case()
    
    with open('large_test.json', 'w') as f:
        json.dump(large_test, f, indent=2)
    
    print(f"\nLarge test case saved to 'large_test.json'")
    print(f"- {len(large_test['customers'])} customers")
    print(f"- {len(large_test['concerts'])} concerts") 
    print(f"- Total calculations: {len(large_test['customers']) * len(large_test['concerts']):,}")

if __name__ == "__main__":
    save_large_test()