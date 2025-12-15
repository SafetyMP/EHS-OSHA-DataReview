# Environment Variables Configuration

This document describes all environment variables used by the OSHA Violation Analyzer application.

## Quick Start

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` with your configuration values

3. For production, use `.env.production.example`:
   ```bash
   cp .env.production.example .env.production
   # Edit .env.production with production values
   ```

4. Validate your environment:
   ```bash
   python scripts/validate_env.py --load-env .env
   ```

## Environment Variable Reference

### Database Configuration

#### `DATABASE_URL`
- **Description**: Database connection URL
- **Required**: Yes (for production)
- **Default**: `sqlite:///data/compliance.db` (development)
- **Formats**:
  - SQLite: `sqlite:///path/to/compliance.db`
  - PostgreSQL: `postgresql://user:password@host:port/database`
  - MySQL: `mysql://user:password@host:port/database`
- **Example**: `postgresql://admin:secret@localhost:5432/compliance_db`

#### `DATABASE_POOL_SIZE`
- **Description**: Number of connections to maintain in the pool
- **Default**: `10`
- **Production**: `20` or higher recommended

#### `DATABASE_MAX_OVERFLOW`
- **Description**: Maximum number of overflow connections
- **Default**: `20`
- **Production**: `40` or higher recommended

### Data Directory

#### `DATA_DIR`
- **Description**: Path to directory containing CSV data files
- **Default**: `./data` (relative to project root)
- **Production**: Use absolute path: `/app/data`

### Caching Configuration

#### `CACHE_TTL`
- **Description**: Cache time-to-live in seconds
- **Default**: `3600` (1 hour)
- **Production**: `7200` (2 hours) recommended

#### `CACHE_MAX_SIZE`
- **Description**: Maximum number of cache entries
- **Default**: `1000`
- **Production**: `5000` recommended

#### `REDIS_URL`
- **Description**: Redis URL for distributed caching (optional)
- **Default**: None (uses in-memory caching)
- **Format**: `redis://host:port` or `redis://password@host:port`
- **Example**: `redis://localhost:6379`

### API Configuration

#### `API_RATE_LIMIT`
- **Description**: Maximum API requests per minute
- **Default**: `100`
- **Production**: `60` recommended

#### `API_MAX_QUERY_ROWS`
- **Description**: Maximum rows returned per query
- **Default**: `10000`
- **Production**: `5000` recommended

### AI/ML Configuration

#### `OPENAI_API_KEY`
- **Description**: OpenAI API key for AI-powered features
- **Required**: Yes (if using AI download features)
- **Get key**: https://platform.openai.com/api-keys

#### `FUZZY_THRESHOLD`
- **Description**: Fuzzy matching threshold (0-100)
- **Default**: `75`
- **Higher values**: Stricter matching

### Performance Settings

#### `ENABLE_CACHING`
- **Description**: Enable caching (true/false)
- **Default**: `true`

#### `ENABLE_CONNECTION_POOLING`
- **Description**: Enable database connection pooling
- **Default**: `true`

### Logging Configuration

#### `LOG_LEVEL`
- **Description**: Logging level
- **Default**: `INFO`
- **Options**: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`
- **Production**: Use `INFO` or `WARNING` (not `DEBUG`)

### Streamlit Configuration

#### `STREAMLIT_SERVER_PORT`
- **Description**: Streamlit server port
- **Default**: `8501`

#### `STREAMLIT_SERVER_ADDRESS`
- **Description**: Streamlit server address
- **Default**: `localhost`
- **Production**: Use `0.0.0.0` to allow external connections

### Security Settings

#### `SECRET_KEY`
- **Description**: Secret key for session management
- **Required**: Yes (for production)
- **Generate**: `python -c "import secrets; print(secrets.token_urlsafe(32))"`
- **Minimum length**: 32 characters

#### `CORS_ORIGINS`
- **Description**: Allowed CORS origins (comma-separated)
- **Default**: `*` (allows all origins)
- **Production**: Restrict to your domain(s)
- **Example**: `https://yourdomain.com,https://app.yourdomain.com`

### Deployment Settings

#### `ENVIRONMENT`
- **Description**: Deployment environment
- **Default**: `development`
- **Options**: `development`, `staging`, `production`

#### `DEBUG`
- **Description**: Enable debug mode
- **Default**: `true`
- **Production**: Must be `false`

## Production Checklist

Before deploying to production, ensure:

- [ ] `DATABASE_URL` is set to PostgreSQL or MySQL (not SQLite)
- [ ] `SECRET_KEY` is set to a strong random value (32+ characters)
- [ ] `LOG_LEVEL` is set to `INFO` or `WARNING`
- [ ] `DEBUG` is set to `false`
- [ ] `CORS_ORIGINS` is restricted to your domain(s)
- [ ] `STREAMLIT_SERVER_ADDRESS` is set to `0.0.0.0` if external access needed
- [ ] `REDIS_URL` is configured for distributed caching
- [ ] Database pool sizes are increased for production load

## Validation

Validate your environment variables:

```bash
# Validate development environment
python scripts/validate_env.py --load-env .env

# Validate production environment
python scripts/validate_env.py --environment production --load-env .env.production
```

## Loading Environment Variables

### Python (using python-dotenv)

```python
from dotenv import load_dotenv
load_dotenv()  # Loads .env from current directory
load_dotenv('.env.production')  # Load specific file
```

### Shell Script

```bash
# Load .env file
export $(cat .env | xargs)

# Or use source
set -a
source .env
set +a
```

### Docker

```yaml
# docker-compose.yml
services:
  app:
    env_file:
      - .env.production
```

## Security Best Practices

1. **Never commit `.env` files** - They're in `.gitignore`
2. **Use different secrets** for each environment
3. **Rotate secrets regularly** in production
4. **Use secret management** services (AWS Secrets Manager, HashiCorp Vault, etc.)
5. **Restrict CORS** to known domains
6. **Use HTTPS** in production
7. **Set DEBUG=false** in production
8. **Use strong SECRET_KEY** (32+ random characters)

## Troubleshooting

### Environment variables not loading

1. Check file is named `.env` (with leading dot)
2. Verify file is in project root directory
3. Check file permissions (should be readable)
4. Ensure no syntax errors in `.env` file

### Database connection issues

1. Verify `DATABASE_URL` format is correct
2. Check database server is running
3. Verify credentials are correct
4. Check network connectivity

### Cache not working

1. Verify `REDIS_URL` is correct (if using Redis)
2. Check Redis server is running
3. Verify `ENABLE_CACHING=true`

