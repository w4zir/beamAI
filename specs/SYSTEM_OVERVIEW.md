# SYSTEM_OVERVIEW.md

## Purpose
This system provides a **unified search and recommendation platform** for an e-commerce product catalog. It is designed to be developed locally and scaled to large production environments (Shopify / DoorDash scale) without architectural rewrites.

## Goals
- Unified keyword search, semantic search, and recommendations
- Local-first development (Supabase, Docker)
- Cloud-agnostic deployment (AWS, GCP, Azure)
- 100% open-source technologies
- Deterministic, explainable ranking

## Non-Goals
- Real-time model training
- End-to-end LLM-based ranking
- Cloud-provider-specific SDKs in core logic

## Core Principles
- Retrieval is separate from ranking
- Offline training, online serving
- Cache before compute
- Append-only event data

## Design Principles

1. **Separation of Concerns**: Retrieval, ranking, and serving are independent
2. **Fail Gracefully**: Every component has a fallback
3. **Measure Everything**: Metrics drive decisions, not opinions
4. **Privacy by Design**: Minimal data collection, clear retention
5. **Local-First Development**: Same code runs on laptop and cloud
6. **Immutable Events**: Append-only data enables replay and auditing