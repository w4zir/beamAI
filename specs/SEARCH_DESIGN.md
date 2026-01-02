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

### Step 2: Spell Correction (Optional - Phase 2)
- Use SymSpell or similar
- Threshold: Suggest correction if >80% confidence
- Example: "runnig" → "running"

### Step 3: Synonym Expansion
- Maintain synonym dictionary
  - "sneakers" → ["running shoes", "trainers", "athletic shoes"]
  - "laptop" → ["notebook", "computer"]
- Expand query before search

### Step 4: Query Classification
- Navigational: "nike air max" (specific product)
- Informational: "best running shoes" (needs ranking)
- Transactional: "buy nike shoes" (high purchase intent)

### Step 5: Intent Extraction (Phase 3)
- Use NER model to extract:
  - Brand: "Nike"
  - Category: "shoes"
  - Attribute: "red", "size 10"
- Boost results matching extracted entities