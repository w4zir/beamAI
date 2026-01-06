# Phase 2: Core Search & Recommendations - TODO Checklist

**Goal**: Enhance core search and recommendation functionality with semantic search and query understanding.

**Timeline**: Weeks 5-10

**Status**: 
- ✅ **2.1 Semantic Search (FAISS)**: Core implementation COMPLETE
- ⏳ **2.2 Query Enhancement (Rule-Based)**: NOT IMPLEMENTED

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

**Note**: This phase will be enhanced with AI-powered query understanding in AI Phase 1. The AI orchestration layer will provide intent classification and query rewriting capabilities that complement traditional query enhancement techniques.

### Setup & Configuration
- [ ] Install spell correction library (SymSpell or similar)
- [ ] Add spell correction library to `requirements.txt`
- [ ] Create query enhancement service module (`app/services/search/query_enhancement.py`)
- [ ] Create synonym dictionary structure
- [ ] Set up query classification logic
- [ ] **AI Integration**: Coordinate with AI Phase 1 for LLM-powered query understanding

### Spell Correction
- [ ] Integrate SymSpell or similar spell correction library
- [ ] Build dictionary from product names and descriptions
- [ ] Configure confidence threshold (>80%)
- [ ] Implement spell correction function
- [ ] Handle common misspellings
- [ ] Add spell correction to query preprocessing pipeline
- [ ] Log spell corrections for analysis
- [ ] Add metrics: spell correction usage count

### Synonym Expansion
- [ ] Create synonym dictionary data structure
- [ ] Populate synonym dictionary with common synonyms
- [ ] Add domain-specific synonyms (e.g., "sneakers" → ["running shoes", "trainers"])
- [ ] Implement synonym expansion function
- [ ] Expand query before search
- [ ] Handle multi-word synonyms
- [ ] Add synonym dictionary management (CRUD operations)
- [ ] Create synonym dictionary update process
- [ ] Add metrics: synonym expansion usage count

### Query Classification
- [ ] Implement query classification logic
- [ ] Classify queries as:
  - [ ] Navigational (specific product search)
  - [ ] Informational (general information search)
  - [ ] Transactional (purchase intent)
- [ ] Create classification rules/heuristics
- [ ] Add classification to query processing
- [ ] Use classification to adjust ranking (future)
- [ ] Log query classifications for analysis
- [ ] Add metrics: query classification distribution

### Query Normalization
- [ ] Create query normalization service
- [ ] Implement lowercase conversion
- [ ] Implement whitespace normalization
- [ ] Remove special characters (if appropriate)
- [ ] Handle unicode normalization
- [ ] Add query length limits
- [ ] Validate query format
- [ ] Add query normalization to preprocessing pipeline

### Intent Extraction (Future/Optional)
- [ ] Research NER (Named Entity Recognition) libraries
- [ ] Implement brand extraction
- [ ] Implement category extraction
- [ ] Implement attribute extraction
- [ ] Use extracted entities to boost matching results
- [ ] Add intent extraction to query processing
- [ ] **AI Integration**: AI Phase 1 provides LLM-powered entity extraction via QueryRewriteAgent

### Integration with Search Endpoint
- [ ] Integrate query enhancement into search endpoint
- [ ] Apply query preprocessing before search
- [ ] Make enhancement optional (feature flag)
- [ ] Maintain original query for logging
- [ ] Return enhanced query in response (for transparency)
- [ ] Update API documentation

### Testing
- [ ] Write unit tests for spell correction
- [ ] Write unit tests for synonym expansion
- [ ] Write unit tests for query classification
- [ ] Write unit tests for query normalization
- [ ] Write integration tests for query enhancement pipeline
- [ ] Test with various query types
- [ ] Test spell correction accuracy
- [ ] Test synonym expansion correctness
- [ ] Verify query enhancement improves zero-result rate by 10-15%
- [ ] Performance test: query enhancement latency

### Monitoring & Metrics
- [ ] Add metrics: query enhancement usage count
- [ ] Add metrics: spell correction count
- [ ] Add metrics: synonym expansion count
- [ ] Add metrics: query classification distribution
- [ ] Track zero-result rate before/after enhancement
- [ ] Track search result quality improvements
- [ ] Log query enhancement transformations
- [ ] Monitor query expansion impact on results

---

## Success Criteria Verification

### Semantic search returns relevant results for conceptual queries
- [x] Test semantic search with conceptual queries (e.g., "comfortable shoes for running")
- [x] Verify results are relevant and match intent
- [x] Compare semantic vs keyword-only results
- [ ] Measure relevance metrics (NDCG, precision@K)

### Query enhancement improves zero-result rate
- [ ] Measure zero-result rate before query enhancement
- [ ] Measure zero-result rate after query enhancement
- [ ] Verify improvement in zero-result rate by 10-15%
- [ ] Track query enhancement impact on search quality

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
- [ ] Document query enhancement features
- [x] Update FEATURE_DEFINITIONS.md with new features (product_embedding feature documented)
- [ ] Update API documentation with query enhancement endpoints/parameters
- [ ] Create developer guide for adding new search features

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

