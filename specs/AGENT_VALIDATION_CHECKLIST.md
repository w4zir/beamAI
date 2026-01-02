# AGENT_VALIDATION_CHECKLIST.md

## Purpose
This checklist ensures that AI agents (e.g., Cursor or other code-generating agents) produce **production-grade, maintainable code** for the search and recommendation system. It prevents hallucinations, schema drift, and architectural violations.

---

## 1️⃣ Architectural Compliance

- [ ] Agent strictly follows `/specs/ARCHITECTURE.md` boundaries.
- [ ] No business logic or ML in FastAPI request handlers.
- [ ] Retrieval (search / reco) and ranking are separate.
- [ ] No cloud SDKs in core services.
- [ ] Offline training code is not included in serving code.

---

## 2️⃣ Data Model Compliance

- [ ] All SQL tables reference canonical tables in `/specs/DATA_MODEL.md`.
- [ ] No direct queries on raw Olist or source tables in APIs.
- [ ] Events table is append-only; no updates or deletes.
- [ ] Feature computation uses approved columns only.

---

## 3️⃣ Feature Compliance

- [ ] All features used are defined in `/specs/FEATURE_DEFINITIONS.md`.
- [ ] No ad-hoc feature computation inside API routes.
- [ ] Offline jobs produce features for serving, not online computation.
- [ ] Feature names and types match the definitions exactly.

---

## 4️⃣ Search and Recommendation

- [ ] Keyword search only uses Postgres FTS.
- [ ] Semantic search uses FAISS embeddings loaded offline.
- [ ] Search returns candidate IDs only, no ranking.
- [ ] Popularity and collaborative filtering models adhere to `/specs/RECOMMENDATION_DESIGN.md`.
- [ ] Ranking logic strictly follows `/specs/RANKING_LOGIC.md` formula.

---

## 5️⃣ API and Contracts

- [ ] FastAPI endpoints match `/specs/API_CONTRACTS.md` exactly.
- [ ] Response format, field names, and types are correct.
- [ ] No extra logic beyond orchestration.
- [ ] TODOs are inserted when agent is unsure, not guesses.

---

## 6️⃣ Deployment and Infra

- [ ] Local setup uses Docker Compose with Supabase, Redis, FAISS.
- [ ] Cloud deployment uses managed services; no SDKs in core code.
- [ ] Environment variables control configuration.
- [ ] No environment-specific hacks in code.

---

## 7️⃣ Agent Behavior Checks

- [ ] Agent references `/specs/` explicitly when writing code.
- [ ] Agent leaves TODOs instead of hallucinating data or features.
- [ ] No LLM-based ranking added.
- [ ] No unsafe SQL (cross joins, deletes, raw string interpolation).
- [ ] Agent acknowledges prime prompt before starting tasks.

---

## 8️⃣ Testing & Verification

- [ ] All generated code has basic unit tests or placeholders.
- [ ] Search and recommendation outputs are consistent with expected candidates.
- [ ] Features and ranking scores validated against small sample data.
- [ ] Performance sanity check (queries < 100ms locally for small data).

---

## Usage

1. Before any coding session, ensure **agent is primed** using `/docs`.
2. After code generation, **run this checklist** for each module.
3. Reject any output violating these rules.
4. Update checklist if new docs or features are added.

---

**Mental Model:**
> Agents are junior engineers. This checklist is their QA reviewer. Follow it strictly to prevent scaling disasters.

