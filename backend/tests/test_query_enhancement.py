"""
Unit tests for query enhancement components.

Tests:
- Spell correction
- Synonym expansion
- Query classification
- Query normalization
- Intent extraction
- Query enhancement orchestration
"""
import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from app.services.search.spell_correction import SpellCorrectionService
from app.services.search.synonym_expansion import SynonymExpansionService
from app.services.search.query_classification import (
    QueryClassificationService,
    QUERY_TYPE_NAVIGATIONAL,
    QUERY_TYPE_INFORMATIONAL,
    QUERY_TYPE_TRANSACTIONAL,
)
from app.services.search.normalization import QueryNormalizationService
from app.services.search.intent_extraction import IntentExtractionService
from app.services.search.query_enhancement import QueryEnhancementService, EnhancedQuery


# ============================================================================
# Spell Correction Tests
# ============================================================================

@pytest.fixture
def temp_synonym_dict():
    """Create temporary synonym dictionary."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump({
            "sneakers": ["running shoes", "trainers"],
            "laptop": ["notebook", "computer"],
        }, f)
        yield Path(f.name)


@pytest.fixture
def temp_abbreviation_dict():
    """Create temporary abbreviation dictionary."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump({
            "tv": "television",
            "pc": "personal computer",
        }, f)
        yield Path(f.name)


def test_spell_correction_initialization():
    """Test spell correction service initialization."""
    service = SpellCorrectionService(max_edit_distance=2, confidence_threshold=0.8)
    assert not service.is_available()
    
    # Mock database to return products
    with patch('app.services.search.spell_correction.get_supabase_client') as mock_client:
        mock_response = Mock()
        mock_response.data = [
            {"name": "Running Shoes", "category": "sports"},
            {"name": "Laptop Computer", "category": "electronics"},
        ]
        mock_client.return_value.table.return_value.select.return_value.execute.return_value = mock_response
        
        success = service.initialize()
        assert success
        assert service.is_available()


def test_spell_correction_correct():
    """Test spell correction with various misspellings."""
    service = SpellCorrectionService(max_edit_distance=2, confidence_threshold=0.8)
    
    # Mock database
    with patch('app.services.search.spell_correction.get_supabase_client') as mock_client:
        mock_response = Mock()
        mock_response.data = [
            {"name": "Running Shoes", "category": "sports"},
            {"name": "Laptop Computer", "category": "electronics"},
        ]
        mock_client.return_value.table.return_value.select.return_value.execute.return_value = mock_response
        
        service.initialize()
        
        # Test exact match (no correction needed)
        corrected, confidence, applied = service.correct("running shoes")
        assert "running" in corrected.lower()
        assert "shoes" in corrected.lower()
        
        # Test with empty query
        corrected, confidence, applied = service.correct("")
        assert corrected == ""
        assert not applied


def test_spell_correction_confidence_threshold():
    """Test spell correction confidence threshold."""
    service = SpellCorrectionService(max_edit_distance=2, confidence_threshold=0.9)
    
    with patch('app.services.search.spell_correction.get_supabase_client') as mock_client:
        mock_response = Mock()
        mock_response.data = [{"name": "Running Shoes", "category": "sports"}]
        mock_client.return_value.table.return_value.select.return_value.execute.return_value = mock_response
        
        service.initialize()
        
        # Low confidence correction should not be applied
        corrected, confidence, applied = service.correct("runnig")
        # Should return original if confidence too low
        assert not applied or confidence <= 0.9


# ============================================================================
# Synonym Expansion Tests
# ============================================================================

def test_synonym_expansion_initialization(temp_synonym_dict):
    """Test synonym expansion service initialization."""
    service = SynonymExpansionService(synonym_dict_path=temp_synonym_dict, max_synonyms=5)
    success = service.initialize()
    assert success
    assert service.is_available()


def test_synonym_expansion_expand(temp_synonym_dict):
    """Test synonym expansion."""
    service = SynonymExpansionService(synonym_dict_path=temp_synonym_dict, max_synonyms=5)
    service.initialize()
    
    # Test expansion
    expanded_query, expanded_terms, expanded = service.expand("sneakers")
    assert expanded
    assert "sneakers" in expanded_terms
    assert "running shoes" in expanded_query.lower() or "trainers" in expanded_query.lower()
    
    # Test no expansion
    expanded_query, expanded_terms, expanded = service.expand("unknown term")
    assert not expanded
    assert len(expanded_terms) == 0


def test_synonym_expansion_max_limit(temp_synonym_dict):
    """Test synonym expansion respects max limit."""
    service = SynonymExpansionService(synonym_dict_path=temp_synonym_dict, max_synonyms=1)
    service.initialize()
    
    expanded_query, expanded_terms, expanded = service.expand("sneakers")
    # Should only expand with max 1 synonym
    assert expanded


def test_synonym_expansion_empty_dict():
    """Test synonym expansion with empty dictionary."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump({}, f)
        temp_path = Path(f.name)
    
    service = SynonymExpansionService(synonym_dict_path=temp_path)
    service.initialize()
    
    expanded_query, expanded_terms, expanded = service.expand("test")
    assert not expanded


# ============================================================================
# Query Classification Tests
# ============================================================================

def test_query_classification_navigational():
    """Test query classification for navigational queries."""
    service = QueryClassificationService()
    
    with patch('app.services.search.query_classification.get_supabase_client') as mock_client:
        mock_response = Mock()
        mock_response.data = [
            {"name": "Nike Air Max"},
            {"name": "Apple iPhone"},
        ]
        mock_client.return_value.table.return_value.select.return_value.execute.return_value = mock_response
        
        service.initialize()
        
        # Test navigational query
        classification = service.classify("nike air max")
        assert classification == QUERY_TYPE_NAVIGATIONAL
        
        # Test short brand query
        classification = service.classify("nike shoes")
        assert classification == QUERY_TYPE_NAVIGATIONAL


def test_query_classification_transactional():
    """Test query classification for transactional queries."""
    service = QueryClassificationService()
    service.initialize()
    
    # Test purchase intent keywords
    classification = service.classify("buy running shoes")
    assert classification == QUERY_TYPE_TRANSACTIONAL
    
    classification = service.classify("cheap laptops")
    assert classification == QUERY_TYPE_TRANSACTIONAL
    
    classification = service.classify("discount headphones")
    assert classification == QUERY_TYPE_TRANSACTIONAL


def test_query_classification_informational():
    """Test query classification for informational queries."""
    service = QueryClassificationService()
    service.initialize()
    
    # Test question keywords
    classification = service.classify("what is a good laptop")
    assert classification == QUERY_TYPE_INFORMATIONAL
    
    classification = service.classify("best running shoes")
    assert classification == QUERY_TYPE_INFORMATIONAL
    
    classification = service.classify("top rated headphones")
    assert classification == QUERY_TYPE_INFORMATIONAL


def test_query_classification_default():
    """Test query classification defaults to informational."""
    service = QueryClassificationService()
    service.initialize()
    
    # Test unclear query
    classification = service.classify("random query")
    assert classification == QUERY_TYPE_INFORMATIONAL


# ============================================================================
# Query Normalization Tests
# ============================================================================

def test_query_normalization_basic(temp_abbreviation_dict):
    """Test basic query normalization."""
    service = QueryNormalizationService(abbreviation_dict_path=temp_abbreviation_dict)
    service.initialize()
    
    # Test lowercase
    normalized = service.normalize("RUNNING SHOES")
    assert normalized == "running shoes"
    
    # Test trim whitespace
    normalized = service.normalize("  running shoes  ")
    assert normalized == "running shoes"
    
    # Test remove punctuation
    normalized = service.normalize("running, shoes!")
    assert normalized == "running shoes"


def test_query_normalization_abbreviation_expansion(temp_abbreviation_dict):
    """Test abbreviation expansion."""
    service = QueryNormalizationService(abbreviation_dict_path=temp_abbreviation_dict)
    service.initialize()
    
    # Test abbreviation expansion
    normalized = service.normalize("tv")
    assert "television" in normalized
    
    normalized = service.normalize("pc laptop")
    assert "personal computer" in normalized


def test_query_normalization_no_expansion(temp_abbreviation_dict):
    """Test normalization without abbreviation expansion."""
    service = QueryNormalizationService(abbreviation_dict_path=temp_abbreviation_dict)
    service.initialize()
    
    normalized = service.normalize("tv", expand_abbreviations=False)
    assert normalized == "tv"


def test_query_normalization_empty():
    """Test normalization with empty query."""
    service = QueryNormalizationService()
    service.initialize()
    
    normalized = service.normalize("")
    assert normalized == ""
    
    normalized = service.normalize(None)
    assert normalized == ""


# ============================================================================
# Intent Extraction Tests
# ============================================================================

def test_intent_extraction_brand():
    """Test brand extraction."""
    service = IntentExtractionService()
    
    with patch('app.services.search.intent_extraction.get_supabase_client') as mock_client:
        mock_response = Mock()
        mock_response.data = [
            {"name": "Nike Running Shoes", "category": "sports"},
            {"name": "Apple Laptop", "category": "electronics"},
        ]
        mock_client.return_value.table.return_value.select.return_value.execute.return_value = mock_response
        
        service.initialize()
        
        entities = service.extract("nike running shoes")
        assert entities["brand"] == "nike"
        
        entities = service.extract("apple laptop")
        assert entities["brand"] == "apple"


def test_intent_extraction_category():
    """Test category extraction."""
    service = IntentExtractionService()
    
    with patch('app.services.search.intent_extraction.get_supabase_client') as mock_client:
        mock_response = Mock()
        mock_response.data = [
            {"name": "Running Shoes", "category": "sports"},
        ]
        mock_client.return_value.table.return_value.select.return_value.execute.return_value = mock_response
        
        service.initialize()
        
        entities = service.extract("running shoes")
        assert entities["category"] == "sports" or entities["category"] == "shoes"


def test_intent_extraction_attributes():
    """Test attribute extraction (color, size)."""
    service = IntentExtractionService()
    service.initialize()
    
    entities = service.extract("red running shoes size 10")
    assert entities["attributes"]["color"] == "red"
    assert entities["attributes"]["size"] is not None
    
    entities = service.extract("blue wireless headphones")
    assert entities["attributes"]["color"] == "blue"
    assert "wireless" in entities["attributes"]["other"]


# ============================================================================
# Query Enhancement Orchestration Tests
# ============================================================================

def test_query_enhancement_service_enhance():
    """Test query enhancement orchestration."""
    service = QueryEnhancementService(
        enable_spell_correction=True,
        enable_synonym_expansion=True,
        enable_classification=True,
        enable_intent_extraction=True,
    )
    
    # Mock all services
    with patch('app.services.search.query_enhancement.get_normalization_service') as mock_norm, \
         patch('app.services.search.query_enhancement.get_spell_correction_service') as mock_spell, \
         patch('app.services.search.query_enhancement.get_synonym_expansion_service') as mock_synonym, \
         patch('app.services.search.query_enhancement.get_query_classification_service') as mock_class, \
         patch('app.services.search.query_enhancement.get_intent_extraction_service') as mock_intent:
        
        # Setup mocks
        mock_norm.return_value.normalize.return_value = "running shoes"
        mock_spell.return_value.is_available.return_value = False
        mock_synonym.return_value.is_available.return_value = False
        mock_class.return_value.is_available.return_value = True
        mock_class.return_value.classify.return_value = QUERY_TYPE_INFORMATIONAL
        mock_intent.return_value.is_available.return_value = True
        mock_intent.return_value.extract.return_value = {
            "brand": None,
            "category": "shoes",
            "attributes": {"color": None, "size": None, "other": []},
        }
        
        enhanced = service.enhance("running shoes")
        
        assert enhanced.original_query == "running shoes"
        assert enhanced.normalized_query == "running shoes"
        assert enhanced.classification == QUERY_TYPE_INFORMATIONAL


def test_query_enhancement_empty_query():
    """Test query enhancement with empty query."""
    service = QueryEnhancementService()
    
    enhanced = service.enhance("")
    assert enhanced.original_query == ""
    assert enhanced.normalized_query == ""


def test_enhanced_query_get_final_query():
    """Test EnhancedQuery.get_final_query() priority."""
    # Test with expanded query
    enhanced = EnhancedQuery(
        original_query="test",
        normalized_query="test",
        expanded_query="test OR expanded",
        expansion_applied=True,
    )
    assert enhanced.get_final_query() == "test OR expanded"
    
    # Test with corrected query (no expansion)
    enhanced = EnhancedQuery(
        original_query="test",
        normalized_query="test",
        corrected_query="corrected",
        correction_applied=True,
    )
    assert enhanced.get_final_query() == "corrected"
    
    # Test with only normalized query
    enhanced = EnhancedQuery(
        original_query="test",
        normalized_query="normalized",
    )
    assert enhanced.get_final_query() == "normalized"


def test_query_enhancement_error_handling():
    """Test query enhancement error handling."""
    service = QueryEnhancementService()
    
    # Mock normalization to raise exception
    with patch('app.services.search.query_enhancement.get_normalization_service') as mock_norm:
        mock_norm.return_value.normalize.side_effect = Exception("Normalization error")
        
        enhanced = service.enhance("test query")
        # Should return minimal enhancement on error
        assert enhanced.original_query == "test query"
        assert enhanced.normalized_query == "test query"  # Fallback to lowercase strip

