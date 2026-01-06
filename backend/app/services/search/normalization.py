"""
Enhanced query normalization service.

According to SEARCH_DESIGN.md:
- Phase 2.2: Query Normalization
- Lowercase, trim whitespace, remove punctuation
- Expand abbreviations (e.g., "tv" → "television")
"""
import os
import re
import json
from pathlib import Path
from typing import Dict, Optional

from app.core.logging import get_logger

logger = get_logger(__name__)

# Default abbreviation dictionary path
DEFAULT_ABBREVIATION_DICT_PATH = Path(__file__).parent.parent.parent.parent / "data" / "abbreviations.json"


class QueryNormalizationService:
    """
    Enhanced query normalization service.
    
    Performs:
    - Lowercase conversion
    - Whitespace normalization
    - Punctuation removal (except hyphens in product names)
    - Abbreviation expansion
    """
    
    def __init__(self, abbreviation_dict_path: Optional[Path] = None):
        """
        Initialize query normalization service.
        
        Args:
            abbreviation_dict_path: Path to abbreviation dictionary JSON file
        """
        self.abbreviation_dict_path = abbreviation_dict_path or DEFAULT_ABBREVIATION_DICT_PATH
        self.abbreviations: Dict[str, str] = {}
        self._is_initialized = False
    
    def initialize(self) -> bool:
        """
        Load abbreviation dictionary from JSON file.
        
        Returns:
            True if initialization successful, False otherwise
        """
        if self._is_initialized:
            return True
        
        try:
            logger.info(
                "query_normalization_loading",
                path=str(self.abbreviation_dict_path),
            )
            
            if not self.abbreviation_dict_path.exists():
                logger.warning(
                    "query_normalization_dict_not_found",
                    path=str(self.abbreviation_dict_path),
                    message="Abbreviation expansion will be disabled",
                )
                self.abbreviations = {}
                self._is_initialized = True
                return True
            
            with open(self.abbreviation_dict_path, 'r', encoding='utf-8') as f:
                abbreviations = json.load(f)
            
            # Validate structure
            if not isinstance(abbreviations, dict):
                logger.error(
                    "query_normalization_invalid_dict",
                    message="Abbreviation dictionary must be a JSON object",
                )
                self.abbreviations = {}
                self._is_initialized = True
                return False
            
            # Normalize keys to lowercase
            self.abbreviations = {k.lower(): v.lower() for k, v in abbreviations.items()}
            
            self._is_initialized = True
            logger.info(
                "query_normalization_loaded",
                abbreviation_count=len(self.abbreviations),
            )
            return True
            
        except json.JSONDecodeError as e:
            logger.error(
                "query_normalization_json_error",
                path=str(self.abbreviation_dict_path),
                error=str(e),
                message="Invalid JSON in abbreviation dictionary",
            )
            self.abbreviations = {}
            self._is_initialized = True
            return False
        except Exception as e:
            logger.error(
                "query_normalization_load_failed",
                path=str(self.abbreviation_dict_path),
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True,
            )
            self.abbreviations = {}
            self._is_initialized = True
            return False
    
    def normalize(self, query: str, expand_abbreviations: bool = True) -> str:
        """
        Normalize query string.
        
        Steps:
        1. Lowercase
        2. Trim whitespace
        3. Remove punctuation (except hyphens)
        4. Expand abbreviations (if enabled)
        5. Normalize whitespace
        
        Args:
            query: Raw search query
            expand_abbreviations: Whether to expand abbreviations (default: True)
            
        Returns:
            Normalized query string
        """
        if not query:
            return ""
        
        if not self._is_initialized:
            self.initialize()
        
        # Step 1: Lowercase
        normalized = query.lower()
        
        # Step 2: Remove punctuation (except hyphens and spaces)
        # Keep hyphens for product names like "air-max"
        normalized = re.sub(r'[^\w\s-]', ' ', normalized)
        
        # Step 3: Replace multiple spaces/hyphens with single space
        normalized = re.sub(r'[\s-]+', ' ', normalized)
        
        # Step 4: Trim whitespace
        normalized = normalized.strip()
        
        # Step 5: Expand abbreviations (if enabled)
        if expand_abbreviations and self.abbreviations:
            words = normalized.split()
            expanded_words = []
            
            for word in words:
                # Check if word is an abbreviation
                expansion = self.abbreviations.get(word)
                if expansion and expansion != word:
                    # Expand abbreviation
                    expanded_words.append(expansion)
                else:
                    # Keep original word
                    expanded_words.append(word)
            
            normalized = " ".join(expanded_words)
        
        return normalized
    
    def is_available(self) -> bool:
        """
        Check if normalization service is available.
        
        Returns:
            True if service is initialized, False otherwise
        """
        if not self._is_initialized:
            self.initialize()
        return self._is_initialized


# Global service instance (singleton pattern)
_normalization_service: Optional[QueryNormalizationService] = None


def get_normalization_service() -> QueryNormalizationService:
    """
    Get global normalization service instance.
    
    Returns:
        QueryNormalizationService instance
    """
    global _normalization_service
    
    if _normalization_service is None:
        abbreviation_dict_path = os.getenv("QUERY_ABBREVIATION_DICT_PATH")
        
        if abbreviation_dict_path:
            abbreviation_dict_path = Path(abbreviation_dict_path)
        else:
            abbreviation_dict_path = DEFAULT_ABBREVIATION_DICT_PATH
        
        _normalization_service = QueryNormalizationService(
            abbreviation_dict_path=abbreviation_dict_path,
        )
        
        _normalization_service.initialize()
    
    return _normalization_service

