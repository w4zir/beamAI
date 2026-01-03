"""
Test script to verify Supabase connection and database accessibility.
Run this script to check if your app can connect to Supabase successfully.
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
    print(f"Loaded environment from {env_path}")
else:
    print(f"Note: .env file not found at {env_path}")
    print("   Environment variables will be read from system environment")

from app.core.database import get_supabase_client


def test_connection():
    """Test Supabase connection and perform basic queries."""
    print("=" * 60)
    print("Testing Supabase Connection")
    print("=" * 60)
    print()
    
    # Step 1: Check environment variables
    print("Step 1: Checking environment variables...")
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")
    
    if not supabase_url:
        print("[X] SUPABASE_URL not found in environment variables")
        print("   Please set SUPABASE_URL in your .env file")
        return False
    else:
        print(f"[OK] SUPABASE_URL found: {supabase_url}")
    
    if not supabase_key:
        print("[X] SUPABASE_SERVICE_KEY not found in environment variables")
        print("   Please set SUPABASE_SERVICE_KEY in your .env file")
        return False
    else:
        # Show first and last few characters of key for security
        key_preview = f"{supabase_key[:8]}...{supabase_key[-8:]}" if len(supabase_key) > 16 else "***"
        print(f"[OK] SUPABASE_SERVICE_KEY found: {key_preview}")
    
    print()
    
    # Step 2: Create Supabase client
    print("Step 2: Creating Supabase client...")
    client = get_supabase_client()
    
    if not client:
        print("[X] Failed to create Supabase client")
        print("   Check your .env file configuration and Supabase instance status")
        return False
    
    print("[OK] Supabase client created successfully")
    print()
    
    # Step 3: Test database connection with a simple query
    print("Step 3: Testing database connection...")
    try:
        # Try to query a table that should exist (products)
        result = client.table('products').select('id').limit(1).execute()
        print(f"[OK] Database connection successful!")
        print(f"   Found {len(result.data)} product(s) in database")
        if result.data:
            print(f"   Sample product ID: {result.data[0].get('id', 'N/A')}")
    except Exception as e:
        print(f"[X] Database query failed: {e}")
        print("   This might mean:")
        print("   - Tables don't exist (run migrations)")
        print("   - Network connectivity issues")
        print("   - Invalid credentials")
        return False
    
    print()
    
    # Step 4: Check if required tables exist
    print("Step 4: Checking required tables...")
    required_tables = ['products', 'users', 'events']
    tables_found = []
    tables_missing = []
    
    for table in required_tables:
        try:
            result = client.table(table).select('id').limit(1).execute()
            tables_found.append(table)
            print(f"[OK] Table '{table}' exists")
        except Exception as e:
            tables_missing.append(table)
            print(f"[X] Table '{table}' not found or not accessible: {e}")
    
    print()
    
    # Summary
    print("=" * 60)
    print("Connection Test Summary")
    print("=" * 60)
    
    if tables_missing:
        print(f"[!] Warning: {len(tables_missing)} table(s) missing: {', '.join(tables_missing)}")
        print("   Run migrations to create missing tables:")
        print("   - supabase/migrations/001_create_tables.sql")
        print("   - supabase/migrations/002_create_fts_index.sql")
        print()
    
    if len(tables_found) == len(required_tables):
        print("[OK] All tests passed! Supabase connection is working correctly.")
        return True
    elif client:
        print("[OK] Supabase connection successful, but some tables are missing.")
        print("   Connection is working, but you may need to run migrations.")
        return True
    else:
        print("[X] Connection test failed. Please check your configuration.")
        return False


if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)

