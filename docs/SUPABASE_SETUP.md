# Connecting to Supabase and Setting Up Schema

This guide explains how to connect to your local Supabase instance and set up the database schema and seed data.

## Prerequisites

- Supabase is running locally (based on `supabase/config.toml`)
  - API: http://localhost:54321
  - Database: localhost:54322
  - Studio: http://localhost:54323

## Connection Methods

### Method 1: Using Supabase CLI (Recommended)

If you have the Supabase CLI installed:

```bash
# Navigate to project root
cd /path/to/beamAI

# Link to your local Supabase instance
supabase link --project-ref local


(venv) (base) PS D:\ai_ws\softwares> │ Project URL    │ http://127.0.0.1:54321     

# Apply all migrations
supabase db reset

# Or apply migrations incrementally
supabase migration up
```

**Get Supabase CLI:**
- Windows: `scoop install supabase` or download from https://github.com/supabase/cli/releases
- Mac: `brew install supabase/tap/supabase`
- Linux: See https://github.com/supabase/cli#install-the-cli

### Method 2: Direct PostgreSQL Connection (psql)

Connect directly to the PostgreSQL database:

```bash
# Connect to Supabase database
psql -h localhost -p 54322 -U postgres -d postgres

# Default password is usually: postgres
# Or check your Supabase container logs for the actual password
```

Once connected, run the migrations:

```sql
-- Run migration 001
\i supabase/migrations/001_create_tables.sql

-- Run migration 002
\i supabase/migrations/002_create_fts_index.sql
```

**Or from command line:**

```bash
# Run migration 001
psql -h localhost -p 54322 -U postgres -d postgres -f supabase/migrations/001_create_tables.sql

# Run migration 002
psql -h localhost -p 54322 -U postgres -d postgres -f supabase/migrations/002_create_fts_index.sql
```

### Method 3: Using Supabase Studio (Web UI)

1. Open Supabase Studio in your browser: http://localhost:54323
2. Navigate to the SQL Editor
3. Copy and paste the contents of each migration file:
   - `supabase/migrations/001_create_tables.sql`
   - `supabase/migrations/002_create_fts_index.sql`
4. Run each SQL script

### Method 4: Using Python Script (Automated)

Create a simple Python script to run migrations:

```bash
# From project root
cd backend
python -c "
import os
import sys
from pathlib import Path
from supabase import create_client

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Get Supabase client
url = os.getenv('SUPABASE_URL', 'http://localhost:54321')
key = os.getenv('SUPABASE_SERVICE_KEY', '')
client = create_client(url, key)

# Read and execute migrations
migrations_dir = Path('../supabase/migrations')
for migration_file in sorted(migrations_dir.glob('*.sql')):
    print(f'Running {migration_file.name}...')
    sql = migration_file.read_text()
    # Note: Supabase Python client doesn't support raw SQL execution
    # You'll need to use psql or Supabase Studio for migrations
    print(f'  Please run this migration manually: {migration_file}')
"
```

**Note:** The Supabase Python client doesn't support executing raw SQL. Use one of the other methods for migrations.

## Finding Your Supabase Credentials

If you're unsure about your Supabase connection details:

1. **Check Supabase container logs:**
   ```bash
   # Find your Supabase container
   docker ps | grep supabase
   
   # View logs to find connection details
   docker logs <container_name>
   ```

2. **Check environment variables:**
   ```bash
   # If using Supabase CLI
   supabase status
   ```

3. **Default credentials** (if using Supabase CLI local development):
   - Database URL: `postgresql://postgres:postgres@localhost:54322/postgres`
   - Service Role Key: Check `supabase/.temp/keys.json` or Supabase Studio
   - Anon Key: Check `supabase/.temp/keys.json` or Supabase Studio

## Setting Up Environment Variables

Before running the seed script, ensure your `.env` file is configured:

**Root `.env` file:**
```bash
SUPABASE_URL=http://localhost:54321
SUPABASE_SERVICE_KEY=your-service-role-key-here
```

To get your service role key:
1. Open Supabase Studio: http://localhost:54323
2. Go to Settings → API
3. Copy the `service_role` key (keep this secret!)

## Running Migrations

### Step 1: Apply Schema Migrations

Choose one of the methods above to run:
- `supabase/migrations/001_create_tables.sql` - Creates products, users, and events tables
- `supabase/migrations/002_create_fts_index.sql` - Creates full-text search indexes

### Step 2: Verify Tables Were Created

```bash
# Using psql
psql -h localhost -p 54322 -U postgres -d postgres -c "\dt"

# Or check in Supabase Studio → Table Editor
```

You should see:
- `products`
- `users`
- `events`

## Seeding Data

After migrations are applied, seed the database with sample data:

```bash
# From project root
cd backend

# Activate virtual environment (if using one)
# On Windows:
.\venv\Scripts\activate
# On Mac/Linux:
source venv/bin/activate

# Run seed script
python scripts/seed_data.py
```

The seed script will:
- Create 20 sample products across 8 categories
- Create 10 sample users
- Generate 100 sample events (views, add_to_cart, purchases)

### Compute Initial Popularity Scores

After seeding, compute initial popularity scores:

```bash
# From backend directory
python -m app.services.features.compute
```

## Troubleshooting

### Connection Refused

If you can't connect to port 54322:

```bash
# Check if Supabase is running
docker ps | grep supabase

# Or check if port is in use
netstat -an | grep 54322  # Windows
lsof -i :54322            # Mac/Linux
```

### Authentication Failed

If you get authentication errors:

1. Check the password in your Supabase container logs
2. Verify you're using the correct user (usually `postgres`)
3. Check if your Supabase instance uses different credentials

### Migrations Already Applied

If tables already exist and you want to reset:

```bash
# Using Supabase CLI
supabase db reset

# Or manually drop tables (WARNING: deletes all data)
psql -h localhost -p 54322 -U postgres -d postgres -c "DROP TABLE IF EXISTS events, products, users CASCADE;"
```

### Seed Script Fails

If the seed script fails:

1. **Check environment variables:**
   ```bash
   # Verify .env file exists and has correct values
   cat .env | grep SUPABASE
   ```

2. **Test Supabase connection:**
   ```bash
   cd backend
   python -c "from app.core.database import get_supabase_client; client = get_supabase_client(); print('Connected!' if client else 'Failed')"
   ```

3. **Verify tables exist:**
   ```bash
   psql -h localhost -p 54322 -U postgres -d postgres -c "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';"
   ```

## Quick Reference

**Connection Strings:**
- PostgreSQL: `postgresql://postgres:postgres@localhost:54322/postgres`
- Supabase API: `http://localhost:54321`
- Supabase Studio: `http://localhost:54323`

**Common Commands:**
```bash
# Connect to database
psql -h localhost -p 54322 -U postgres -d postgres

# Run migration
psql -h localhost -p 54322 -U postgres -d postgres -f supabase/migrations/001_create_tables.sql

# Seed data
cd backend && python scripts/seed_data.py

# Compute features
cd backend && python -m app.services.features.compute
```

