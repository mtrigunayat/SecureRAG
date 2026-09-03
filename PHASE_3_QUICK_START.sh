#!/bin/bash
# Phase 3 - Quick Start Guide
# Run this to set up and test Phase 3

echo "======================================================"
echo "PHASE 3: QUICK START - CLAUDE MCP INTEGRATION"
echo "======================================================"
echo ""

# Check if services are running
echo "🔍 Checking service status..."
echo ""

if lsof -i :8000 > /dev/null; then
    echo "✓ Backend is running on port 8000"
else
    echo "✗ Backend NOT running on port 8000"
    echo "  Start with: cd backend && python run.py"
fi

if lsof -i :5001 > /dev/null; then
    echo "✓ MCP Server is running on port 5001"
else
    echo "✗ MCP Server NOT running on port 5001"
    echo "  Start with: cd mcp-server && python run.py"
fi

echo ""
echo "======================================================"
echo "QUICK VALIDATION"
echo "======================================================"
echo ""

# Health checks
echo "Testing health endpoints..."

BACKEND_HEALTH=$(curl -s http://localhost:8000/health 2>/dev/null)
if [[ $BACKEND_HEALTH == *"ok"* ]]; then
    echo "✓ Backend health: OK"
else
    echo "✗ Backend health: FAILED"
fi

MCP_HEALTH=$(curl -s http://localhost:5001/health 2>/dev/null)
if [[ $MCP_HEALTH == *"ok"* ]]; then
    echo "✓ MCP Server health: OK"
else
    echo "✗ MCP Server health: FAILED"
fi

echo ""
echo "======================================================"
echo "TOKEN INFORMATION"
echo "======================================================"
echo ""
echo "Engineering Token (Pre-generated):"
echo "  mcp_TLDwkbdblkYWEnNPXahwk4bhXmJFZfFS97Xtz758sIw"
echo ""
echo "To generate tokens for other departments:"
echo "  cd backend"
echo "  python -m scripts.mcp_token_manager --action create --user-id 2 --description 'Claude: Sales'"
echo "  python -m scripts.mcp_token_manager --action create --user-id 3 --description 'Claude: HR'"
echo ""

echo "======================================================"
echo "NEXT STEPS"
echo "======================================================"
echo ""
echo "1. Read the integration guide:"
echo "   docs/PHASE_3_CLAUDE_INTEGRATION.md"
echo ""
echo "2. Run validation tests:"
echo "   cd backend && python tests/phase_3_acl_validation.py"
echo ""
echo "3. Configure Claude:"
echo "   - Go to Claude settings"
echo "   - Add MCP Server connection"
echo "   - URL: http://localhost:5001/mcp"
echo "   - Token: mcp_TLDwkbdblkYWEnNPXahwk4bhXmJFZfFS97Xtz758sIw"
echo ""
echo "4. Test in Claude:"
echo "   - Ask: 'What is company policy?'"
echo "   - Ask: 'Tell me about deployment guidelines'"
echo "   - Ask: 'Can you cite your sources?'"
echo ""
echo "======================================================"
echo "STATUS: Phase 3 Ready ✅"
echo "======================================================"
