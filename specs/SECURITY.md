# SECURITY.md

## Purpose

This document defines security requirements, authentication, authorization, encryption, and compliance strategies for the search and recommendation system.

**Alignment**: Implements Phase 5 from `docs/TODO/implementation_phases.md`

---

## Design Principles

1. **Defense in Depth**: Multiple layers of security
2. **Least Privilege**: Minimum permissions required
3. **Zero Trust**: Verify all requests, trust no one
4. **Privacy by Design**: Minimize data collection, protect PII
5. **Audit Everything**: Log all security-relevant events

---

## Authentication & Authorization

### API Key Management

**Purpose**: Authenticate API clients and enforce rate limits

**API Key Structure**:
- Format: `sk_live_<random_32_chars>` or `sk_test_<random_32_chars>`
- Prefix: `sk_live_` (production) or `sk_test_` (development)
- Length: 40 characters total
- Storage: Hashed in database (bcrypt or Argon2)

**API Key Lifecycle**:
1. **Generation**: Admin creates key via API or admin panel
2. **Activation**: Key active immediately after creation
3. **Rotation**: Generate new key, deprecate old key (30-day grace period)
4. **Revocation**: Immediate deactivation, invalidate all sessions

**API Key Metadata**:
- `key_id`: Unique identifier
- `name`: Human-readable name (e.g., "Production Frontend")
- `created_at`: Creation timestamp
- `last_used_at`: Last usage timestamp
- `rate_limit_search`: Search requests per minute
- `rate_limit_recommend`: Recommendation requests per minute
- `allowed_ips`: Optional IP whitelist (CIDR blocks)
- `expires_at`: Optional expiration date

**Endpoints**:
- `POST /auth/api-keys`: Create new API key
- `GET /auth/api-keys`: List API keys (admin only)
- `DELETE /auth/api-keys/{key_id}`: Revoke API key
- `POST /auth/api-keys/{key_id}/rotate`: Rotate API key

**Authentication Flow**:
1. Client includes API key in `Authorization` header: `Bearer sk_live_...`
2. Server validates key (check hash, expiration, revocation)
3. Server checks rate limits per key
4. Server checks IP whitelist (if configured)
5. Request proceeds if all checks pass

### User Authentication (Optional)

**Purpose**: Authenticate end users for personalized features

**Methods**:
- **JWT Tokens**: Stateless authentication
- **OAuth2**: Third-party authentication (Google, GitHub)
- **Session-Based**: Traditional session cookies (if needed)

**JWT Token Structure**:
```json
{
  "user_id": "user_123",
  "email": "user@example.com",
  "exp": 1234567890,
  "iat": 1234567890,
  "iss": "beamai_search_api"
}
```

**Token Validation**:
- Verify signature (HMAC or RSA)
- Check expiration (`exp` claim)
- Verify issuer (`iss` claim)
- Check revocation list (Redis cache)

**OAuth2 Integration**:
- Support Google OAuth2
- Support GitHub OAuth2
- Custom OAuth2 provider support

### Role-Based Access Control (RBAC)

**Roles**:
- **Admin**: Full access (API key management, cache invalidation, experiments)
- **Developer**: Read-only access (metrics, logs, experiments)
- **User**: Standard API access (search, recommendations)

**Permissions**:
- **Admin**: All endpoints, including `/admin/*`
- **Developer**: Read-only endpoints, `/metrics`, `/health`
- **User**: Public endpoints only (`/search`, `/recommend`)

**Implementation**:
- Middleware checks role from JWT token or API key metadata
- Deny access if insufficient permissions
- Log all permission denials

---

## Data Encryption

### Encryption in Transit

**TLS/HTTPS**:
- **Requirement**: All API traffic must use HTTPS
- **TLS Version**: TLS 1.2 minimum, TLS 1.3 preferred
- **Certificate**: Let's Encrypt (development) or managed certificates (production)
- **Certificate Rotation**: Automatic (managed) or manual (Let's Encrypt)

**Internal Service Communication**:
- **Database**: TLS required for all connections
- **Redis**: TLS optional (if Redis supports it)
- **Service-to-Service**: TLS required in production

### Encryption at Rest

**Database Encryption**:
- **PostgreSQL**: Use encrypted storage volumes (AWS EBS encryption, GCP disk encryption)
- **Backups**: Encrypt all database backups
- **Encryption Key**: Managed by cloud provider (KMS) or HashiCorp Vault

**Redis Encryption**:
- **Data at Rest**: Encrypt Redis persistence files (AOF/RDB)
- **Encryption Key**: Managed by cloud provider or Vault

**File Storage**:
- **FAISS Index**: Encrypt index files if stored on disk
- **Model Artifacts**: Encrypt model files in object storage (S3, GCS)

### Field-Level Encryption (PII)

**Purpose**: Encrypt sensitive fields in database

**Fields to Encrypt**:
- User email addresses (if stored)
- User preferences (if contains PII)
- API key metadata (if contains sensitive info)

**Encryption Method**:
- **Algorithm**: AES-256-GCM
- **Key Management**: HashiCorp Vault or cloud KMS
- **Key Rotation**: Quarterly

**Implementation**:
- Encrypt on write, decrypt on read
- Use application-level encryption (not database-level)
- Store encryption metadata (key version, IV) with encrypted data

---

## Secrets Management

### Secrets to Manage

**Database Credentials**:
- Connection strings
- Username/password
- SSL certificates

**API Keys**:
- LLM API keys (OpenAI, Anthropic)
- External service API keys
- Internal service API keys

**Encryption Keys**:
- Field-level encryption keys
- JWT signing keys
- TLS private keys

### Secrets Storage

**Development**:
- Environment variables (`.env` file, not committed)
- Docker secrets (for Docker Compose)

**Production**:
- **Primary**: HashiCorp Vault
- **Alternative**: AWS Secrets Manager, GCP Secret Manager, Azure Key Vault
- **Fallback**: Environment variables (if managed service unavailable)

### Secret Rotation

**Policy**:
- **API Keys**: Rotate every 90 days
- **Database Passwords**: Rotate every 180 days
- **Encryption Keys**: Rotate quarterly
- **JWT Keys**: Rotate every 365 days

**Process**:
1. Generate new secret
2. Update in secrets manager
3. Update application configuration
4. Restart services (rolling deployment)
5. Verify new secret works
6. Deprecate old secret (30-day grace period)
7. Delete old secret

### Secret Access Audit

**Logging**:
- Log all secret access (who, what, when)
- Alert on unusual access patterns
- Retain audit logs for 1 year

**Access Control**:
- Only authorized services can access secrets
- Use service accounts with minimal permissions
- Rotate service account credentials regularly

---

## Input Validation & Sanitization

### SQL Injection Prevention

**Rule**: Never use string interpolation in SQL queries

**Safe Methods**:
- **Parameterized Queries**: Use placeholders (`$1`, `%s`)
- **ORM/Query Builder**: Use SQLAlchemy, asyncpg parameterized queries
- **Input Validation**: Validate all inputs before database queries

**Example**:
```python
# ✅ Safe: Parameterized query
await db.fetch("SELECT * FROM products WHERE id = $1", product_id)

# ❌ Unsafe: String interpolation
await db.fetch(f"SELECT * FROM products WHERE id = '{product_id}'")
```

### XSS Prevention

**Rule**: Sanitize all user inputs before rendering

**Methods**:
- **Input Sanitization**: Remove/escape HTML tags
- **Output Encoding**: Encode special characters in responses
- **Content Security Policy (CSP)**: Restrict script execution

**Implementation**:
- Use framework's built-in sanitization (FastAPI, React)
- Validate input schemas (Pydantic models)
- Escape special characters in API responses

### Input Validation

**Query Parameters**:
- **Query Length**: Max 500 characters
- **Query Content**: Allow alphanumeric, spaces, common punctuation
- **User ID**: UUID format validation
- **Limit (k)**: Integer, range 1-100

**Request Body**:
- **Schema Validation**: Use Pydantic models
- **Type Checking**: Validate types (string, integer, etc.)
- **Range Validation**: Validate numeric ranges
- **Required Fields**: Enforce required fields

**Example**:
```python
from pydantic import BaseModel, Field, validator

class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    user_id: Optional[str] = Field(None, regex=r'^[a-zA-Z0-9_-]+$')
    k: int = Field(10, ge=1, le=100)
    
    @validator('query')
    def validate_query(cls, v):
        # Additional validation logic
        if len(v.strip()) == 0:
            raise ValueError('Query cannot be empty')
        return v.strip()
```

### Rate Limiting

**Purpose**: Prevent abuse and DDoS attacks

**Implementation**: See `specs/API_CONTRACTS.md` for rate limit details

**Per IP**:
- Search: 100 requests/minute (burst: 150)
- Recommend: 50 requests/minute (burst: 75)

**Per API Key**:
- Search: 1000 requests/minute
- Recommend: 500 requests/minute

**Abuse Detection**:
- Same query >20 times/minute → throttle
- Sequential product_id enumeration → flag and block

---

## Security Headers

### HTTP Security Headers

**Required Headers**:
- `Strict-Transport-Security: max-age=31536000; includeSubDomains` (HSTS)
- `X-Content-Type-Options: nosniff` (Prevent MIME sniffing)
- `X-Frame-Options: DENY` (Prevent clickjacking)
- `X-XSS-Protection: 1; mode=block` (XSS protection)
- `Content-Security-Policy: default-src 'self'` (CSP)
- `Referrer-Policy: strict-origin-when-cross-origin` (Referrer policy)

**CORS Configuration**:
- **Allowed Origins**: Configure per environment
- **Allowed Methods**: GET, POST, OPTIONS
- **Allowed Headers**: Content-Type, Authorization, X-Trace-ID
- **Credentials**: Allow cookies if needed (for session-based auth)

**Implementation**:
- Set headers in FastAPI middleware
- Configure CORS in FastAPI application

---

## Privacy & Compliance

### GDPR Compliance

**Right to Access**:
- **Endpoint**: `GET /privacy/user/{user_id}/data`
- **Response**: All user data (events, preferences, interactions)
- **Format**: JSON export
- **Timeline**: Within 30 days of request

**Right to Deletion (Right to be Forgotten)**:
- **Endpoint**: `DELETE /privacy/user/{user_id}`
- **Actions**:
  1. Delete user record from `users` table
  2. Anonymize `user_id` in `events` table (replace with hash)
  3. Purge user data from Redis cache
  4. Exclude user from future model training
  5. Confirm deletion via email
- **Timeline**: Within 30 days of request
- **Retention**: Some data may be retained for legal/compliance reasons (anonymized)

**Data Portability**:
- **Endpoint**: `GET /privacy/user/{user_id}/export`
- **Response**: Machine-readable format (JSON)
- **Includes**: Events, preferences, interactions

**Consent Management**:
- Track user consent for data collection
- Allow users to opt-out of tracking
- Respect "Do Not Track" header

### Data Minimization

**Collect Only What's Needed**:
- **Do Collect**: User ID, product interactions, timestamps, event types
- **Don't Collect**: IP addresses (unless required), user agents (unless required), precise locations

**Data Retention**:
- **Hot Data (Postgres)**: 90 days (events)
- **Warm Data (S3/GCS)**: 2 years (aggregated events)
- **Cold Archive**: 7 years (compliance backups)
- **Anonymized Analytics**: Indefinite

**Data Deletion**:
- Automatic deletion after retention period
- Manual deletion via privacy API
- Audit log of all deletions

### Privacy Policy

**Requirements**:
- Clear explanation of data collection
- Purpose of data collection
- Data retention policies
- User rights (access, deletion, portability)
- Contact information for privacy requests

**Location**: Public documentation, linked from API responses

---

## Security Audit Requirements

### Regular Audits

**Frequency**: Quarterly

**Scope**:
- Authentication and authorization
- Input validation
- Encryption (in transit and at rest)
- Secrets management
- API security
- Infrastructure security

**Process**:
1. Review security configurations
2. Test authentication/authorization
3. Review access logs
4. Check for security vulnerabilities
5. Review compliance status
6. Document findings and remediation

### Vulnerability Scanning

**Tools**:
- **Dependencies**: Dependabot, Snyk, or similar
- **Container Images**: Trivy, Clair
- **Infrastructure**: Cloud provider security scanning

**Frequency**: Weekly (automated)

**Response**:
- Critical vulnerabilities: Patch within 24 hours
- High vulnerabilities: Patch within 7 days
- Medium vulnerabilities: Patch within 30 days

### Penetration Testing

**Frequency**: Annually

**Scope**:
- API endpoints
- Authentication/authorization
- Input validation
- Infrastructure security

**Process**:
1. Hire external security firm
2. Conduct penetration test
3. Document findings
4. Remediate vulnerabilities
5. Re-test to verify fixes

---

## Incident Response

### Security Incident Types

**Data Breach**:
- Unauthorized access to user data
- Data exfiltration
- Database compromise

**API Abuse**:
- DDoS attacks
- Rate limit bypass
- Unauthorized access

**Infrastructure Compromise**:
- Server compromise
- Container escape
- Network intrusion

### Incident Response Process

1. **Detection**: Identify security incident
2. **Containment**: Isolate affected systems
3. **Investigation**: Determine scope and impact
4. **Remediation**: Fix vulnerabilities, restore systems
5. **Communication**: Notify affected users (if required)
6. **Post-Mortem**: Document incident and lessons learned

### Notification Requirements

**GDPR**: Notify data protection authority within 72 hours of breach

**Users**: Notify affected users if breach involves personal data

**Internal**: Notify security team and management immediately

---

## References

- **Implementation Phases**: `docs/TODO/implementation_phases.md` (Phase 5)
- **API Contracts**: `specs/API_CONTRACTS.md` (Rate Limiting)
- **Data Model**: `specs/DATA_MODEL.md` (Privacy & Deletion)
- **Architecture**: `specs/ARCHITECTURE.md` (Security Considerations)

---

End of document

