#!/usr/bin/env python
"""
MCP Token Management CLI

Utility for creating, listing, and revoking MCP tokens.

Usage:
    # Create token for user
    python -m scripts.mcp_token_manager --action create --user-id 1 --description "Claude personal"
    
    # List tokens for user
    python -m scripts.mcp_token_manager --action list --user-id 1
    
    # Revoke specific token
    python -m scripts.mcp_token_manager --action revoke --token-id 5
    
    # Revoke all tokens for user
    python -m scripts.mcp_token_manager --action revoke-all --user-id 1
"""
import sys
import argparse
from datetime import datetime

# Add backend directory to path
sys.path.insert(0, '/Users/mohittrigunayat/Desktop/personal/SecureRAG/backend')

from app.db.session import SessionLocal, engine, Base
from app.models import MCPToken, User
from app.services.mcp_token_service import (
    create_mcp_token_for_user,
    revoke_mcp_token,
    revoke_all_user_tokens,
    get_user_mcp_tokens,
    get_active_user_mcp_tokens
)


def create_token(user_id: int, description: str = None, created_via: str = "cli") -> None:
    """Create a new MCP token for a user."""
    db = SessionLocal()
    try:
        # Verify user exists
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            print(f"❌ Error: User {user_id} not found")
            return
        
        print(f"Creating MCP token for: {user.username} ({user.email})")
        
        # Generate token
        raw_token = create_mcp_token_for_user(
            user_id=user_id,
            db=db,
            description=description,
            created_via=created_via
        )
        
        print(f"\n✅ Token created successfully!\n")
        print(f"Token: {raw_token}")
        print(f"\n⚠️  IMPORTANT: Save this token securely. It will not be shown again.")
        print(f"   Store in: .env file, Anthropic platform, or secure credential manager\n")
        
    except Exception as e:
        print(f"❌ Error creating token: {e}")
    finally:
        db.close()


def list_tokens(user_id: int, active_only: bool = False) -> None:
    """List MCP tokens for a user."""
    db = SessionLocal()
    try:
        # Verify user exists
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            print(f"❌ Error: User {user_id} not found")
            return
        
        if active_only:
            tokens = get_active_user_mcp_tokens(user_id, db)
            print(f"\n📋 Active MCP tokens for {user.username}:\n")
        else:
            tokens = get_user_mcp_tokens(user_id, db)
            print(f"\n📋 All MCP tokens for {user.username}:\n")
        
        if not tokens:
            print("   (no tokens)")
            return
        
        for token in tokens:
            status = "✅ ACTIVE"
            if token.is_revoked():
                status = "❌ REVOKED"
            elif token.is_expired():
                status = "⏰ EXPIRED"
            
            desc = token.description or "(no description)"
            last_used = token.last_used_at.isoformat() if token.last_used_at else "never"
            
            print(f"   ID: {token.id}")
            print(f"   Status: {status}")
            print(f"   Description: {desc}")
            print(f"   Created: {token.created_at.isoformat()}")
            print(f"   Expires: {token.expires_at.isoformat()}")
            print(f"   Last Used: {last_used}")
            print()
        
    except Exception as e:
        print(f"❌ Error listing tokens: {e}")
    finally:
        db.close()


def revoke_token(token_id: int) -> None:
    """Revoke a specific MCP token."""
    db = SessionLocal()
    try:
        token = db.query(MCPToken).filter(MCPToken.id == token_id).first()
        if not token:
            print(f"❌ Error: Token {token_id} not found")
            return
        
        if token.is_revoked():
            print(f"ℹ️  Token {token_id} is already revoked")
            return
        
        success = revoke_mcp_token(token_id, db)
        if success:
            print(f"✅ Token {token_id} revoked successfully")
        else:
            print(f"❌ Failed to revoke token {token_id}")
        
    except Exception as e:
        print(f"❌ Error revoking token: {e}")
    finally:
        db.close()


def revoke_user_tokens(user_id: int) -> None:
    """Revoke all MCP tokens for a user."""
    db = SessionLocal()
    try:
        # Verify user exists
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            print(f"❌ Error: User {user_id} not found")
            return
        
        count = revoke_all_user_tokens(user_id, db)
        print(f"✅ Revoked {count} token(s) for {user.username}")
        
    except Exception as e:
        print(f"❌ Error revoking tokens: {e}")
    finally:
        db.close()


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="MCP Token Management CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Create token:     python -m scripts.mcp_token_manager --action create --user-id 1
  List tokens:      python -m scripts.mcp_token_manager --action list --user-id 1
  List active only: python -m scripts.mcp_token_manager --action list --user-id 1 --active
  Revoke token:     python -m scripts.mcp_token_manager --action revoke --token-id 5
  Revoke all:       python -m scripts.mcp_token_manager --action revoke-all --user-id 1
        """
    )
    
    parser.add_argument(
        "--action",
        required=True,
        choices=["create", "list", "revoke", "revoke-all"],
        help="Action to perform"
    )
    parser.add_argument(
        "--user-id",
        type=int,
        help="User ID (required for create, list, revoke-all)"
    )
    parser.add_argument(
        "--token-id",
        type=int,
        help="Token ID (required for revoke)"
    )
    parser.add_argument(
        "--description",
        type=str,
        help="Token description (optional for create)"
    )
    parser.add_argument(
        "--active",
        action="store_true",
        help="List only active tokens (optional for list)"
    )
    
    args = parser.parse_args()
    
    try:
        if args.action == "create":
            if not args.user_id:
                print("❌ Error: --user-id required for create action")
                sys.exit(1)
            create_token(args.user_id, args.description)
        
        elif args.action == "list":
            if not args.user_id:
                print("❌ Error: --user-id required for list action")
                sys.exit(1)
            list_tokens(args.user_id, args.active)
        
        elif args.action == "revoke":
            if not args.token_id:
                print("❌ Error: --token-id required for revoke action")
                sys.exit(1)
            revoke_token(args.token_id)
        
        elif args.action == "revoke-all":
            if not args.user_id:
                print("❌ Error: --user-id required for revoke-all action")
                sys.exit(1)
            revoke_user_tokens(args.user_id)
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
