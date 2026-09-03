#!/usr/bin/env python3
"""
Test MCP Server via HTTP (Postman-compatible)
Send JSON-RPC 2.0 requests to MCP server HTTP interface
"""

import asyncio
import httpx
import json

MCP_TOKEN = "mcp_734k-BXP25cJvvML9PC2LOqeDNLZI_KUDJG1s2QHaX4"
MCP_URL = "http://localhost:5000"

print("=" * 80)
print("MCP SERVER HTTP FLOW TEST (Postman-Compatible)")
print("=" * 80)

async def test_mcp_http():
    """Test MCP via HTTP JSON-RPC"""
    
    async with httpx.AsyncClient() as client:
        
        # Step 1: Test MCP Tools via JSON-RPC
        print("\n📝 TEST 1: Call MCP Tool via JSON-RPC")
        print("-" * 80)
        
        # JSON-RPC 2.0 request format
        rpc_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "ask_knowledge_base",
                "arguments": {
                    "question": "What is our deployment process?",
                    "mcp_token": MCP_TOKEN
                }
            }
        }
        
        print("Request Body:")
        print(json.dumps(rpc_request, indent=2))
        
        try:
            response = await client.post(
                f"{MCP_URL}/rpc",
                json=rpc_request,
                timeout=30
            )
            
            print(f"\n✅ Status: {response.status_code}")
            result = response.json()
            print(f"Response: {json.dumps(result, indent=2)[:500]}...")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            print("\nℹ️  If this fails, MCP might not have HTTP RPC enabled.")
            print("   Try Test 2 instead (Direct Python script)")

async def test_mcp_direct_http():
    """Alternative: Test if MCP exposes tools via HTTP"""
    
    print("\n📝 TEST 2: Query MCP Tools List")
    print("-" * 80)
    
    async with httpx.AsyncClient() as client:
        try:
            # Try JSON-RPC list tools
            rpc_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/list"
            }
            
            response = await client.post(
                f"{MCP_URL}/rpc",
                json=rpc_request,
                timeout=10
            )
            
            print(f"✅ Tools list: {response.status_code}")
            print(json.dumps(response.json(), indent=2))
            
        except Exception as e:
            print(f"⚠️  Could not list tools: {e}")

if __name__ == "__main__":
    asyncio.run(test_mcp_http())
    asyncio.run(test_mcp_direct_http())
