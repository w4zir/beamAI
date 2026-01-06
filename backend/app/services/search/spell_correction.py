"""
Spell correction service using SymSpell.

According to SEARCH_DESIGN.md:
- Phase 2.2: Spell Correction
- Use SymSpell library
- Max edit distance: 2
- Confidence threshold: >80%
- Dictionary built from product names, categories, and common search terms
"""
import os
import re
from typing import Optional, Tuple, List
from pathlib import Path
from symspellpy import SymSpell, Verbosity

from app.core.logging import get_logger
from app.core.database import get_supabase_client

logger = get_logger(__name__)

# Default configuration
DEFAULT_MAX_EDIT_DISTANCE = 2
DEFAULT_CONFIDENCE_THRESHOLD = 0.8


class SpellCorrectionService:
    """
    Spell correction service using SymSpell.
    
    Builds dictionary from product names, categories, and common search terms.
    Only applies corrections with confidence > threshold.
    """
    
    def __init__(
        self,
        max_edit_distance: int = DEFAULT_MAX_EDIT_DISTANCE,
        confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
    ):
        """
        Initialize spell correction service.
        
        Args:
            max_edit_distance: Maximum edit distance for spell correction (default: 2)
            confidence_threshold: Minimum confidence to apply correction (default: 0.8)
        """
        self.max_edit_distance = max_edit_distance
        self.confidence_threshold = confidence_threshold
        self.sym_spell: Optional[SymSpell] = None
        self._is_initialized = False
    
    def initialize(self) -> bool:
        """
        Initialize spell checker by building dictionary from products.
        
        Returns:
            True if initialization successful, False otherwise
        """
        if self._is_initialized and self.sym_spell is not None:
            return True
        
        try:
            logger.info("spell_correction_initializing")
            
            # Create SymSpell instance
            self.sym_spell = SymSpell(max_dictionary_edit_distance=self.max_edit_distance)
            
            # Build dictionary from products
            dictionary_words = self._build_dictionary_from_products()
            
            if not dictionary_words:
                logger.warning("spell_correction_no_dictionary_words")
                return False
            
            # Add words to dictionary
            # SymSpell expects: word, frequency (we use 1 for all words)
            for word in dictionary_words:
                # Add word with frequency 1
                # SymSpell's create_dictionary expects lowercase words
                self.sym_spell.create_dictionary_entry(word.lower(), 1)
            
            self._is_initialized = True
            logger.info(
                "spell_correction_initialized",
                dictionary_size=len(dictionary_words),
                max_edit_distance=self.max_edit_distance,
            )
            return True
            
        except Exception as e:
            logger.error(
                "spell_correction_initialization_failed",
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True,
            )
            self.sym_spell = None
            self._is_initialized = False
            return False
    
    def _build_dictionary_from_products(self) -> List[str]:
        """
        Build dictionary from product names, categories, and common search terms.
        
        Returns:
            List of unique words for dictionary
        """
        words = set()
        
        # Common search terms (domain-specific)
        common_terms = [
            "running", "shoes", "sneakers", "trainers", "athletic",
            "laptop", "notebook", "computer", "phone", "smartphone",
            "headphones", "earphones", "earbuds", "watch", "smart",
            "wireless", "bluetooth", "charging", "cable", "usb",
            "jacket", "coat", "shirt", "jeans", "dress", "bag",
            "tablet", "mouse", "keyboard", "monitor", "display",
            "speaker", "charger", "power", "bank", "battery",
            "buy", "cheap", "discount", "sale", "best", "top",
            "new", "latest", "popular", "rated", "review",
        ]
        
        for term in common_terms:
            # Split multi-word terms
            words.update(term.lower().split())
        
        # Load words from products
        client = get_supabase_client()
        if not client:
            logger.warning("spell_correction_db_unavailable")
            return list(words)
        
        try:
            # Fetch product names and categories
            response = client.table("products").select("name, category").execute()
            
            if response.data:
                for product in response.data:
                    # Extract words from product name
                    name = product.get("name", "")
                    if name:
                        name_words = self._extract_words(name)
                        words.update(name_words)
                    
                    # Extract words from category
                    category = product.get("category", "")
                    if category:
                        category_words = self._extract_words(category)
                        words.update(category_words)
            
            logger.info(
                "spell_correction_dictionary_built",
                total_words=len(words),
                products_processed=len(response.data) if response.data else 0,
            )
            
        except Exception as e:
            logger.warning(
                "spell_correction_dictionary_build_partial",
                error=str(e),
                error_type=type(e).__name__,
                message="Using common terms only",
            )
        
        return list(words)
    
    def _extract_words(self, text: str) -> List[str]:
        """
        Extract words from text (alphanumeric only, lowercase).
        
        Args:
            text: Input text
            
        Returns:
            List of words
        """
        if not text:
            return []
        
        # Convert to lowercase and extract words
        words = re.findall(r'\b[a-z0-9]+\b', text.lower())
        return words
    
    def correct(self, query: str) -> Tuple[str, float, bool]:
        """
        Correct spelling errors in query.
        
        Args:
            query: Original query string
            
        Returns:
            Tuple of (corrected_query, confidence, applied)
            - corrected_query: Corrected query (or original if no correction applied)
            - confidence: Confidence score (0.0 to 1.0)
            - applied: Whether correction was applied (confidence > threshold)
        """
        if not self._is_initialized or self.sym_spell is None:
            # If not initialized, return original query
            return query, 0.0, False
        
        if not query or not query.strip():
            return query, 0.0, False
        
        try:
            # Split query into words
            words = query.split()
            corrected_words = []
            total_confidence = 0.0
            corrections_applied = 0
            
            for word in words:
                # Check if word needs correction
                suggestions = self.sym_spell.lookup(
                    word.lower(),
                    Verbosity.CLOSEST,
                    max_edit_distance=self.max_edit_distance,
                )
                
                if suggestions:
                    # Get best suggestion
                    best_suggestion = suggestions[0]
                    original_word = word.lower()
                    suggested_word = best_suggestion.term
                    distance = best_suggestion.distance
                    
                    # Calculate confidence
                    # Confidence decreases with edit distance
                    # For distance 0: confidence = 1.0 (exact match, no correction needed)
                    # For distance 1: confidence = 0.9
                    # For distance 2: confidence = 0.8
                    if distance == 0:
                        # Exact match, no correction needed
                        confidence = 1.0
                        corrected_words.append(word)  # Keep original casing
                    else:
                        # Calculate confidence based on edit distance
                        confidence = 1.0 - (distance * 0.1)
                        
                        # Only apply if confidence > threshold
                        if confidence > self.confidence_threshold:
                            # Use suggested word but try to preserve casing
                            if word[0].isupper():
                                suggested_word = suggested_word.capitalize()
                            corrected_words.append(suggested_word)
                            corrections_applied += 1
                        else:
                            # Confidence too low, keep original
                            corrected_words.append(word)
                            confidence = 0.0
                    total_confidence += confidence
                else:
                    # No suggestions found, keep original word
                    corrected_words.append(word)
                    total_confidence += 1.0  # Assume correct if no suggestions
            
            # Calculate average confidence
            avg_confidence = total_confidence / len(words) if words else 0.0
            
            # Build corrected query
            corrected_query = " ".join(corrected_words)
            
            # Determine if any corrections were applied
            applied = corrections_applied > 0 and avg_confidence > self.confidence_threshold
            
            return corrected_query, avg_confidence, applied
            
        except Exception as e:
            logger.warning(
                "spell_correction_error",
                query=query,
                error=str(e),
                error_type=type(e).__name__,
            )
            # On error, return original query
            return query, 0.0, False
    
    def is_available(self) -> bool:
        """
        Check if spell correction service is available.
        
        Returns:
            True if service is initialized and ready, False otherwise
        """
        return self._is_initialized and self.sym_spell is not None


# Global service instance (singleton pattern)
_spell_correction_service: Optional[SpellCorrectionService] = None


def get_spell_correction_service() -> Optional[SpellCorrectionService]:
    """
    Get global spell correction service instance.
    
    Returns:
        SpellCorrectionService instance or None if unavailable
    """
    global _spell_correction_service
    
    if _spell_correction_service is None:
        # Initialize service
        max_edit_distance = int(os.getenv("QUERY_SPELL_CORRECTION_MAX_EDIT_DISTANCE", str(DEFAULT_MAX_EDIT_DISTANCE)))
        confidence_threshold = float(os.getenv("QUERY_SPELL_CORRECTION_THRESHOLD", str(DEFAULT_CONFIDENCE_THRESHOLD)))
        
        _spell_correction_service = SpellCorrectionService(
            max_edit_distance=max_edit_distance,
            confidence_threshold=confidence_threshold,
        )
        
        # Initialize dictionary
        _spell_correction_service.initialize()
    
    return _spell_correction_service if _spell_correction_service.is_available() else None

