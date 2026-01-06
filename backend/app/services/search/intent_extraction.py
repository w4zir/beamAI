"""
Intent extraction service (basic rule-based).

According to SEARCH_DESIGN.md:
- Phase 2.2: Intent Extraction (basic rule-based)
- Extract: brand, category, attributes
- Will be enhanced by AI Phase 1 LLM-powered extraction
"""
import re
from typing import Dict, List, Optional, Set
from app.core.logging import get_logger
from app.core.database import get_supabase_client

logger = get_logger(__name__)

# Common color keywords
COLOR_KEYWORDS = {
    "red", "blue", "green", "yellow", "orange", "purple", "pink",
    "black", "white", "gray", "grey", "brown", "beige", "navy",
    "silver", "gold", "bronze", "copper", "maroon", "teal",
}

# Common size keywords
SIZE_KEYWORDS = {
    "small", "medium", "large", "xl", "xxl", "xxxl",
    "xs", "s", "m", "l",
    "size", "sizes",
}

# Size patterns (e.g., "size 10", "10", "size M")
SIZE_PATTERN = re.compile(r'\b(size\s*)?(\d+|xs|s|m|l|xl|xxl|xxxl)\b', re.IGNORECASE)


class IntentExtractionService:
    """
    Basic rule-based intent extraction service.
    
    Extracts:
    - Brand: From known brands in products
    - Category: From known categories in products
    - Attributes: Color, size, etc.
    """
    
    def __init__(self):
        """Initialize intent extraction service."""
        self.brands: Set[str] = set()
        self.categories: Set[str] = set()
        self._is_initialized = False
    
    def initialize(self) -> bool:
        """
        Load brand and category dictionaries from products.
        
        Returns:
            True if initialization successful, False otherwise
        """
        if self._is_initialized:
            return True
        
        try:
            logger.info("intent_extraction_loading")
            
            # Load brands and categories from products
            client = get_supabase_client()
            if client:
                try:
                    response = client.table("products").select("name, category").execute()
                    
                    if response.data:
                        for product in response.data:
                            # Extract brand from product name (first word if capitalized)
                            name = product.get("name", "")
                            if name:
                                words = name.split()
                                if words:
                                    first_word = words[0]
                                    if first_word and first_word[0].isupper():
                                        self.brands.add(first_word.lower())
                            
                            # Extract category
                            category = product.get("category", "")
                            if category:
                                self.categories.add(category.lower())
                    
                    logger.info(
                        "intent_extraction_loaded",
                        brand_count=len(self.brands),
                        category_count=len(self.categories),
                    )
                except Exception as e:
                    logger.warning(
                        "intent_extraction_load_failed",
                        error=str(e),
                        error_type=type(e).__name__,
                        message="Using empty dictionaries",
                    )
            else:
                logger.warning(
                    "intent_extraction_db_unavailable",
                    message="Using empty dictionaries",
                )
            
            self._is_initialized = True
            return True
            
        except Exception as e:
            logger.error(
                "intent_extraction_initialization_failed",
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True,
            )
            self._is_initialized = True  # Mark as initialized even if failed
            return False
    
    def extract(self, query: str) -> Dict[str, any]:
        """
        Extract entities from query.
        
        Args:
            query: Search query string
            
        Returns:
            Dictionary with extracted entities:
            {
                "brand": Optional[str],
                "category": Optional[str],
                "attributes": {
                    "color": Optional[str],
                    "size": Optional[str],
                    "other": List[str]
                }
            }
        """
        if not self._is_initialized:
            self.initialize()
        
        if not query or not query.strip():
            return {
                "brand": None,
                "category": None,
                "attributes": {
                    "color": None,
                    "size": None,
                    "other": [],
                },
            }
        
        query_lower = query.lower()
        query_words = set(query_lower.split())
        
        # Extract brand
        brand = self._extract_brand(query_lower, query_words)
        
        # Extract category
        category = self._extract_category(query_lower, query_words)
        
        # Extract attributes
        attributes = self._extract_attributes(query_lower, query_words)
        
        return {
            "brand": brand,
            "category": category,
            "attributes": attributes,
        }
    
    def _extract_brand(self, query_lower: str, query_words: Set[str]) -> Optional[str]:
        """
        Extract brand from query.
        
        Args:
            query_lower: Lowercase query
            query_words: Set of query words
            
        Returns:
            Extracted brand or None
        """
        # Check if any known brand appears in query
        for brand in self.brands:
            if brand in query_lower:
                return brand
        
        # Check for brand-like patterns (capitalized first word)
        words = query_lower.split()
        if words:
            first_word = words[0]
            # If first word looks like a brand (short, alphabetic)
            if len(first_word) <= 15 and first_word.isalpha():
                return first_word
        
        return None
    
    def _extract_category(self, query_lower: str, query_words: Set[str]) -> Optional[str]:
        """
        Extract category from query.
        
        Args:
            query_lower: Lowercase query
            query_words: Set of query words
            
        Returns:
            Extracted category or None
        """
        # Check if any known category appears in query
        for category in self.categories:
            if category in query_lower:
                return category
        
        # Check for common category keywords
        category_keywords = {
            "shoes", "sneakers", "trainers", "footwear",
            "laptop", "notebook", "computer",
            "phone", "smartphone", "mobile",
            "headphones", "earphones", "earbuds",
            "watch", "timepiece",
            "jacket", "coat", "shirt", "jeans", "dress",
            "bag", "purse", "handbag",
            "tablet", "mouse", "keyboard", "monitor",
            "speaker", "charger", "cable",
        }
        
        for keyword in category_keywords:
            if keyword in query_lower:
                return keyword
        
        return None
    
    def _extract_attributes(self, query_lower: str, query_words: Set[str]) -> Dict[str, any]:
        """
        Extract attributes (color, size, etc.) from query.
        
        Args:
            query_lower: Lowercase query
            query_words: Set of query words
            
        Returns:
            Dictionary with extracted attributes
        """
        attributes = {
            "color": None,
            "size": None,
            "other": [],
        }
        
        # Extract color
        for color in COLOR_KEYWORDS:
            if color in query_words:
                attributes["color"] = color
                break
        
        # Extract size
        # Check for size keywords
        for size in SIZE_KEYWORDS:
            if size in query_words:
                attributes["size"] = size
                break
        
        # Check for size patterns (e.g., "size 10", "10")
        size_match = SIZE_PATTERN.search(query_lower)
        if size_match:
            size_value = size_match.group(2)  # Extract the size value
            attributes["size"] = size_value.lower()
        
        # Extract other attributes (wireless, bluetooth, etc.)
        other_attributes = {
            "wireless", "bluetooth", "usb", "usb-c", "usbc",
            "4k", "hd", "high definition",
            "smart", "touch", "waterproof", "water-resistant",
            "portable", "compact", "lightweight",
        }
        
        for attr in other_attributes:
            if attr in query_lower:
                attributes["other"].append(attr)
        
        return attributes
    
    def is_available(self) -> bool:
        """
        Check if intent extraction service is available.
        
        Returns:
            True if service is initialized, False otherwise
        """
        if not self._is_initialized:
            self.initialize()
        return self._is_initialized


# Global service instance (singleton pattern)
_intent_extraction_service: Optional[IntentExtractionService] = None


def get_intent_extraction_service() -> Optional[IntentExtractionService]:
    """
    Get global intent extraction service instance.
    
    Returns:
        IntentExtractionService instance or None if unavailable
    """
    global _intent_extraction_service
    
    if _intent_extraction_service is None:
        _intent_extraction_service = IntentExtractionService()
        _intent_extraction_service.initialize()
    
    return _intent_extraction_service if _intent_extraction_service.is_available() else None

