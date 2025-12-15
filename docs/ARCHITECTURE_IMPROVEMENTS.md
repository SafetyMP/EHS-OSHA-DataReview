# Architecture & Technical Improvements

This document outlines architectural and technical improvements to enhance performance, scalability, and maintainability of the OSHA Compliance Analyzer.

## 🚀 High Priority Improvements

### 1. Database-First Architecture

**Current Issue**: Loading 18+ million rows into memory on every initialization  
**Solution**: Migrate to database-first architecture

**Implementation**:
```python
# Current: Loads all data into memory
analyzer = OSHAAnalyzer()  # 5-15 min load time

# Improved: Query only what's needed
analyzer = OSHAAnalyzerDB()  # Instant initialization
results = analyzer.search_violations(year=2023)  # Fast query
```

**Benefits**:
- **Instant initialization** (no data loading)
- **Memory efficient** (query only needed data)
- **Faster queries** (indexed database lookups)
- **Concurrent access** (multiple users)

**Architecture**:
```
┌─────────────┐
│   Streamlit │
│    App      │
└──────┬──────┘
       │
       │ SQL Queries
       ▼
┌─────────────┐
│  Database   │
│ (SQLite/    │
│  PostgreSQL)│
└─────────────┘
```

**Migration Path**:
1. ✅ Database backend already implemented (`src/analyzer_db.py`)
2. Update `app.py` to use `OSHAAnalyzerDB` by default
3. Run `python -m src.db_migration` to populate database
4. Remove CSV-based analyzer (or keep as fallback)

---

### 2. Lazy Loading & Streaming

**Current Issue**: Loads entire datasets upfront  
**Solution**: Load data on-demand with streaming

**Implementation**:
```python
class LazyOSHAAnalyzer:
    def __init__(self):
        self._data_loaded = False
        self._db = get_db_manager()
    
    def _ensure_data_loaded(self, data_type):
        """Load data only when needed."""
        if not self._data_loaded[data_type]:
            # Load in chunks or query from database
            pass
    
    def search_violations(self, **filters):
        # Query directly from database - no upfront loading
        return self._db.query_violations(**filters)
```

**Benefits**:
- Faster startup
- Lower memory footprint
- Better user experience (app appears quickly)

---

### 3. Caching Strategy

**Current**: Streamlit's `@st.cache_resource` (works but limited)  
**Improved**: Multi-layer caching

**Architecture**:
```
┌─────────────────┐
│   Application   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌──────────────┐
│  Query Cache    │────▶│   Redis      │
│  (Hot Data)     │     │  (Optional)  │
└─────────────────┘     └──────────────┘
         │
         ▼
┌─────────────────┐
│  Streamlit Cache│
│  @st.cache_data │
└─────────────────┘
         │
         ▼
┌─────────────────┐
│   Database      │
│   (Cold Data)   │
└─────────────────┘
```

**Implementation**:
```python
from functools import lru_cache
import redis

# In-memory cache for frequent queries
@lru_cache(maxsize=1000)
def cached_query(query_hash):
    # Fast lookup for common queries
    pass

# Redis for shared cache (multiple instances)
redis_client = redis.Redis()
def get_cached_result(key):
    result = redis_client.get(key)
    if result:
        return json.loads(result)
    return None
```

**Cache Invalidation Strategy**:
- Time-based TTL (e.g., 1 hour for summary stats)
- Event-based invalidation (on data updates)
- Version-based (cache key includes data version)

---

### 4. API Layer

**Current**: Monolithic Streamlit app  
**Improved**: Separate API and frontend

**Architecture**:
```
┌──────────────┐     ┌──────────┐     ┌────────────┐
│   Streamlit  │────▶│   FastAPI│────▶│  Database  │
│   Frontend   │     │   API    │     │            │
└──────────────┘     └──────────┘     └────────────┘
                            │
                            ▼
                     ┌──────────────┐
                     │   Other      │
                     │   Clients    │
                     │  (Mobile,    │
                     │   Web, etc)  │
                     └──────────────┘
```

**Benefits**:
- **Reusability**: API can serve multiple frontends
- **Performance**: API can be optimized separately
- **Scalability**: Can scale API and frontend independently
- **Integration**: Other systems can use the API

**Implementation**:
```python
# api/main.py
from fastapi import FastAPI
from src.analyzer_db import OSHAAnalyzerDB

app = FastAPI()
analyzer = OSHAAnalyzerDB()

@app.get("/api/v1/company/{company_name}")
async def get_company_compliance(company_name: str):
    return analyzer.compare_company_across_agencies(company_name)

@app.get("/api/v1/violations")
async def search_violations(year: int = None, state: str = None):
    return analyzer.search_violations(year=year, state=state).to_dict('records')
```

---

### 5. Background Processing & Job Queue

**Current**: All processing happens synchronously  
**Improved**: Background jobs for heavy operations

**Use Cases**:
- Data migration/ETL
- Large report generation
- Risk score calculations for many companies
- Data aggregation and pre-computation

**Architecture**:
```
┌──────────────┐
│   User       │
│   Request    │
└──────┬───────┘
       │
       ▼
┌──────────────┐     ┌──────────────┐
│   FastAPI    │────▶│   Celery     │
│   Endpoint   │     │   (Job Queue)│
└──────────────┘     └──────┬───────┘
                            │
                            ▼
                    ┌──────────────┐
                    │   Workers    │
                    │  (Background)│
                    └──────────────┘
```

**Implementation**:
```python
# tasks.py
from celery import Celery

celery_app = Celery('osha_analyzer')

@celery_app.task
def calculate_risk_scores_batch(company_names):
    """Calculate risk scores for multiple companies in background."""
    analyzer = OSHAAnalyzerDB()
    results = []
    for company in company_names:
        risk = analyzer.get_company_risk_score(company)
        results.append(risk)
    return results

# API endpoint
@app.post("/api/v1/batch/risk-scores")
async def batch_risk_scores(companies: List[str]):
    task = calculate_risk_scores_batch.delay(companies)
    return {"task_id": task.id, "status": "processing"}

@app.get("/api/v1/tasks/{task_id}")
async def get_task_status(task_id: str):
    task = celery_app.AsyncResult(task_id)
    return {"status": task.status, "result": task.result}
```

---

## 📊 Data Architecture Improvements

### 6. Data Partitioning

**For Very Large Datasets**:

**Strategy**: Partition by year or region
```
violations_2020/
violations_2021/
violations_2022/
...
```

**Implementation**:
```python
class PartitionedDatabase:
    def query_by_year(self, year: int):
        # Query only relevant partition
        table = f"violations_{year}"
        return self.query(f"SELECT * FROM {table}")
```

**Benefits**:
- Faster queries (smaller tables)
- Easier data management
- Can archive old partitions

---

### 7. Data Pre-aggregation

**Current**: Aggregations calculated on-the-fly  
**Improved**: Pre-compute common aggregations

**Implementation**:
```python
# Pre-aggregated tables
CREATE TABLE violation_summary_by_year AS
SELECT 
    year,
    COUNT(*) as violation_count,
    SUM(current_penalty) as total_penalties,
    AVG(current_penalty) as avg_penalty
FROM violations
GROUP BY year;

# Query becomes instant
SELECT * FROM violation_summary_by_year WHERE year = 2023;
```

**Use Cases**:
- Summary statistics by year/state/industry
- Top violations lists
- Trend data

**Update Strategy**:
- Incremental updates (only new data)
- Scheduled refresh (daily/weekly)
- Materialized views (PostgreSQL)

---

### 8. Columnar Storage (For Analytics)

**For Read-Heavy Analytics Workloads**:

**Options**:
- **Parquet files** (already mentioned in enhancements)
- **Apache Arrow** in-memory format
- **ClickHouse** or **DuckDB** for OLAP queries

**Implementation**:
```python
import pyarrow.parquet as pq

# Convert to Parquet (one-time)
df.to_parquet('violations.parquet', compression='snappy')

# Fast columnar reads
df = pd.read_parquet('violations.parquet', columns=['year', 'state', 'penalty'])
```

**Benefits**:
- 70-90% smaller file sizes
- Faster reads (columnar format)
- Better compression

---

## 🔄 Processing Architecture

### 9. ETL Pipeline

**Current**: Manual data loading  
**Improved**: Automated ETL pipeline

**Architecture**:
```
┌──────────────┐
│  Data Source │
│   (DOL API)  │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│   Extract    │
│   (Download) │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  Transform   │
│ (Clean/Norm) │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│    Load      │
│  (Database)  │
└──────────────┘
```

**Tools**: Apache Airflow, Prefect, or simple cron jobs

**Implementation**:
```python
# etl/pipeline.py
from prefect import flow, task

@task
def extract_data():
    # Download from source
    pass

@task
def transform_data(raw_data):
    # Clean and normalize
    pass

@task
def load_data(transformed_data):
    # Load into database
    pass

@flow
def osha_etl_pipeline():
    raw = extract_data()
    transformed = transform_data(raw)
    load_data(transformed)

# Schedule: Daily at 2 AM
osha_etl_pipeline.serve(schedule="0 2 * * *")
```

---

### 10. Incremental Data Updates

**Current**: Full reload each time  
**Improved**: Incremental updates

**Strategy**:
```python
# Track last update timestamp
last_update = get_last_update_timestamp()

# Only fetch new/updated records
new_violations = fetch_violations_since(last_update)

# Update database incrementally
update_database(new_violations)
```

**Benefits**:
- Faster updates (only process new data)
- Less storage (don't duplicate existing data)
- Real-time capabilities

---

## 🏗️ Application Architecture

### 11. Microservices (For Scale)

**If Application Grows Large**:

**Service Breakdown**:
```
┌──────────────────┐
│  API Gateway     │
└────────┬─────────┘
         │
    ┌────┴────┬──────────┬──────────┐
    │         │          │          │
    ▼         ▼          ▼          ▼
┌───────┐ ┌───────┐ ┌────────┐ ┌────────┐
│Company│ │Violat │ │Analytic│ │Data    │
│Service│ │Service│ │Service │ │Service │
└───────┘ └───────┘ └────────┘ └────────┘
```

**Benefits**:
- Independent scaling
- Technology flexibility
- Fault isolation
- Team autonomy

**Trade-offs**:
- More complex deployment
- Network latency
- Distributed system challenges

---

### 12. Search Architecture

**For Better Search Performance**:

**Option A: Full-Text Search Engine**
- **Elasticsearch** or **OpenSearch**
- Fast text search
- Faceted search
- Autocomplete

**Option B: Database Full-Text Search**
- PostgreSQL full-text search
- Simpler architecture
- Good enough for most use cases

**Implementation**:
```python
# Elasticsearch integration
from elasticsearch import Elasticsearch

es = Elasticsearch()

# Index violations
def index_violations():
    for violation in violations:
        es.index(
            index='violations',
            body={
                'company_name': violation.company_name,
                'standard': violation.standard,
                'description': violation.description,
                # Full-text searchable
            }
        )

# Fast search
results = es.search(
    index='violations',
    body={'query': {'match': {'company_name': 'Amazon'}}}
)
```

---

### 13. Connection Pooling

**For Database Efficiency**:

**Current**: New connection per request  
**Improved**: Connection pooling

```python
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

engine = create_engine(
    database_url,
    poolclass=QueuePool,
    pool_size=10,          # Maintain 10 connections
    max_overflow=20,       # Allow 20 more if needed
    pool_pre_ping=True,    # Verify connections
    pool_recycle=3600      # Recycle connections after 1 hour
)
```

**Benefits**:
- Faster queries (reuse connections)
- Better resource management
- Handle concurrent requests

---

## 🔐 Security & Operations

### 14. Authentication & Authorization

**For Multi-User Systems**:

```python
# Add user authentication
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

async def get_current_user(token: str = Depends(oauth2_scheme)):
    # Verify token and get user
    user = verify_token(token)
    if not user:
        raise HTTPException(status_code=401)
    return user

@app.get("/api/v1/company/{company_name}")
async def get_company(
    company_name: str,
    current_user = Depends(get_current_user)
):
    # Check permissions
    if not current_user.can_access_company_data():
        raise HTTPException(status_code=403)
    return analyzer.compare_company_across_agencies(company_name)
```

---

### 15. Monitoring & Observability

**Add Comprehensive Monitoring**:

**Metrics**:
- Query performance (response times)
- Cache hit rates
- Error rates
- Resource usage (CPU, memory, disk)

**Tools**:
- **Prometheus** + **Grafana** for metrics
- **Sentry** for error tracking
- **Datadog** or **New Relic** for APM

**Implementation**:
```python
from prometheus_client import Counter, Histogram, generate_latest

query_counter = Counter('queries_total', 'Total queries', ['endpoint'])
query_duration = Histogram('query_duration_seconds', 'Query duration')

@app.get("/api/v1/company/{company_name}")
async def get_company(company_name: str):
    with query_duration.time():
        query_counter.labels(endpoint='company').inc()
        return analyzer.compare_company_across_agencies(company_name)

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type="text/plain")
```

---

### 16. Configuration Management

**Externalize Configuration**:

```python
# config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    redis_url: str = "redis://localhost:6379"
    cache_ttl: int = 3600
    max_query_rows: int = 10000
    api_rate_limit: int = 100
    
    class Config:
        env_file = ".env"

settings = Settings()
```

**Benefits**:
- Environment-specific configs
- No hardcoded values
- Easy to change without code changes

---

## 📈 Performance Optimizations

### 17. Query Optimization

**Database Indexes**:
```sql
-- Ensure critical indexes exist
CREATE INDEX idx_violations_company ON violations(company_name_normalized);
CREATE INDEX idx_violations_year_state ON violations(year, site_state);
CREATE INDEX idx_violations_agency_year ON violations(agency, year);
CREATE INDEX idx_violations_penalty ON violations(current_penalty) WHERE current_penalty > 0;
```

**Query Patterns**:
```python
# Bad: Full table scan
df[df['company_name'].str.contains('Amazon')]

# Good: Indexed lookup
query.filter(Violation.company_name_normalized.contains('AMAZON'))
```

---

### 18. Pagination

**For Large Result Sets**:

```python
@app.get("/api/v1/violations")
async def get_violations(
    page: int = 1,
    page_size: int = 100,
    offset: int = None
):
    offset = offset or (page - 1) * page_size
    
    results = analyzer.search_violations(
        limit=page_size,
        offset=offset
    )
    
    return {
        "data": results.to_dict('records'),
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total_count,
            "has_next": offset + page_size < total_count
        }
    }
```

---

### 19. Async Operations

**For I/O-Bound Tasks**:

```python
import asyncio
from asyncio import gather

async def search_multiple_companies(company_names):
    """Search multiple companies concurrently."""
    tasks = [
        analyzer.search_company_async(name)
        for name in company_names
    ]
    results = await gather(*tasks)
    return results
```

---

## 🧪 Testing & Quality

### 20. Testing Architecture

**Test Pyramid**:
```
        /\
       /  \
      /Unit\        (70% - Fast, isolated)
     /Tests \
    /--------\
   /Integration\     (20% - Service interactions)
  /    Tests    \
 /--------------\
/  E2E Tests    \   (10% - Full user flows)
/________________\
```

**Implementation**:
```python
# tests/unit/test_analyzer.py
def test_search_violations():
    analyzer = OSHAAnalyzerDB()
    results = analyzer.search_violations(year=2023, limit=10)
    assert len(results) <= 10
    assert all(r['year'] == 2023 for r in results)

# tests/integration/test_api.py
def test_company_search_api():
    response = client.get("/api/v1/company/Amazon")
    assert response.status_code == 200
    assert 'risk_score' in response.json()
```

---

## 🚀 Deployment Architecture

### 21. Containerization

**Docker Setup**:
```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["streamlit", "run", "app.py", "--server.port=8501"]
```

**Docker Compose**:
```yaml
version: '3.8'
services:
  app:
    build: .
    ports:
      - "8501:8501"
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/osha
    depends_on:
      - db
  
  db:
    image: postgres:15
    volumes:
      - db_data:/var/lib/postgresql/data
  
  redis:
    image: redis:7
```

---

### 22. CI/CD Pipeline

**Automated Testing & Deployment**:

```yaml
# .github/workflows/ci.yml
name: CI/CD

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
      - run: pip install -r requirements.txt
      - run: pytest
      
  deploy:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - run: docker build -t osha-analyzer .
      - run: docker push osha-analyzer
```

---

## 📊 Recommended Implementation Order

### Phase 1: Quick Wins (1-2 weeks)
1. ✅ **Database Backend** (Already implemented!)
2. **Update app.py to use database by default**
3. **Add connection pooling**
4. **Implement pagination**

### Phase 2: Performance (2-4 weeks)
5. **Add caching layer (Redis)**
6. **Query optimization & indexes**
7. **Pre-aggregated tables**
8. **Parquet format conversion**

### Phase 3: Architecture (1-2 months)
9. **API layer (FastAPI)**
10. **Background job processing**
11. **ETL pipeline**
12. **Monitoring & observability**

### Phase 4: Scale (2-3 months)
13. **Microservices (if needed)**
14. **Search engine integration**
15. **Authentication & authorization**
16. **Advanced deployment (Kubernetes, etc.)**

---

## 💡 Summary

**Immediate Impact** (Do First):
- ✅ Use database backend (already done!)
- Add connection pooling
- Implement pagination
- Add basic caching

**High Impact** (Do Soon):
- API layer for flexibility
- Background processing for heavy tasks
- Query optimization
- Monitoring

**Long-term** (Do When Scaling):
- Microservices architecture
- Advanced search
- ETL pipeline automation
- Container orchestration

---

## 📚 Additional Resources

- **Database**: PostgreSQL for production, SQLite for development
- **Caching**: Redis for distributed cache
- **API**: FastAPI for async performance
- **Job Queue**: Celery with Redis/RabbitMQ
- **Monitoring**: Prometheus + Grafana
- **Search**: Elasticsearch for advanced search needs

