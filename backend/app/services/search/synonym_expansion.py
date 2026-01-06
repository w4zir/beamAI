"""
Synonym expansion service.

According to SEARCH_DESIGN.md:
- Phase 2.2: Synonym Expansion
- OR expansion strategy: "sneakers" → "sneakers OR running shoes OR trainers"
- Boost original term (1.0) vs synonyms (0.8)
- Limit: max 3-5 synonyms per term
"""
import os
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional

from app.core.logging import get_logger

logger = get_logger(__name__)

# Default configuration
DEFAULT_MAX_SYNONYMS = 5
DEFAULT_SYNONYM_BOOST = 0.8
DEFAULT_SYNONYM_DICT_PATH = Path(__file__).parent.parent.parent.parent / "data" / "synonyms.json"


class SynonymExpansionService:
    """
    Synonym expansion service.
    
    Expands query terms with synonyms using OR expansion strategy.
    Original terms get boost 1.0, synonyms get boost 0.8.
    """
    
    def __init__(
        self,
        synonym_dict_path: Optional[Path] = None,
        max_synonyms: int = DEFAULT_MAX_SYNONYMS,
        synonym_boost: float = DEFAULT_SYNONYM_BOOST,
    ):
        """
        Initialize synonym expansion service.
        
        Args:
            synonym_dict_path: Path to synonym dictionary JSON file
            max_synonyms: Maximum number of synonyms per term (default: 5)
            synonym_boost: Boost score for synonyms (default: 0.8)
        """
        self.synonym_dict_path = synonym_dict_path or DEFAULT_SYNONYM_DICT_PATH
        self.max_synonyms = max_synonyms
        self.synonym_boost = synonym_boost
        self.synonym_dict: Dict[str, List[str]] = {}
        self._is_initialized = False
    
    def initialize(self) -> bool:
        """
        Load synonym dictionary from JSON file.
        
        Returns:
            True if initialization successful, False otherwise
        """
        if self._is_initialized:
            return True
        
        try:
            logger.info(
                "synonym_expansion_loading",
                path=str(self.synonym_dict_path),
            )
            
            if not self.synonym_dict_path.exists():
                logger.warning(
                    "synonym_expansion_dict_not_found",
                    path=str(self.synonym_dict_path),
                    message="Synonym expansion will be disabled",
                )
                self.synonym_dict = {}
                self._is_initialized = True  # Mark as initialized even if empty
                return True
            
            with open(self.synonym_dict_path, 'r', encoding='utf-8') as f:
                self.synonym_dict = json.load(f)
            
            # Validate structure
            if not isinstance(self.synonym_dict, dict):
                logger.error(
                    "synonym_expansion_invalid_dict",
                    message="Synonym dictionary must be a JSON object",
                )
                self.synonym_dict = {}
                self._is_initialized = True
                return False
            
            # Normalize keys to lowercase for case-insensitive matching
            normalized_dict = {}
            for key, synonyms in self.synonym_dict.items():
                if isinstance(synonyms, list):
                    normalized_dict[key.lower()] = [s.lower() for s in synonyms if isinstance(s, str)]
            
            self.synonym_dict = normalized_dict
            
            self._is_initialized = True
            logger.info(
                "synonym_expansion_loaded",
                synonym_count=len(self.synonym_dict),
                max_synonyms=self.max_synonyms,
            )
            return True
            
        except json.JSONDecodeError as e:
            logger.error(
                "synonym_expansion_json_error",
                path=str(self.synonym_dict_path),
                error=str(e),
                message="Invalid JSON in synonym dictionary",
            )
            self.synonym_dict = {}
            self._is_initialized = True
            return False
        except Exception as e:
            logger.error(
                "synonym_expansion_load_failed",
                path=str(self.synonym_dict_path),
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True,
            )
            self.synonym_dict = {}
            self._is_initialized = True
            return False
    
    def expand(self, query: str) -> Tuple[str, List[str], bool]:
        """
        Expand query with synonyms using OR expansion strategy.
        
        Args:
            query: Original query string
            
        Returns:
            Tuple of (expanded_query, expanded_terms, expanded)
            - expanded_query: Query with synonyms (OR expansion format)
            - expanded_terms: List of terms that were expanded
            - expanded: Whether any expansion occurred
        """
        if not self._is_initialized:
            self.initialize()
        
        if not query or not query.strip():
            return query, [], False
        
        # Split query into words
        words = query.lower().split()
        expanded_parts = []
        expanded_terms = []
        
        for word in words:
            # Check if word has synonyms
            synonyms = self.synonym_dict.get(word, [])
            
            if synonyms:
                # Limit synonyms
                limited_synonyms = synonyms[:self.max_synonyms]
                
                # Build OR expansion: "word OR synonym1 OR synonym2 ..."
                # Original term comes first (boost 1.0)
                expansion_parts = [word] + limited_synonyms
                expanded_query_part = " OR ".join(expansion_parts)
                expanded_parts.append(f"({expanded_query_part})")
                expanded_terms.append(word)
            else:
                # No synonyms, keep original word
                expanded_parts.append(word)
        
        # Build expanded query
        expanded_query = " ".join(expanded_parts)
        
        # Determine if expansion occurred
        expanded = len(expanded_terms) > 0
        
        return expanded_query, expanded_terms, expanded
    
    def get_synonyms(self, term: str) -> List[str]:
        """
        Get synonyms for a term.
        
        Args:
            term: Term to get synonyms for
            
        Returns:
            List of synonyms (limited to max_synonyms)
        """
        if not self._is_initialized:
            self.initialize()
        
        synonyms = self.synonym_dict.get(term.lower(), [])
        return synonyms[:self.max_synonyms]
    
    def is_available(self) -> bool:
        """
        Check if synonym expansion service is available.
        
        Returns:
            True if service is initialized and has synonyms, False otherwise
        """
        if not self._is_initialized:
            self.initialize()
        return len(self.synonym_dict) > 0


# Global service instance (singleton pattern)
_synonym_expansion_service: Optional[SynonymExpansionService] = None


def get_synonym_expansion_service() -> Optional[SynonymExpansionService]:
    """
    Get global synonym expansion service instance.
    
    Returns:
        SynonymExpansionService instance or None if unavailable
    """
    global _synonym_expansion_service
    
    if _synonym_expansion_service is None:
        # Get configuration from environment
        max_synonyms = int(os.getenv("QUERY_MAX_SYNONYMS", str(DEFAULT_MAX_SYNONYMS)))
        synonym_dict_path = os.getenv("QUERY_SYNONYM_DICT_PATH")
        
        if synonym_dict_path:
            synonym_dict_path = Path(synonym_dict_path)
        else:
            synonym_dict_path = DEFAULT_SYNONYM_DICT_PATH
        
        _synonym_expansion_service = SynonymExpansionService(
            synonym_dict_path=synonym_dict_path,
            max_synonyms=max_synonyms,
        )
        
        # Initialize
        _synonym_expansion_service.initialize()
    
    return _synonym_expansion_service if _synonym_expansion_service.is_available() else None

