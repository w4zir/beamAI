# DEPLOYMENT_STRATEGY.md

## Local Development
- Docker Compose
- Supabase (Postgres)
- Redis
- FAISS local index

## Cloud Deployment
- Kubernetes (EKS / GKE)
- Managed Postgres (Aurora / Cloud SQL)
- Managed Redis

## Rules
- No cloud SDKs in core services
- Configuration via environment variables only
- Same containers run locally and in cloud

