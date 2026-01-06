# Phase 2: Core Search & Recommendations - TODO Checklist

**Goal**: Enhance core search and recommendation functionality with semantic search and query understanding.

**Timeline**: Weeks 5-10

**Status**: 
- ✅ **2.1 Semantic Search (FAISS)**: Core implementation COMPLETE
- ✅ **2.2 Query Enhancement (Rule-Based)**: IMPLEMENTATION COMPLETE

**Note**: Query Enhancement will be enhanced with AI-powered query understanding in AI Phase 1. See `ai_phase1_TODO_checklist.md` for AI orchestration layer implementation.

---

## 2.1 Semantic Search (FAISS)

**Status**: ✅ **Core implementation complete**. 

**Implemented**:
- FAISS index building and loading
- SentenceTransformers embedding generation
- Semantic search query processing
- Hybrid search integration (keyword + semantic)
- Graceful fallback to keyword-only search
- Prometheus metrics for semantic search
- Memory usage monitoring
- Health check endpoint integration

**Remaining items** (optional enhancements):
- Automated index rebuild pipeline (weekly batch job) - **See Phase 6.3 Batch Infrastructure**
- Hot-reloading of index (without restart)
- Query embedding caching (for repeated queries)

### Setup & Configuration
- [x] Install FAISS library (`faiss-cpu` or `faiss-gpu`)
- [x] Install SentenceTransformers library
- [x] Add FAISS and SentenceTransformers to `requirements.txt`
- [x] Create semantic search service module (`app/services/search/semantic.py`)
- [x] Configure embedding model (`all-MiniLM-L6-v2` or `all-mpnet-base-v2`)
- [x] Determine embedding dimensions (384 or 768)

### Embedding Generation
- [x] Create embedding generation script/function
- [x] Load SentenceTransformers model
- [x] Generate embeddings for product descriptions
- [x] Batch process embeddings for all products
- [x] Store embeddings in temporary storage (for index building)
- [x] Handle missing or empty product descriptions
- [x] Add embedding generation to batch job pipeline

### Index Building
- [x] Create FAISS index builder script (`scripts/build_faiss_index.py`)
- [x] Choose index type (`IndexIVFFlat` or `IndexHNSW`)
- [x] Configure index parameters (nlist, nprobe for IVFFlat; M, ef_construction for HNSW)
- [x] Build FAISS index from product embeddings
- [x] Save index to disk (with versioning)
- [x] Create index metadata file (product_id mapping, index version, build date)
- [x] Add index validation (verify all products are indexed)
- [ ] Create index rebuild pipeline (weekly batch job) - **See Phase 6.3 Batch Infrastructure**

### Index Loading & Management
- [x] Create index loader service
- [x] Load FAISS index in memory on application startup
- [x] Implement index version checking
- [x] Handle index loading failures gracefully
- [ ] Support hot-reloading of index (without restart)
- [x] Monitor index memory usage
- [x] Add index health check endpoint

### Query Processing
- [x] Create query embedding function
- [x] Generate query embedding on-the-fly for search requests
- [x] Implement FAISS index search (top-K candidates)
- [x] Calculate cosine similarity scores
- [x] Return `search_semantic_score` for each result
- [x] Handle empty query or invalid input
- [ ] Add query embedding caching (optional, for repeated queries) - **Requires Phase 3.1 Redis Caching**

### Hybrid Search Integration
- [x] Create hybrid search service
- [x] Combine keyword and semantic search results
- [x] Implement result merging logic
- [x] Use `max(keyword_score, semantic_score)` per RANKING_LOGIC.md
- [x] Handle cases where one search type fails
- [x] Add hybrid search metrics (keyword vs semantic result counts)
- [ ] Test hybrid search with various query types

### Fallback Mechanisms
- [x] Implement fallback to keyword-only if FAISS index fails
- [x] Implement fallback if embedding generation fails
- [ ] Add circuit breaker for semantic search service - **See Phase 3.3 Circuit Breakers**
- [x] Log fallback events for monitoring
- [x] Ensure graceful degradation

### Integration with Search Endpoint
- [x] Integrate semantic search into search endpoint
- [x] Add semantic search as optional parameter
- [x] Update search response to include semantic scores
- [x] Maintain backward compatibility (keyword-only still works)
- [x] Add feature flag for semantic search (enable/disable)
- [x] Update API documentation

### Testing
- [x] Write unit tests for embedding generation
- [x] Write unit tests for index building
- [x] Write unit tests for query processing
- [x] Write unit tests for hybrid search merging
- [x] Write integration tests for semantic search endpoint
- [x] Test with various query types (conceptual, specific, misspelled)
- [x] Test fallback mechanisms
- [x] Performance test: embedding generation latency
- [x] Performance test: FAISS search latency
- [x] Verify semantic search returns relevant results for conceptual queries
- [x] Write unit tests for metrics collection
- [x] Write unit tests for memory usage calculation
- [x] Write integration tests for health check endpoint
- [x] Write integration tests for metrics endpoint

### Monitoring & Metrics
- [x] Add metrics: semantic search request count
- [x] Add metrics: semantic search latency (p50, p95, p99) - Prometheus histogram implemented
- [x] Add metrics: embedding generation latency
- [x] Add metrics: FAISS index search latency
- [x] Add metrics: hybrid search result distribution
- [x] Add metrics: fallback usage count
- [x] Log semantic search queries and results
- [x] Track semantic vs keyword result overlap

---

## 2.2 Query Enhancement (Rule-Based)

**Status**: ✅ **IMPLEMENTATION COMPLETE**

**Note**: This phase will be enhanced with AI-powered query understanding in AI Phase 1. The AI orchestration layer will provide intent classification and query rewriting capabilities that complement traditional query enhancement techniques.

### Setup & Configuration
- [x] Install spell correction library (SymSpell or similar)
- [x] Add spell correction library to `requirements.txt`
- [x] Create query enhancement service module (`app/services/search/query_enhancement.py`)
- [x] Create synonym dictionary structure
- [x] Set up query classification logic
- [ ] **AI Integration**: Coordinate with AI Phase 1 for LLM-powered query understanding

### Spell Correction
- [x] Integrate SymSpell or similar spell correction library
- [x] Build dictionary from product names and descriptions
- [x] Configure confidence threshold (>80%)
- [x] Implement spell correction function
- [x] Handle common misspellings
- [x] Add spell correction to query preprocessing pipeline
- [x] Log spell corrections for analysis
- [x] Add metrics: spell correction usage count

### Synonym Expansion
- [x] Create synonym dictionary data structure
- [x] Populate synonym dictionary with common synonyms
- [x] Add domain-specific synonyms (e.g., "sneakers" → ["running shoes", "trainers"])
- [x] Implement synonym expansion function
- [x] Expand query before search
- [x] Handle multi-word synonyms
- [ ] Add synonym dictionary management (CRUD operations) - **Future enhancement**
- [ ] Create synonym dictionary update process - **Future enhancement**
- [x] Add metrics: synonym expansion usage count

### Query Classification
- [x] Implement query classification logic
- [x] Classify queries as:
  - [x] Navigational (specific product search)
  - [x] Informational (general information search)
  - [x] Transactional (purchase intent)
- [x] Create classification rules/heuristics
- [x] Add classification to query processing
- [ ] Use classification to adjust ranking (future)
- [x] Log query classifications for analysis
- [x] Add metrics: query classification distribution

### Query Normalization
- [x] Create query normalization service
- [x] Implement lowercase conversion
- [x] Implement whitespace normalization
- [x] Remove special characters (if appropriate)
- [x] Handle unicode normalization
- [ ] Add query length limits - **Future enhancement**
- [ ] Validate query format - **Future enhancement**
- [x] Add query normalization to preprocessing pipeline
- [x] Add abbreviation expansion

### Intent Extraction (Basic Rule-Based)
- [x] Implement brand extraction (rule-based)
- [x] Implement category extraction (rule-based)
- [x] Implement attribute extraction (color, size, etc.)
- [ ] Use extracted entities to boost matching results - **Future enhancement**
- [x] Add intent extraction to query processing
- [ ] **AI Integration**: AI Phase 1 provides LLM-powered entity extraction via QueryRewriteAgent

### Integration with Search Endpoint
- [x] Integrate query enhancement into search endpoint
- [x] Apply query preprocessing before search
- [x] Make enhancement optional (feature flag: `ENABLE_QUERY_ENHANCEMENT`)
- [x] Maintain original query for logging
- [ ] Return enhanced query in response (for transparency) - **Optional future enhancement**
- [ ] Update API documentation - **See how to run.md**

### Testing
- [x] Write unit tests for spell correction
- [x] Write unit tests for synonym expansion
- [x] Write unit tests for query classification
- [x] Write unit tests for query normalization
- [x] Write integration tests for query enhancement pipeline
- [x] Test with various query types
- [x] Test spell correction accuracy
- [x] Test synonym expansion correctness
- [ ] Verify query enhancement improves zero-result rate by 10-15% - **Requires production data**
- [x] Performance test: query enhancement latency

### Monitoring & Metrics
- [x] Add metrics: query enhancement usage count
- [x] Add metrics: spell correction count
- [x] Add metrics: synonym expansion count
- [x] Add metrics: query classification distribution
- [ ] Track zero-result rate before/after enhancement - **Requires production monitoring**
- [ ] Track search result quality improvements - **Requires production monitoring**
- [x] Log query enhancement transformations
- [ ] Monitor query expansion impact on results - **Requires production monitoring**

---

## Success Criteria Verification

### Semantic search returns relevant results for conceptual queries
- [x] Test semantic search with conceptual queries (e.g., "comfortable shoes for running")
- [x] Verify results are relevant and match intent
- [x] Compare semantic vs keyword-only results
- [ ] Measure relevance metrics (NDCG, precision@K)

### Query enhancement improves zero-result rate
- [ ] Measure zero-result rate before query enhancement - **Requires production data**
- [ ] Measure zero-result rate after query enhancement - **Requires production data**
- [ ] Verify improvement in zero-result rate by 10-15% - **Requires production data**
- [ ] Track query enhancement impact on search quality - **Requires production monitoring**

### Hybrid search combines keyword and semantic effectively
- [x] Verify hybrid search merges results correctly
- [x] Verify `max(keyword_score, semantic_score)` logic works
- [ ] Test with various query types (conceptual, specific, misspelled)
- [ ] Measure hybrid search result quality

### Index rebuild pipeline runs successfully
- [ ] Create weekly batch job for index rebuild - **See Phase 6.3 Batch Infrastructure**
- [ ] Test index rebuild pipeline
- [ ] Verify zero-downtime index updates
- [ ] Monitor index rebuild metrics

---

## Documentation

- [x] Document semantic search implementation and usage
- [x] Document FAISS index building and management
- [x] Document query enhancement features (see how to run.md)
- [x] Update FEATURE_DEFINITIONS.md with new features (product_embedding feature documented)
- [x] Update API documentation with query enhancement feature flag (see how to run.md)
- [ ] Create developer guide for adding new search features - **Future enhancement**

---

## Integration & Testing

- [x] Integration test: End-to-end semantic search flow
  - [x] Verify embedding generation
  - [x] Verify FAISS index search
  - [x] Verify hybrid search merging
  - [x] Verify results are returned correctly
- [ ] Integration test: Query enhancement end-to-end
  - [ ] Verify query preprocessing
  - [ ] Verify enhanced query improves results
- [ ] Load test: Verify semantic search doesn't impact performance significantly
- [ ] Test semantic search resilience (what happens if index fails to load?)

---

## Notes

- Semantic search core implementation is complete
- Query enhancement can be implemented incrementally (spell correction → synonyms → classification)
- AI Phase 1 will enhance query understanding with LLM-powered intent classification and query rewriting
- Test each component independently before integration
- Monitor search performance and quality metrics
- Document any deviations from the plan

---

## References

- Phase 2 specification: `/docs/TODO/implementation_plan.md` (Phase 2: Core Search & Recommendations)
- Feature definitions: `/specs/FEATURE_DEFINITIONS.md`
- Ranking logic: `/specs/RANKING_LOGIC.md`
- Search design: `/specs/SEARCH_DESIGN.md`
- **AI Architecture**: `/specs/AI_ARCHITECTURE.md`
- **AI Phase 1**: `/docs/TODO/ai_phase1_TODO_checklist.md` (Query Understanding)

