"""
Query classification service.

According to SEARCH_DESIGN.md:
- Phase 2.2: Query Classification
- Classify queries as: navigational, informational, transactional
- Rule-based classification (will be enhanced by AI Phase 1)
"""
import re
from typing import Set, Optional, List
from app.core.logging import get_logger
from app.core.database import get_supabase_client

logger = get_logger(__name__)

# Query type constants
QUERY_TYPE_NAVIGATIONAL = "navigational"
QUERY_TYPE_INFORMATIONAL = "informational"
QUERY_TYPE_TRANSACTIONAL = "transactional"

# Purchase intent keywords
PURCHASE_INTENT_KEYWORDS = {
    "buy", "purchase", "order", "shop", "shopping",
    "cheap", "affordable", "budget", "discount", "sale",
    "price", "cost", "deal", "offer", "promotion",
    "where to buy", "where can i buy", "for sale",
}

# Question/informational keywords
QUESTION_KEYWORDS = {
    "what", "what is", "what are", "what's",
    "how", "how to", "how do", "how does",
    "why", "when", "where", "which",
    "best", "top", "recommended", "popular",
    "review", "reviews", "compare", "comparison",
    "difference", "differences", "vs", "versus",
}


class QueryClassificationService:
    """
    Query classification service.
    
    Classifies queries into:
    - Navigational: Specific product/brand search
    - Informational: General information search
    - Transactional: Purchase intent
    """
    
    def __init__(self):
        """Initialize query classification service."""
        self.brands: Set[str] = set()
        self._is_initialized = False
    
    def initialize(self) -> bool:
        """
        Load brand dictionary from products.
        
        Returns:
            True if initialization successful, False otherwise
        """
        if self._is_initialized:
            return True
        
        try:
            logger.info("query_classification_loading_brands")
            
            # Load brands from products
            client = get_supabase_client()
            if client:
                try:
                    # Fetch product names to extract brands
                    response = client.table("products").select("name").execute()
                    
                    if response.data:
                        for product in response.data:
                            name = product.get("name", "")
                            if name:
                                # Extract potential brand (first word, capitalized)
                                words = name.split()
                                if words:
                                    # Common brand patterns: first word if capitalized
                                    first_word = words[0]
                                    if first_word and first_word[0].isupper():
                                        self.brands.add(first_word.lower())
                    
                    logger.info(
                        "query_classification_brands_loaded",
                        brand_count=len(self.brands),
                    )
                except Exception as e:
                    logger.warning(
                        "query_classification_brand_load_failed",
                        error=str(e),
                        error_type=type(e).__name__,
                        message="Using empty brand dictionary",
                    )
            else:
                logger.warning(
                    "query_classification_db_unavailable",
                    message="Using empty brand dictionary",
                )
            
            self._is_initialized = True
            return True
            
        except Exception as e:
            logger.error(
                "query_classification_initialization_failed",
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True,
            )
            self._is_initialized = True  # Mark as initialized even if failed
            return False
    
    def classify(self, query: str) -> str:
        """
        Classify query into navigational, informational, or transactional.
        
        Args:
            query: Search query string
            
        Returns:
            Query type: "navigational", "informational", or "transactional"
        """
        if not self._is_initialized:
            self.initialize()
        
        if not query or not query.strip():
            return QUERY_TYPE_INFORMATIONAL
        
        query_lower = query.lower()
        query_words = set(query_lower.split())
        
        # Check for transactional intent (purchase keywords)
        if self._has_purchase_intent(query_lower, query_words):
            return QUERY_TYPE_TRANSACTIONAL
        
        # Check for informational intent (question words) BEFORE navigational
        # This ensures questions are classified as informational, not navigational
        if self._has_informational_intent(query_lower, query_words):
            return QUERY_TYPE_INFORMATIONAL
        
        # Check for navigational intent (brand + model pattern)
        if self._has_navigational_intent(query_lower, query_words):
            return QUERY_TYPE_NAVIGATIONAL
        
        # Default to informational
        return QUERY_TYPE_INFORMATIONAL
    
    def _has_purchase_intent(self, query_lower: str, query_words: Set[str]) -> bool:
        """
        Check if query has purchase intent.
        
        Args:
            query_lower: Lowercase query
            query_words: Set of query words
            
        Returns:
            True if query has purchase intent
        """
        # Check for purchase intent keywords
        for keyword in PURCHASE_INTENT_KEYWORDS:
            if keyword in query_lower:
                return True
        
        return False
    
    def _has_navigational_intent(self, query_lower: str, query_words: Set[str]) -> bool:
        """
        Check if query has navigational intent (specific product/brand search).
        
        Args:
            query_lower: Lowercase query
            query_words: Set of query words
            
        Returns:
            True if query has navigational intent
        """
        # Check if query contains a known brand
        for brand in self.brands:
            if brand in query_lower:
                # Brand found, likely navigational
                # Additional check: if query is short (2-4 words), more likely navigational
                word_count = len(query_lower.split())
                if word_count <= 4:
                    return True
        
        # Only check for brand-like patterns if we have brands loaded
        # This prevents generic queries from being misclassified as navigational
        if not self.brands:
            return False
        
        # Check for brand-like patterns (capitalized words at start)
        # Pattern: "Brand Model" or "Brand Product"
        # Only match if the first word could be a brand (short, alphanumeric, not a common word)
        words = query_lower.split()
        if len(words) >= 2:
            first_word = words[0]
            # Common words that shouldn't be treated as brands
            common_words = {"what", "how", "why", "when", "where", "which", "best", "top", 
                          "good", "cheap", "buy", "random", "search", "find", "get", "a", "an", "the"}
            
            # Only consider navigational if:
            # 1. First word is not a common word
            # 2. First word is short (typical brand length)
            # 3. Query is short (2-3 words, typical for brand+model)
            if (first_word not in common_words and 
                len(first_word) <= 10 and first_word.isalpha() and
                len(words) <= 3):
                second_word = words[1] if len(words) > 1 else ""
                if second_word and len(second_word) <= 15:
                    # Likely navigational: "brand model" pattern
                    return True
        
        return False
    
    def _has_informational_intent(self, query_lower: str, query_words: Set[str]) -> bool:
        """
        Check if query has informational intent.
        
        Args:
            query_lower: Lowercase query
            query_words: Set of query words
            
        Returns:
            True if query has informational intent
        """
        # Check for question keywords
        for keyword in QUESTION_KEYWORDS:
            if keyword in query_lower:
                return True
        
        # Check for question patterns
        if query_lower.startswith(("what", "how", "why", "when", "where", "which")):
            return True
        
        return False
    
    def is_available(self) -> bool:
        """
        Check if query classification service is available.
        
        Returns:
            True if service is initialized, False otherwise
        """
        if not self._is_initialized:
            self.initialize()
        return self._is_initialized


# Global service instance (singleton pattern)
_query_classification_service: Optional[QueryClassificationService] = None


def get_query_classification_service() -> Optional[QueryClassificationService]:
    """
    Get global query classification service instance.
    
    Returns:
        QueryClassificationService instance or None if unavailable
    """
    global _query_classification_service
    
    if _query_classification_service is None:
        _query_classification_service = QueryClassificationService()
        _query_classification_service.initialize()
    
    return _query_classification_service if _query_classification_service.is_available() else None

