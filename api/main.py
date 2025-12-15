"""
FastAPI application for OSHA Compliance Analyzer API.
Provides REST API endpoints for programmatic access.
"""

from fastapi import FastAPI, Query, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Optional, List
from pathlib import Path
import sys
import logging

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.analyzer_db import OSHAAnalyzerDB
from src.compliance_analyzer import ComplianceAnalyzer
from src.config import get_settings
from src.cache import get_cache_stats

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="OSHA Compliance Analyzer API",
    description="REST API for OSHA compliance data analysis",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global analyzers (initialized on startup)
analyzer: Optional[OSHAAnalyzerDB] = None
compliance_analyzer: Optional[ComplianceAnalyzer] = None


@app.on_event("startup")
async def startup_event():
    """Initialize analyzers on startup."""
    global analyzer, compliance_analyzer
    settings = get_settings()
    data_dir = settings.get_data_dir()
    
    try:
        analyzer = OSHAAnalyzerDB(data_dir=data_dir)
        compliance_analyzer = ComplianceAnalyzer(data_dir=data_dir)
        logger.info("Analyzers initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing analyzers: {e}")
        raise


@app.get("/")
async def root():
    """API root endpoint."""
    return {
        "name": "OSHA Compliance Analyzer API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "analyzers_loaded": analyzer is not None}


@app.get("/api/v1/violations")
async def search_violations(
    state: Optional[str] = Query(None, description="State code (e.g., CA, NY)"),
    year: Optional[int] = Query(None, description="Year filter"),
    naics_prefix: Optional[str] = Query(None, description="NAICS code prefix"),
    keyword: Optional[str] = Query(None, description="Keyword search in standard"),
    min_penalty: Optional[float] = Query(None, description="Minimum penalty amount"),
    limit: int = Query(100, ge=1, le=10000, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Offset for pagination")
):
    """Search violations with filters."""
    if not analyzer:
        raise HTTPException(status_code=503, detail="Analyzer not initialized")
    
    try:
        results = analyzer.search_violations(
            state=state,
            year=year,
            naics_prefix=naics_prefix,
            keyword=keyword,
            min_penalty=min_penalty,
            limit=limit,
            offset=offset
        )
        
        total_count = analyzer.count_violations(
            state=state,
            year=year,
            naics_prefix=naics_prefix,
            keyword=keyword,
            min_penalty=min_penalty
        )
        
        return {
            "data": results.to_dict('records'),
            "pagination": {
                "limit": limit,
                "offset": offset,
                "total": total_count,
                "has_next": offset + limit < total_count,
                "has_previous": offset > 0
            }
        }
    except Exception as e:
        logger.error(f"Error searching violations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/violations/top")
async def get_top_violations(
    n: int = Query(10, ge=1, le=100, description="Number of top violations"),
    year: Optional[int] = Query(None, description="Year filter")
):
    """Get top violations by citation count."""
    if not analyzer:
        raise HTTPException(status_code=503, detail="Analyzer not initialized")
    
    try:
        results = analyzer.top_violations(n=n, year=year)
        return results.to_dict('records')
    except Exception as e:
        logger.error(f"Error getting top violations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/violations/by-state")
async def get_violations_by_state(
    year: Optional[int] = Query(None, description="Year filter")
):
    """Get violation counts by state."""
    if not analyzer:
        raise HTTPException(status_code=503, detail="Analyzer not initialized")
    
    try:
        results = analyzer.violations_by_state(year=year)
        return results.to_dict('records')
    except Exception as e:
        logger.error(f"Error getting violations by state: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/violations/by-industry")
async def get_violations_by_industry(
    year: Optional[int] = Query(None, description="Year filter"),
    n: int = Query(15, ge=1, le=100, description="Number of industries")
):
    """Get violation counts by industry."""
    if not analyzer:
        raise HTTPException(status_code=503, detail="Analyzer not initialized")
    
    try:
        results = analyzer.violations_by_industry(year=year, n=n)
        return results.to_dict('records')
    except Exception as e:
        logger.error(f"Error getting violations by industry: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/company/{company_name}")
async def get_company_compliance(
    company_name: str,
    agencies: Optional[str] = Query(None, description="Comma-separated agency list"),
    include_risk_score: bool = Query(True, description="Include risk score"),
    use_fuzzy: bool = Query(True, description="Use fuzzy matching")
):
    """Get comprehensive compliance summary for a company."""
    if not compliance_analyzer:
        raise HTTPException(status_code=503, detail="Analyzer not initialized")
    
    agency_list = agencies.split(',') if agencies else None
    
    try:
        summary = compliance_analyzer.compare_company_across_agencies(
            company_name,
            agencies=agency_list,
            include_risk_score=include_risk_score,
            use_fuzzy=use_fuzzy
        )
        return summary
    except Exception as e:
        logger.error(f"Error getting company compliance: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/company/{company_name}/risk-score")
async def get_company_risk_score(
    company_name: str,
    agencies: Optional[str] = Query(None, description="Comma-separated agency list"),
    use_fuzzy: bool = Query(True, description="Use fuzzy matching")
):
    """Get risk score for a company."""
    if not compliance_analyzer:
        raise HTTPException(status_code=503, detail="Analyzer not initialized")
    
    agency_list = agencies.split(',') if agencies else None
    
    try:
        risk_score = compliance_analyzer.get_company_risk_score(
            company_name,
            agencies=agency_list,
            use_fuzzy=use_fuzzy
        )
        return risk_score
    except Exception as e:
        logger.error(f"Error getting risk score: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/company/{company_name}/impact")
async def get_company_impact(
    company_name: str,
    agencies: Optional[str] = Query(None, description="Comma-separated agency list"),
    use_fuzzy: bool = Query(True, description="Use fuzzy matching")
):
    """Analyze violation impact for a company."""
    if not compliance_analyzer:
        raise HTTPException(status_code=503, detail="Analyzer not initialized")
    
    agency_list = agencies.split(',') if agencies else None
    
    try:
        impact = compliance_analyzer.analyze_violation_impact(
            company_name,
            agencies=agency_list,
            use_fuzzy=use_fuzzy
        )
        return impact
    except Exception as e:
        logger.error(f"Error analyzing impact: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/stats/cache")
async def get_cache_statistics():
    """Get cache statistics."""
    return get_cache_stats()


@app.get("/api/v1/stats/database")
async def get_database_statistics():
    """Get database statistics."""
    if not analyzer:
        raise HTTPException(status_code=503, detail="Analyzer not initialized")
    
    try:
        # Get basic database stats
        from src.database import get_db_manager
        db = get_db_manager()
        session = db.get_session()
        from src.database import Violation, Inspection
        from sqlalchemy import func
        
        total_violations = session.query(func.count(Violation.id)).scalar() or 0
        total_inspections = session.query(func.count(Inspection.id)).scalar() or 0
        
        session.close()
        
        return {
            "total_violations": total_violations,
            "total_inspections": total_inspections,
            "database_url": str(db.database_url)
        }
    except Exception as e:
        logger.error(f"Error getting database stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run(app, host="0.0.0.0", port=8000)

