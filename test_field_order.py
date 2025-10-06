#!/usr/bin/env python3
"""
Script untuk test urutan field dalam response API
"""

import requests
import json

def test_field_order():
    """Test urutan field dalam response"""
    base_url = "http://localhost:5000"
    
    try:
        # Test endpoint contacts
        print("Testing field order in /contacts endpoint...")
        response = requests.get(f"{base_url}/contacts?limit=1")
        
        if response.status_code == 200:
            data = response.json()
            if data['success'] and data['data']:
                contact = data['data'][0]
                print("\nField order in response:")
                for i, (key, value) in enumerate(contact.items(), 1):
                    print(f"{i}. {key}: {value}")
                
                # Check if 'id' is first
                first_field = list(contact.keys())[0]
                if first_field == 'id':
                    print("\n✅ SUCCESS: Field 'id' is first!")
                else:
                    print(f"\n❌ ERROR: First field is '{first_field}', should be 'id'")
            else:
                print("No data returned")
        else:
            print(f"Error: {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to API. Make sure the server is running on localhost:5000")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_field_order()
