#!/usr/bin/env python3
"""
Test script for verifying the Wati API integration.
This script tests the basic functionality of the Wati API wrapper.
"""

import os
import logging
import json
import requests
from whatsapp_mcp.wati_api import wati_api

# Make sure our root logger is configured properly
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("wati_test")

def analyze_response_structure(response):
    """Analyzes and prints the structure of an API response."""
    print("\nAnalyzing response structure:")
    
    if not isinstance(response, dict):
        print(f"Response is not a dictionary: {type(response)}")
        return
    
    print(f"Response top-level keys: {list(response.keys())}")
    
    # Check for result status
    if "result" in response:
        print(f"Result value: {response['result']}")
        
        # Check if result is a dict with more data
        if isinstance(response["result"], dict):
            print(f"Result keys: {list(response['result'].keys())}")
    
    # Check for common data containers
    for key in ["contact_list", "contacts", "messages", "conversation", "data"]:
        if key in response:
            data = response[key]
            if isinstance(data, list):
                print(f"{key} contains {len(data)} items")
                if data:
                    print(f"First item keys: {list(data[0].keys())}")
            else:
                print(f"{key} is not a list: {type(data)}")
    
    # Check pagination info
    if "link" in response and isinstance(response["link"], dict):
        print(f"Pagination info: {response['link']}")

def check_api_connection():
    """Verify basic API connectivity."""
    print("\nTesting basic API connectivity...")
    
    # Try making a direct request to verify credentials
    try:
        test_url = f"{wati_api.base_url}/{wati_api.tenant_id}/api/v1/getContacts"
        headers = wati_api.headers
        
        print(f"Making test request to: {test_url}")
        print(f"Using headers: {headers}")
        
        response = requests.get(test_url, headers=headers, params={"pageSize": 1, "pageNumber": 1})
        
        print(f"Response status code: {response.status_code}")
        print(f"Response headers: {dict(response.headers)}")
        
        try:
            response_json = response.json()
            print(f"Response JSON preview: {json.dumps(response_json)[:500]}...")
            analyze_response_structure(response_json)
        except json.JSONDecodeError:
            print(f"Response is not valid JSON: {response.text[:500]}")
            
        if response.status_code == 200:
            print("✅ API connection successful")
        else:
            print(f"❌ API connection failed with status code {response.status_code}")
            
    except Exception as e:
        print(f"❌ Exception when testing API connection: {str(e)}")

def test_get_contacts():
    """Test retrieving contacts from the Wati API."""
    print("\nTesting get_contacts...")
    try:
        contacts = wati_api.get_contacts(page_size=5, page_number=1)
        if contacts:
            print(f"✅ Successfully retrieved {len(contacts)} contacts")
            for contact in contacts:
                print(f"  - {contact.name} ({contact.phone_number})")
        else:
            print("❌ Failed to retrieve contacts - empty result")
            
            # Try a direct API call to diagnose
            print("\nDiagnosing get_contacts API directly:")
            test_url = f"{wati_api.base_url}/{wati_api.tenant_id}/api/v1/getContacts"
            response = requests.get(test_url, headers=wati_api.headers, params={"pageSize": 5, "pageNumber": 1})
            
            if response.status_code == 200:
                try:
                    response_json = response.json()
                    analyze_response_structure(response_json)
                except json.JSONDecodeError:
                    print(f"Response is not valid JSON: {response.text[:500]}")
            else:
                print(f"Direct API call failed with status {response.status_code}")
                
    except Exception as e:
        print(f"❌ Exception when getting contacts: {str(e)}")

def test_get_messages():
    """Test retrieving messages from the Wati API."""
    print("\nTesting get_messages...")
    
    try:
        # First, get a contact to test with
        contacts = wati_api.get_contacts(page_size=1, page_number=1)
        if not contacts:
            print("❌ No contacts found to test messages with")
            return
        
        contact = contacts[0]
        print(f"Using contact: {contact.name} ({contact.phone_number})")
        
        messages = wati_api.get_messages(contact.phone_number, page_size=5, page_number=1)
        if messages:
            print(f"✅ Successfully retrieved {len(messages)} messages")
            for message in messages:
                content = message.content if len(message.content) <= 50 else message.content[:47] + "..."
                print(f"  - [{message.timestamp}] {'You' if message.is_from_me else contact.name}: {content}")
        else:
            print("❌ Failed to retrieve messages - empty result")
    except Exception as e:
        print(f"❌ Exception when getting messages: {str(e)}")

def test_send_message():
    """Test sending a message via the Wati API."""
    print("\nTesting send_message (no actual message will be sent)...")
    
    try:
        # First get a contact to use as the recipient
        contacts = wati_api.get_contacts(page_size=1, page_number=1)
        if not contacts:
            print("❌ No contacts found to test with")
            return
            
        contact = contacts[0]
        print(f"Would send message to: {contact.name} ({contact.phone_number})")
        
        # Don't actually send a message, just print the API endpoint that would be used
        endpoint = f"api/v1/sendSessionMessage/{contact.phone_number}"
        url = f"{wati_api.base_url}/{wati_api.tenant_id}/{endpoint}"
        print(f"Would call API endpoint: {url}")
        print("✅ API endpoint construction successful")
        
    except Exception as e:
        print(f"❌ Exception when testing send_message: {str(e)}")

def check_env_vars():
    """Check if environment variables are set correctly."""
    print("\nChecking environment variables...")
    
    api_url = os.environ.get("WATI_API_BASE_URL")
    tenant_id = os.environ.get("WATI_TENANT_ID")
    auth_token = os.environ.get("WATI_AUTH_TOKEN")
    
    missing_vars = []
    if not api_url:
        missing_vars.append("WATI_API_BASE_URL")
    if not tenant_id:
        missing_vars.append("WATI_TENANT_ID")
    if not auth_token:
        missing_vars.append("WATI_AUTH_TOKEN")
    
    if missing_vars:
        print(f"❌ Missing environment variables: {', '.join(missing_vars)}")
        print("Please make sure these are set in the .env file.")
        return False
    
    # Check if tenant_id is valid (should be numeric)
    try:
        int(tenant_id)
    except ValueError:
        print(f"⚠️ Warning: Tenant ID should typically be numeric. Current value: {tenant_id}")
    
    print("✅ All required environment variables are set")
    return True

def main():
    """Run all tests."""
    print("=== Wati API Integration Test ===")
    print(f"API Base URL: {os.environ.get('WATI_API_BASE_URL', 'Not set')}")
    print(f"Tenant ID: {os.environ.get('WATI_TENANT_ID', 'Not set')}")
    print(f"Auth Token: {'Set' if os.environ.get('WATI_AUTH_TOKEN') else 'Not set'}")
    print("==============================")
    
    # Check environment variables
    if not check_env_vars():
        print("\n❌ Environment variable check failed. Exiting tests.")
        return
    
    # Check basic API connectivity
    check_api_connection()
    
    # Run the tests
    test_get_contacts()
    test_get_messages()
    test_send_message()
    
    print("\n=== Test Summary ===")
    print("Please check the logs above for detailed information.")
    print("If you're seeing errors, verify:")
    print("1. Your API credentials in the .env file")
    print("2. The API base URL is correct")
    print("3. Your Wati account is active and properly configured")
    print("4. Your network can reach the Wati API servers")

if __name__ == "__main__":
    main() 