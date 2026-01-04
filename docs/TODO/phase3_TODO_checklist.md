# Phase 3: Advanced Search & ML Features - TODO Checklist

**Goal**: Implement semantic search and collaborative filtering.

**Timeline**: Weeks 9-14

---

## 3.1 Semantic Search (FAISS)

### Setup & Configuration
- [ ] Install FAISS library (`faiss-cpu` or `faiss-gpu`)
- [ ] Install SentenceTransformers library
- [ ] Add FAISS and SentenceTransformers to `requirements.txt`
- [ ] Create semantic search service module (`app/services/search/semantic.py`)
- [ ] Configure embedding model (`all-MiniLM-L6-v2` or `all-mpnet-base-v2`)
- [ ] Determine embedding dimensions (384 or 768)

### Embedding Generation
- [ ] Create embedding generation script/function
- [ ] Load SentenceTransformers model
- [ ] Generate embeddings for product descriptions
- [ ] Batch process embeddings for all products
- [ ] Store embeddings in temporary storage (for index building)
- [ ] Handle missing or empty product descriptions
- [ ] Add embedding generation to batch job pipeline

### Index Building
- [ ] Create FAISS index builder script (`scripts/build_faiss_index.py`)
- [ ] Choose index type (`IndexIVFFlat` or `IndexHNSW`)
- [ ] Configure index parameters (nlist, nprobe for IVFFlat; M, ef_construction for HNSW)
- [ ] Build FAISS index from product embeddings
- [ ] Save index to disk (with versioning)
- [ ] Create index metadata file (product_id mapping, index version, build date)
- [ ] Add index validation (verify all products are indexed)
- [ ] Create index rebuild pipeline (weekly batch job)

### Index Loading & Management
- [ ] Create index loader service
- [ ] Load FAISS index in memory on application startup
- [ ] Implement index version checking
- [ ] Handle index loading failures gracefully
- [ ] Support hot-reloading of index (without restart)
- [ ] Monitor index memory usage
- [ ] Add index health check endpoint

### Query Processing
- [ ] Create query embedding function
- [ ] Generate query embedding on-the-fly for search requests
- [ ] Implement FAISS index search (top-K candidates)
- [ ] Calculate cosine similarity scores
- [ ] Return `search_semantic_score` for each result
- [ ] Handle empty query or invalid input
- [ ] Add query embedding caching (optional, for repeated queries)

### Hybrid Search Integration
- [ ] Create hybrid search service
- [ ] Combine keyword and semantic search results
- [ ] Implement result merging logic
- [ ] Use `max(keyword_score, semantic_score)` per RANKING_LOGIC.md
- [ ] Handle cases where one search type fails
- [ ] Add hybrid search metrics (keyword vs semantic result counts)
- [ ] Test hybrid search with various query types

### Fallback Mechanisms
- [ ] Implement fallback to keyword-only if FAISS index fails
- [ ] Implement fallback if embedding generation fails
- [ ] Add circuit breaker for semantic search service
- [ ] Log fallback events for monitoring
- [ ] Ensure graceful degradation

### Integration with Search Endpoint
- [ ] Integrate semantic search into search endpoint
- [ ] Add semantic search as optional parameter
- [ ] Update search response to include semantic scores
- [ ] Maintain backward compatibility (keyword-only still works)
- [ ] Add feature flag for semantic search (enable/disable)
- [ ] Update API documentation

### Testing
- [ ] Write unit tests for embedding generation
- [ ] Write unit tests for index building
- [ ] Write unit tests for query processing
- [ ] Write unit tests for hybrid search merging
- [ ] Write integration tests for semantic search endpoint
- [ ] Test with various query types (conceptual, specific, misspelled)
- [ ] Test fallback mechanisms
- [ ] Performance test: embedding generation latency
- [ ] Performance test: FAISS search latency
- [ ] Verify semantic search returns relevant results for conceptual queries

### Monitoring & Metrics
- [ ] Add metrics: semantic search request count
- [ ] Add metrics: semantic search latency (p50, p95, p99)
- [ ] Add metrics: embedding generation latency
- [ ] Add metrics: FAISS index search latency
- [ ] Add metrics: hybrid search result distribution
- [ ] Add metrics: fallback usage count
- [ ] Log semantic search queries and results
- [ ] Track semantic vs keyword result overlap

---

## 3.2 Collaborative Filtering

### Setup & Configuration
- [ ] Install `implicit` library (Implicit ALS)
- [ ] Install additional dependencies (numpy, scipy)
- [ ] Add implicit and dependencies to `requirements.txt`
- [ ] Create collaborative filtering service module (`app/services/recommendation/collaborative.py`)
- [ ] Configure model parameters (factors, regularization, iterations)

### Data Preparation
- [ ] Create data extraction script for user-product interactions
- [ ] Query events table for user-product interaction matrix
- [ ] Aggregate interactions by type (view, click, purchase) with weights
- [ ] Handle implicit feedback (views, clicks) vs explicit (ratings)
- [ ] Create sparse matrix representation (CSR format)
- [ ] Add data validation (check for empty matrix, minimum interactions)
- [ ] Create data preprocessing pipeline

### Model Training (Offline)
- [ ] Create training script (`scripts/train_cf_model.py`)
- [ ] Implement Implicit ALS model training
- [ ] Configure hyperparameters (factors, regularization, iterations, alpha)
- [ ] Add cross-validation for hyperparameter tuning
- [ ] Save model artifacts (user factors, item factors)
- [ ] Save model metadata (training date, parameters, metrics)
- [ ] Create nightly batch job for model training
- [ ] Add model versioning
- [ ] Handle training failures gracefully

### Model Artifact Storage
- [ ] Set up model artifact storage (S3-compatible or local filesystem)
- [ ] Create model registry structure
- [ ] Implement model versioning system
- [ ] Store model metadata (training metrics, parameters, date)
- [ ] Create model loading service
- [ ] Add model validation on load
- [ ] Implement model rollback capability

### Model Scoring (Online)
- [ ] Create CF scoring service
- [ ] Load model artifacts (user/item factors) on startup
- [ ] Implement `user_product_affinity` score calculation
- [ ] Compute scores for candidate products
- [ ] Cache user factors in Redis (TTL: 24 hours)
- [ ] Handle missing users (cold start)
- [ ] Handle missing products (cold start)
- [ ] Optimize scoring for batch requests

### Cold Start Handling
- [ ] Implement new user handling (use popularity-based recommendations)
- [ ] Implement new product handling (use content-based/embedding similarity)
- [ ] Create transition logic: After 5 interactions, use CF scores
- [ ] Track user interaction count
- [ ] Blend CF scores with popularity scores during transition
- [ ] Add cold start metrics (new user count, new product count)

### Integration with Recommendation Endpoint
- [ ] Integrate CF scoring into recommendation endpoint
- [ ] Combine CF scores with existing ranking features
- [ ] Add CF as optional feature (feature flag)
- [ ] Update recommendation response to include CF scores
- [ ] Maintain backward compatibility
- [ ] Update API documentation

### A/B Testing Setup
- [ ] Create A/B test framework for CF vs popularity baseline
- [ ] Implement traffic splitting (50/50 or configurable)
- [ ] Track experiment metrics (CTR, CVR, engagement)
- [ ] Create experiment dashboard
- [ ] Add statistical analysis tools
- [ ] Document A/B test results

### Testing
- [ ] Write unit tests for data preparation
- [ ] Write unit tests for model training
- [ ] Write unit tests for CF scoring
- [ ] Write unit tests for cold start handling
- [ ] Write integration tests for recommendation endpoint with CF
- [ ] Test with sparse interaction matrix
- [ ] Test with new users (cold start)
- [ ] Test with new products (cold start)
- [ ] Verify CF recommendations show personalization (different users get different results)
- [ ] Performance test: CF scoring latency

### Monitoring & Metrics
- [ ] Add metrics: CF recommendation request count
- [ ] Add metrics: CF scoring latency
- [ ] Add metrics: model training duration
- [ ] Add metrics: cold start usage count
- [ ] Add metrics: A/B test metrics (CTR, CVR)
- [ ] Track model performance over time
- [ ] Log CF recommendations and scores
- [ ] Monitor model staleness (time since last training)

---

## 3.3 Feature Store

### Setup & Configuration
- [ ] Create feature store service module (`app/services/features/store.py`)
- [ ] Design feature store architecture
- [ ] Set up Redis for online features
- [ ] Set up Postgres/Parquet for offline features
- [ ] Create feature store configuration

### Feature Registry
- [ ] Review existing features in FEATURE_DEFINITIONS.md
- [ ] Create feature registry data structure
- [ ] Document all features with metadata:
  - [ ] Feature name
  - [ ] Feature type (online/offline)
  - [ ] Feature version
  - [ ] Feature description
  - [ ] Feature computation logic
  - [ ] Feature lineage (dependencies)
- [ ] Implement feature versioning system
- [ ] Create feature registry API/interface
- [ ] Add feature discovery capabilities

### Feature Storage - Online Features
- [ ] Design Redis schema for online features
- [ ] Implement feature storage in Redis
- [ ] Set appropriate TTLs for cached features
- [ ] Implement feature batch storage
- [ ] Add feature invalidation logic
- [ ] Handle Redis failures gracefully

### Feature Storage - Offline Features
- [ ] Design Postgres schema for offline features (or Parquet structure)
- [ ] Implement feature storage in Postgres/Parquet
- [ ] Create feature snapshot capability
- [ ] Implement feature backfill functionality
- [ ] Add feature versioning in offline storage

### Feature Serving API
- [ ] Create feature fetching API by product_id
- [ ] Create feature fetching API by user_id
- [ ] Implement batch feature fetching (reduce N+1 queries)
- [ ] Add feature caching layer
- [ ] Implement feature fallback (compute if not in store)
- [ ] Add feature fetching metrics
- [ ] Optimize feature fetching performance

### Feature Migration
- [ ] Identify existing features to migrate
- [ ] Create migration plan
- [ ] Migrate popularity_score to feature store
- [ ] Migrate freshness_score to feature store
- [ ] Migrate user_category_affinity to feature store
- [ ] Update all feature consumers to use feature store
- [ ] Verify feature consistency after migration
- [ ] Remove duplicate feature computation code

### Feature Versioning Strategy
- [ ] Define feature versioning scheme
- [ ] Implement version tracking
- [ ] Create feature deprecation process
- [ ] Add feature version migration tools
- [ ] Document versioning best practices

### Testing
- [ ] Write unit tests for feature registry
- [ ] Write unit tests for feature storage (online)
- [ ] Write unit tests for feature storage (offline)
- [ ] Write unit tests for feature serving API
- [ ] Write integration tests for feature store
- [ ] Test feature migration process
- [ ] Test feature versioning
- [ ] Performance test: feature fetching latency
- [ ] Verify feature store reduces feature computation duplication

### Monitoring & Metrics
- [ ] Add metrics: feature store request count
- [ ] Add metrics: feature fetching latency
- [ ] Add metrics: feature cache hit rate
- [ ] Add metrics: feature computation count (fallback)
- [ ] Track feature usage statistics
- [ ] Monitor feature store storage usage
- [ ] Log feature access patterns

---

## 3.4 Query Enhancement

### Setup & Configuration
- [ ] Install spell correction library (SymSpell or similar)
- [ ] Add spell correction library to `requirements.txt`
- [ ] Create query enhancement service module (`app/services/search/query_enhancement.py`)
- [ ] Create synonym dictionary structure
- [ ] Set up query classification logic

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
- [ ] Verify query enhancement improves zero-result rate
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
- [ ] Test semantic search with conceptual queries (e.g., "comfortable shoes for running")
- [ ] Verify results are relevant and match intent
- [ ] Compare semantic vs keyword-only results
- [ ] Measure relevance metrics (NDCG, precision@K)

### CF recommendations show personalization
- [ ] Test CF recommendations for different users
- [ ] Verify different users get different results
- [ ] Measure personalization metrics (diversity, novelty)
- [ ] Compare CF vs popularity-based recommendations

### Feature store reduces feature computation duplication
- [ ] Measure feature computation calls before feature store
- [ ] Measure feature computation calls after feature store
- [ ] Verify reduction in duplicate computations
- [ ] Track feature store cache hit rate

### Query enhancement improves zero-result rate
- [ ] Measure zero-result rate before query enhancement
- [ ] Measure zero-result rate after query enhancement
- [ ] Verify improvement in zero-result rate
- [ ] Track query enhancement impact on search quality

---

## Documentation

- [ ] Document semantic search implementation and usage
- [ ] Document FAISS index building and management
- [ ] Document collaborative filtering model training and serving
- [ ] Document feature store architecture and usage
- [ ] Document query enhancement features
- [ ] Update FEATURE_DEFINITIONS.md with new features
- [ ] Update RANKING_LOGIC.md if ranking changes
- [ ] Update API documentation with new endpoints/parameters
- [ ] Create developer guide for adding new ML features
- [ ] Document model deployment process

---

## Integration & Testing

- [ ] Integration test: End-to-end semantic search flow
  - [ ] Verify embedding generation
  - [ ] Verify FAISS index search
  - [ ] Verify hybrid search merging
  - [ ] Verify results are returned correctly
- [ ] Integration test: End-to-end collaborative filtering flow
  - [ ] Verify model training
  - [ ] Verify model loading
  - [ ] Verify CF scoring
  - [ ] Verify recommendations include CF scores
- [ ] Integration test: Feature store end-to-end
  - [ ] Verify feature storage
  - [ ] Verify feature fetching
  - [ ] Verify feature migration
- [ ] Integration test: Query enhancement end-to-end
  - [ ] Verify query preprocessing
  - [ ] Verify enhanced query improves results
- [ ] Load test: Verify ML features don't impact performance significantly
- [ ] Test ML features resilience (what happens if model fails to load?)

---

## Notes

- Semantic search and collaborative filtering can be implemented in parallel
- Feature store should be implemented early to support other features
- Query enhancement can be implemented incrementally (spell correction → synonyms → classification)
- Test each component independently before integration
- Monitor model performance and retrain as needed
- Document any deviations from the plan
- Consider model versioning and rollback strategies from the start

---

## References

- Phase 3 specification: `/docs/TODO/implementation_phases.md`
- Feature definitions: `/specs/FEATURE_DEFINITIONS.md`
- Ranking logic: `/specs/RANKING_LOGIC.md`
- Search design: `/specs/SEARCH_DESIGN.md`
- Recommendation design: `/specs/RECOMMENDATION_DESIGN.md`

