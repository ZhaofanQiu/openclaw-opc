#!/usr/bin/env python3
"""
Quick script to create a test API key for dashboard access.
"""

import os
import sys

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from src.database import SessionLocal, init_db
from src.services.api_key_service import APIKeyService


def create_test_key():
    """Create a test API key with full permissions."""
    init_db()
    db = SessionLocal()
    
    try:
        service = APIKeyService(db)
        
        # Create a key with read, write, admin permissions
        api_key, plain_key = service.create_key(
            name="Dashboard Access Key",
            permissions=["read", "write", "admin"],
            expires_days=365
        )
        
        print("=" * 60)
        print("✅ API Key 创建成功！")
        print("=" * 60)
        print(f"\n📝 Key 名称: {api_key.name}")
        print(f"🔑 Key ID: {api_key.id}")
        print(f"\n⚠️  请立即保存以下 API Key（只显示一次）:")
        print(f"\n   {plain_key}\n")
        print(f"权限: {api_key.permissions}")
        print(f"过期时间: {api_key.expires_at}")
        print("\n" + "=" * 60)
        print("使用方式:")
        print("  1. 打开 Dashboard: http://localhost/dashboard")
        print("  2. 输入上面的 API Key 登录")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ 创建失败: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    create_test_key()
