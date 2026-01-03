# Docker Compose Setup

This project includes Docker Compose configuration for local development and testing.

## Prerequisites

- Docker Desktop (or Docker Engine + Docker Compose)
- Docker Compose v2.0+

## Quick Start

### 1. Build and Start Services

```bash
# Build and start all services
docker-compose up --build

# Or run in detached mode
docker-compose up -d --build
```

### 2. View Logs

```bash
# View all logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f backend
docker-compose logs -f frontend
```

### 3. Stop Services

```bash
# Stop services
docker-compose down

# Stop and remove volumes (clears database data)
docker-compose down -v
```

## Services

The Docker Compose setup includes:

- **postgres**: PostgreSQL 15 database (port 54322)
- **redis**: Redis 7 cache (port 6379)
- **backend**: FastAPI application (port 8000)
- **frontend**: Vite dev server (port 5173)

## Environment Variables

Create a `.env` file in the project root with:

```bash
# Supabase Configuration (external standalone container)
SUPABASE_URL=http://localhost:54321
SUPABASE_SERVICE_KEY=your-service-key

# Frontend Environment Variables
VITE_SUPABASE_URL=http://localhost:54321
VITE_SUPABASE_ANON_KEY=your-anon-key
VITE_API_URL=http://localhost:8000
```

Alternatively, copy `docker-compose.override.yml.example` to `docker-compose.override.yml` and customize it.

## Database Setup

### Option 1: Using Docker PostgreSQL

The Docker Compose setup includes a PostgreSQL instance. Migrations are automatically applied on first startup.

```bash
# Access PostgreSQL directly
docker-compose exec postgres psql -U postgres -d postgres

# Run migrations manually (if needed)
docker-compose exec backend python -m alembic upgrade head
```

## Running Migrations

Migrations in `supabase/migrations/` are automatically applied when the PostgreSQL container starts for the first time.

To manually run migrations:

```bash
# Connect to Docker PostgreSQL and run SQL
docker-compose exec postgres psql -U postgres -d postgres -f /docker-entrypoint-initdb.d/001_create_tables.sql
```

## Seeding Data

```bash
# Seed the database
docker-compose exec backend python scripts/seed_data.py

# Compute initial popularity scores
docker-compose exec backend python -m app.services.features.compute
```

## Development Workflow

### Hot Reload

Both backend and frontend support hot reload when volumes are mounted:

- Backend: Code changes in `backend/` are automatically reloaded
- Frontend: Code changes in `frontend/` trigger Vite HMR

### Running Commands

```bash
# Execute commands in containers
docker-compose exec backend python scripts/seed_data.py
docker-compose exec frontend npm run build

# Access shell
docker-compose exec backend bash
docker-compose exec frontend sh
```

### Rebuilding After Dependency Changes

```bash
# Rebuild specific service
docker-compose build backend
docker-compose up -d backend

# Rebuild all services
docker-compose build
docker-compose up -d
```

## Accessing Services

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **PostgreSQL**: localhost:54322
- **Redis**: localhost:6379

## Troubleshooting

### Port Already in Use

If ports are already in use, modify ports in `docker-compose.yml`:

```yaml
services:
  backend:
    ports:
      - "8001:8000"  # Change host port
```

### Database Connection Issues

1. Check PostgreSQL is healthy: `docker-compose ps`
2. Verify environment variables: `docker-compose exec backend env | grep SUPABASE`
3. Check logs: `docker-compose logs postgres`
4. Ensure Supabase standalone container is running and accessible

### Volume Permissions

On Linux, you may need to fix permissions:

```bash
sudo chown -R $USER:$USER ./backend
sudo chown -R $USER:$USER ./frontend
```

### Clearing Everything

```bash
# Stop containers and remove volumes
docker-compose down -v

# Remove images
docker-compose down --rmi all

# Clean up everything (including unused images)
docker system prune -a
```

## Production Considerations

This Docker Compose setup is optimized for local development. For production:

1. Use production-ready images (non-dev servers)
2. Set up proper secrets management
3. Configure resource limits
4. Use managed databases (RDS, Cloud SQL, etc.)
5. Set up proper logging and monitoring
6. Configure health checks and restart policies
7. Use multi-stage builds to reduce image size

See `specs/DEPLOYMENT_STRATEGY.md` for production deployment guidelines.

