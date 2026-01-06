"""
Minimal database module for Supabase connection.
This is a placeholder - customize based on your needs.
"""
import os
from typing import Optional
from supabase import create_client, Client
from pathlib import Path
from dotenv import load_dotenv

from app.core.logging import get_logger

logger = get_logger(__name__)

# Load environment variables from .env file in root directory
env_path = Path(__file__).parent.parent.parent.parent / ".env"

if env_path.exists():
    load_dotenv(env_path)
    logger.info("env_loaded", env_path=str(env_path))
else:
    logger.warning("env_file_not_found", expected_path=str(env_path))


def get_supabase_client() -> Optional[Client]:
    """Create and return Supabase client instance."""
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")
    
    if not supabase_url or not supabase_key:
        logger.warning(
            "supabase_credentials_missing",
            message="Check SUPABASE_URL and SUPABASE_SERVICE_KEY in .env"
        )
        return None
    
    if not supabase_url.startswith("http"):
        logger.error(
            "supabase_url_invalid",
            url=supabase_url,
            message="Should start with http:// or https://"
        )
        return None
    
    try:
        logger.info("supabase_client_creating", url_prefix=supabase_url[:30])
        client = create_client(supabase_url, supabase_key)
        logger.info("supabase_client_created")
        return client
    except Exception as e:
        logger.error(
            "supabase_client_creation_failed",
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
        return None


class Database:
    """Database operations wrapper for Supabase."""
    
    def __init__(self):
        self.client = get_supabase_client()
        self._init_error = None
        
        if not self.client:
            try:
                supabase_url = os.getenv("SUPABASE_URL")
                supabase_key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")
                if supabase_url and supabase_key:
                    test_client = create_client(supabase_url, supabase_key)
            except Exception as e:
                self._init_error = str(e)
                logger.error(
                    "database_init_error",
                    error=str(e),
                    error_type=type(e).__name__,
                    exc_info=True,
                )


# Global database instance
db = Database()
