"""
Query enhancement orchestration service.

According to SEARCH_DESIGN.md and phase2_TODO_checklist.md:
- Phase 2.2: Query Enhancement
- Orchestrates: normalization, spell correction, synonym expansion, classification, intent extraction
"""
import time
from typing import Optional, Dict, List
from dataclasses import dataclass

from app.core.logging import get_logger
from app.services.search.normalization import get_normalization_service
from app.services.search.spell_correction import get_spell_correction_service
from app.services.search.synonym_expansion import get_synonym_expansion_service
from app.services.search.query_classification import (
    get_query_classification_service,
    QUERY_TYPE_NAVIGATIONAL,
    QUERY_TYPE_INFORMATIONAL,
    QUERY_TYPE_TRANSACTIONAL,
)
from app.services.search.intent_extraction import get_intent_extraction_service

logger = get_logger(__name__)


@dataclass
class EnhancedQuery:
    """
    Enhanced query result.
    
    Contains original query and all enhancement results.
    """
    original_query: str
    normalized_query: str
    corrected_query: Optional[str] = None
    corrected_confidence: float = 0.0
    correction_applied: bool = False
    expanded_query: Optional[str] = None
    expanded_terms: List[str] = None
    expansion_applied: bool = False
    classification: str = QUERY_TYPE_INFORMATIONAL
    entities: Dict = None
    enhancement_latency_ms: int = 0
    
    def __post_init__(self):
        """Initialize default values."""
        if self.expanded_terms is None:
            self.expanded_terms = []
        if self.entities is None:
            self.entities = {
                "brand": None,
                "category": None,
                "attributes": {
                    "color": None,
                    "size": None,
                    "other": [],
                },
            }
    
    def get_final_query(self) -> str:
        """
        Get final query to use for search.
        
        Priority:
        1. Expanded query (if synonym expansion applied)
        2. Corrected query (if spell correction applied)
        3. Normalized query (fallback)
        
        Returns:
            Final query string to use for search
        """
        if self.expanded_query:
            return self.expanded_query
        elif self.corrected_query:
            return self.corrected_query
        else:
            return self.normalized_query


class QueryEnhancementService:
    """
    Query enhancement orchestration service.
    
    Processes queries through:
    1. Normalization (lowercase, trim, remove punctuation, expand abbreviations)
    2. Spell Correction (if confidence > threshold)
    3. Synonym Expansion (OR expansion)
    4. Query Classification (navigational/informational/transactional)
    5. Intent Extraction (brand, category, attributes)
    """
    
    def __init__(
        self,
        enable_spell_correction: bool = True,
        enable_synonym_expansion: bool = True,
        enable_classification: bool = True,
        enable_intent_extraction: bool = True,
    ):
        """
        Initialize query enhancement service.
        
        Args:
            enable_spell_correction: Enable spell correction (default: True)
            enable_synonym_expansion: Enable synonym expansion (default: True)
            enable_classification: Enable query classification (default: True)
            enable_intent_extraction: Enable intent extraction (default: True)
        """
        self.enable_spell_correction = enable_spell_correction
        self.enable_synonym_expansion = enable_synonym_expansion
        self.enable_classification = enable_classification
        self.enable_intent_extraction = enable_intent_extraction
    
    def enhance(self, query: str) -> EnhancedQuery:
        """
        Enhance query through all processing steps.
        
        Args:
            query: Original search query
            
        Returns:
            EnhancedQuery object with all enhancement results
        """
        start_time = time.time()
        
        # Initialize result with temporary normalized_query (will be set properly below)
        enhanced = EnhancedQuery(original_query=query, normalized_query="")
        
        if not query or not query.strip():
            enhanced.normalized_query = ""
            enhanced.enhancement_latency_ms = int((time.time() - start_time) * 1000)
            return enhanced
        
        try:
            # Step 1: Normalization
            normalization_service = get_normalization_service()
            enhanced.normalized_query = normalization_service.normalize(query)
            
            # Use normalized query for subsequent steps
            current_query = enhanced.normalized_query
            
            # Step 2: Spell Correction
            if self.enable_spell_correction:
                spell_service = get_spell_correction_service()
                if spell_service and spell_service.is_available():
                    corrected_query, confidence, applied = spell_service.correct(current_query)
                    enhanced.corrected_query = corrected_query
                    enhanced.corrected_confidence = confidence
                    enhanced.correction_applied = applied
                    
                    if applied:
                        current_query = corrected_query
                        logger.debug(
                            "query_enhancement_spell_correction_applied",
                            original=enhanced.normalized_query,
                            corrected=corrected_query,
                            confidence=confidence,
                        )
            
            # Step 3: Synonym Expansion
            if self.enable_synonym_expansion:
                synonym_service = get_synonym_expansion_service()
                if synonym_service and synonym_service.is_available():
                    expanded_query, expanded_terms, expanded = synonym_service.expand(current_query)
                    enhanced.expanded_query = expanded_query
                    enhanced.expanded_terms = expanded_terms
                    enhanced.expansion_applied = expanded
                    
                    if expanded:
                        current_query = expanded_query
                        logger.debug(
                            "query_enhancement_synonym_expansion_applied",
                            original=enhanced.corrected_query or enhanced.normalized_query,
                            expanded=expanded_query,
                            terms=expanded_terms,
                        )
            
            # Step 4: Query Classification
            if self.enable_classification:
                classification_service = get_query_classification_service()
                if classification_service and classification_service.is_available():
                    enhanced.classification = classification_service.classify(query)
                    logger.debug(
                        "query_enhancement_classification",
                        query=query,
                        classification=enhanced.classification,
                    )
            
            # Step 5: Intent Extraction
            if self.enable_intent_extraction:
                intent_service = get_intent_extraction_service()
                if intent_service and intent_service.is_available():
                    enhanced.entities = intent_service.extract(query)
                    logger.debug(
                        "query_enhancement_intent_extraction",
                        query=query,
                        entities=enhanced.entities,
                    )
            
            enhanced.enhancement_latency_ms = int((time.time() - start_time) * 1000)
            
            logger.info(
                "query_enhancement_completed",
                original_query=query,
                final_query=enhanced.get_final_query(),
                classification=enhanced.classification,
                correction_applied=enhanced.correction_applied,
                expansion_applied=enhanced.expansion_applied,
                latency_ms=enhanced.enhancement_latency_ms,
            )
            
            return enhanced
            
        except Exception as e:
            logger.error(
                "query_enhancement_error",
                query=query,
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True,
            )
            # On error, return minimal enhancement (just normalization)
            enhanced.normalized_query = query.lower().strip()
            enhanced.enhancement_latency_ms = int((time.time() - start_time) * 1000)
            return enhanced


# Global service instance (singleton pattern)
_query_enhancement_service: Optional[QueryEnhancementService] = None


def get_query_enhancement_service() -> QueryEnhancementService:
    """
    Get global query enhancement service instance.
    
    Returns:
        QueryEnhancementService instance
    """
    global _query_enhancement_service
    
    if _query_enhancement_service is None:
        _query_enhancement_service = QueryEnhancementService()
    
    return _query_enhancement_service

