# SEARCH_DESIGN.md

## Phase 1: Keyword Search
- PostgreSQL Full Text Search
- GIN index on search_vector
- Used for exact and partial matches

## Phase 2: Semantic Search
- SentenceTransformers for embeddings
- FAISS for approximate nearest neighbor search
- Offline index build, in-memory load

## Rules
- Search returns candidate product IDs only
- Ranking is handled downstream

## Query Processing Pipeline

### Step 1: Normalization
- Lowercase
- Remove punctuation
- Trim whitespace

### Step 2: Spell Correction (Phase 2.2)

**Purpose**: Correct spelling errors in user queries to improve search results

**Implementation**: SymSpell or similar spell correction library

**Configuration**:
- **Confidence Threshold**: Suggest correction if confidence >80%
- **Max Edit Distance**: 2 (allow 2 character differences)
- **Dictionary**: Built from product names, categories, common search terms

**Process**:
1. Check if query contains spelling errors
2. Generate candidate corrections
3. Calculate confidence score for each correction
4. If confidence >80%, apply correction
5. Log original query and correction for analysis

**Example**:
- Input: "runnig shoes"
- Correction: "running shoes" (confidence: 95%)
- Applied: Yes (confidence >80%)

**Fallback**: If confidence <80%, use original query (don't risk incorrect correction)

**Metrics**: Track correction rate, confidence distribution, impact on search results

**Integration with AI Phase 1**: LLM-powered spell correction (future enhancement) can provide higher accuracy for context-aware corrections

### Step 3: Synonym Expansion (Phase 2.2)

**Purpose**: Expand queries with synonyms to improve recall

**Synonym Dictionary Structure**:
```json
{
  "sneakers": ["running shoes", "trainers", "athletic shoes", "sports shoes"],
  "laptop": ["notebook", "computer", "notebook computer"],
  "phone": ["smartphone", "mobile phone", "cell phone"],
  "tv": ["television", "tv set", "smart tv"]
}
```

**Expansion Strategy**:
- **OR Expansion**: Query "sneakers" → Search for "sneakers OR running shoes OR trainers"
- **Boost Original**: Original term gets higher boost than synonyms
- **Limit Expansion**: Max 3-5 synonyms per term (prevent query bloat)

**Dictionary Maintenance**:
- **Manual Curation**: Maintain core dictionary manually
- **Auto-Discovery**: Analyze search logs to discover common synonym patterns
- **Category-Specific**: Different synonyms per category (e.g., "sneakers" in sports vs fashion)

**Example**:
- Input: "sneakers"
- Expanded: "sneakers" (boost: 1.0) OR "running shoes" (boost: 0.8) OR "trainers" (boost: 0.8)

**Metrics**: Track expansion rate, synonym usage, impact on search results

**Integration with AI Phase 1**: LLM-powered synonym expansion (future enhancement) can provide context-aware synonyms

### Step 4: Query Classification (Phase 2.2)

**Purpose**: Classify query intent to optimize search strategy

**Query Types**:

**1. Navigational Queries**:
- **Pattern**: Specific product name or brand + model
- **Examples**: "nike air max", "iphone 15 pro", "sony wh-1000xm5"
- **Strategy**: Exact match boost, prioritize brand/model matches
- **Ranking**: Emphasize exact keyword matches

**2. Informational Queries**:
- **Pattern**: General product category or question
- **Examples**: "best running shoes", "what is a good laptop", "top rated headphones"
- **Strategy**: Semantic search emphasis, ranking by quality metrics
- **Ranking**: Emphasize popularity, reviews, freshness

**3. Transactional Queries**:
- **Pattern**: Purchase intent keywords
- **Examples**: "buy nike shoes", "cheap laptops", "discount headphones"
- **Strategy**: Price filtering, availability emphasis
- **Ranking**: Emphasize price, availability, purchase signals

**Classification Logic**:
- **Rule-Based** (Phase 2.2):
  - Check for brand names (dictionary lookup)
  - Check for purchase intent keywords ("buy", "cheap", "discount")
  - Check for question words ("what", "best", "top")
  - Default to informational if unclear

- **LLM-Powered** (AI Phase 1):
  - Use Intent Classification Agent (Tier 1 LLM)
  - Higher accuracy, context-aware
  - Structured JSON output: `{"intent": "navigational|informational|transactional", "confidence": 0.95}`

**Integration**: Rule-based classification as fallback, LLM classification as primary (AI Phase 1)

### Step 5: Query Normalization (Phase 2.2)

**Purpose**: Standardize queries for consistent search behavior

**Normalization Rules**:
1. **Lowercase**: Convert to lowercase
2. **Trim Whitespace**: Remove leading/trailing whitespace
3. **Remove Special Characters**: Remove punctuation (except hyphens in product names)
4. **Handle Abbreviations**: Expand common abbreviations
   - "tv" → "television"
   - "pc" → "personal computer"
   - "usb" → "usb" (keep as-is, common acronym)

**Example**:
- Input: "  Nike Air-Max  "
- Normalized: "nike air-max"

**Abbreviation Dictionary**:
```json
{
  "tv": "television",
  "pc": "personal computer",
  "laptop": "laptop" (no expansion)
}
```

### Step 6: Intent Extraction & Entity Extraction (AI Phase 1)

**Purpose**: Extract structured information from natural language queries

**LLM-Powered Extraction** (AI Phase 1):
- **Agent**: Query Rewrite & Entity Extraction Agent (Tier 1 LLM)
- **Input**: Normalized query
- **Output**: Structured JSON with entities and filters

**Output Schema**:
```json
{
  "normalized_query": "nike running shoes",
  "filters": {
    "brand": "nike",
    "category": "running shoes",
    "price_range": null
  },
  "boosts": ["running", "nike"],
  "entities": {
    "brand": "nike",
    "category": "running shoes",
    "attributes": []
  }
}
```

**Rule-Based Fallback** (Phase 2.2):
- **NER (Named Entity Recognition)**: Extract brand, category, attributes
- **Pattern Matching**: Match against known brands, categories
- **Dictionary Lookup**: Lookup entities in product catalog

**Entity Types**:
- **Brand**: "Nike", "Apple", "Sony"
- **Category**: "running shoes", "laptops", "headphones"
- **Attributes**: "red", "size 10", "wireless"

**Boost Strategy**:
- Boost products matching extracted entities
- Higher boost for exact brand/category matches
- Lower boost for partial matches

**Integration**: LLM-powered extraction as primary (AI Phase 1), rule-based as fallback

**Metrics**: Track extraction accuracy, entity coverage, impact on search results