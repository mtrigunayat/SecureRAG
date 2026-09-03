#!/usr/bin/env python3
"""
Quick verification script for MCP server infrastructure.

Tests:
1. Health endpoint
2. OAuth metadata discovery
3. MCP initialize (no auth)
4. Error handling for missing token

Run with: python verify_mcp_server.py
"""
import asyncio
import json
import httpx
import sys
from pathlib import Path

# Add mcp-server to path
sys.path.insert(0, str(Path(__file__).parent / "mcp-server" / "src"))

BASE_URL = "http://localhost:5000"
TIMEOUT = 5.0


async def test_health():
    """Test health endpoint."""
    print("\n" + "="*60)
    print("TEST 1: Health Endpoint")
    print("="*60)
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{BASE_URL}/health",
                timeout=TIMEOUT
            )
            print(f"Status: {response.status_code}")
            print(f"Response: {json.dumps(response.json(), indent=2)}")
            
            if response.status_code == 200:
                print("✅ PASS: Health endpoint works")
                return True
            else:
                print("❌ FAIL: Unexpected status code")
                return False
    except Exception as e:
        print(f"❌ FAIL: {e}")
        return False


async def test_oauth_metadata():
    """Test OAuth discovery endpoint."""
    print("\n" + "="*60)
    print("TEST 2: OAuth Metadata Discovery")
    print("="*60)
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{BASE_URL}/.well-known/oauth-authorization-server",
                timeout=TIMEOUT
            )
            print(f"Status: {response.status_code}")
            data = response.json()
            print(f"Response keys: {list(data.keys())}")
            print(f"  - issuer: {data.get('issuer')}")
            print(f"  - token_endpoint: {data.get('token_endpoint')}")
            print(f"  - authorization_endpoint: {data.get('authorization_endpoint')}")
            
            required_keys = ['issuer', 'token_endpoint', 'authorization_endpoint']
            if all(k in data for k in required_keys):
                print("✅ PASS: OAuth metadata endpoint works")
                return True
            else:
                missing = [k for k in required_keys if k not in data]
                print(f"❌ FAIL: Missing keys: {missing}")
                return False
    except Exception as e:
        print(f"❌ FAIL: {e}")
        return False


async def test_mcp_initialize():
    """Test MCP initialize request (no auth)."""
    print("\n" + "="*60)
    print("TEST 3: MCP Initialize (No Auth)")
    print("="*60)
    
    request_body = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {
                "name": "verify-test",
                "version": "1.0"
            }
        }
    }
    
    print(f"Request method: initialize")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BASE_URL}/mcp",
                json=request_body,
                timeout=TIMEOUT
            )
            print(f"Status: {response.status_code}")
            data = response.json()
            
            if "error" in data:
                print(f"Response error: {data['error']}")
                print("❌ FAIL: Initialization failed")
                return False
            
            if "result" in data:
                result = data["result"]
                print(f"Response result keys: {list(result.keys())}")
                print(f"  - protocolVersion: {result.get('protocolVersion')}")
                print(f"  - serverInfo.name: {result.get('serverInfo', {}).get('name')}")
                print("✅ PASS: Initialize request works")
                return True
            
            print("❌ FAIL: No error or result in response")
            print(f"Full response: {json.dumps(data, indent=2)}")
            return False
    except Exception as e:
        print(f"❌ FAIL: {e}")
        return False


async def test_mcp_unauthorized():
    """Test that tools/list requires auth."""
    print("\n" + "="*60)
    print("TEST 4: MCP tools/list Without Auth (Should Fail)")
    print("="*60)
    
    request_body = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list",
        "params": {}
    }
    
    print(f"Request method: tools/list (no Authorization header)")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BASE_URL}/mcp",
                json=request_body,
                timeout=TIMEOUT
            )
            print(f"Status: {response.status_code}")
            
            if response.status_code == 401:
                print(f"Response: {json.dumps(response.json(), indent=2)}")
                print("✅ PASS: Unauthorized request properly rejected")
                return True
            else:
                data = response.json()
                if "error" in data:
                    print(f"Response error: {data['error']}")
                    print("✅ PASS: tools/list rejected (with error response)")
                    return True
                else:
                    print(f"❌ FAIL: Request should have been rejected")
                    print(f"Full response: {json.dumps(data, indent=2)}")
                    return False
    except Exception as e:
        print(f"❌ FAIL: {e}")
        return False


async def test_mcp_with_invalid_token():
    """Test that invalid token is rejected."""
    print("\n" + "="*60)
    print("TEST 5: MCP tools/list With Invalid Token (Should Fail)")
    print("="*60)
    
    request_body = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/list",
        "params": {}
    }
    
    print(f"Request method: tools/list with Authorization: Bearer invalid_token")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BASE_URL}/mcp",
                json=request_body,
                headers={"Authorization": "Bearer invalid_token_12345"},
                timeout=TIMEOUT
            )
            print(f"Status: {response.status_code}")
            
            if response.status_code in [401, 400, 403]:
                print(f"Response: {json.dumps(response.json(), indent=2)}")
                print("✅ PASS: Invalid token properly rejected")
                return True
            else:
                data = response.json()
                if "error" in data:
                    print(f"Response error: {data['error']}")
                    print("✅ PASS: Invalid token rejected (with error response)")
                    return True
                else:
                    print(f"❌ FAIL: Invalid token should have been rejected")
                    return False
    except Exception as e:
        print(f"❌ FAIL: {e}")
        return False


async def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("MCP SERVER INFRASTRUCTURE VERIFICATION")
    print("="*60)
    print(f"Target: {BASE_URL}")
    print("Note: Make sure server is running on localhost:5000")
    
    results = []
    
    try:
        results.append(("Health Endpoint", await test_health()))
        results.append(("OAuth Metadata", await test_oauth_metadata()))
        results.append(("MCP Initialize", await test_mcp_initialize()))
        results.append(("Unauthorized Request", await test_mcp_unauthorized()))
        results.append(("Invalid Token", await test_mcp_with_invalid_token()))
    except KeyboardInterrupt:
        print("\n\nTests interrupted by user")
        return 1
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All infrastructure tests passed!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
