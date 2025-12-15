"""
Database-backed OSHA Analyzer
Analysis functions using database queries instead of in-memory DataFrames.
"""

# Standard library imports
from pathlib import Path
from typing import Dict, Any, Optional

# Third-party imports
import pandas as pd
from sqlalchemy import func, and_, or_

# Local imports
from .cache import cached
from .database import get_db_manager, Inspection, Violation
from .db_loader import DatabaseDataLoader


class OSHAAnalyzerDB:
    """Database-backed OSHA analyzer for improved performance."""
    
    def __init__(self, data_dir: Optional[Path] = None, database_url: Optional[str] = None, 
                 use_cache: bool = True):
        """
        Initialize analyzer with database backend.
        
        Args:
            data_dir: Directory containing data files
            database_url: Optional database URL (defaults to SQLite in data_dir)
            use_cache: If True, cache query results (default: True)
        """
        self.data_dir = data_dir or Path(__file__).parent.parent / "data"
        self.db = get_db_manager(database_url=database_url, data_dir=self.data_dir)
        self.db_loader = DatabaseDataLoader(data_dir=self.data_dir, database_url=database_url)
        self._cache = {} if use_cache else None
    
    def search_violations(
        self,
        state: Optional[str] = None,
        naics_prefix: Optional[str] = None,
        year: Optional[int] = None,
        keyword: Optional[str] = None,
        min_penalty: Optional[float] = None,
        limit: int = 100,
        offset: int = 0
    ) -> pd.DataFrame:
        """
        Search violations with filters using database queries.
        
        Args:
            state: State filter
            naics_prefix: NAICS code prefix filter
            year: Year filter
            keyword: Keyword search in standard
            min_penalty: Minimum penalty filter
            limit: Maximum number of results (default: 100, max: 10000)
            offset: Offset for pagination (default: 0)
        
        Returns:
            DataFrame with violations
        """
        # Cap limit to prevent memory issues
        limit = min(limit, 10000)
        
        session = self.db.get_session()
        try:
            query = session.query(Violation).filter(Violation.agency == "OSHA")
            
            if state:
                query = query.filter(Violation.site_state == state.upper())
            
            if naics_prefix:
                query = query.filter(Violation.naics_code.like(f"{naics_prefix}%"))
            
            if year:
                query = query.filter(Violation.year == year)
            
            if keyword:
                keyword_lower = keyword.lower()
                query = query.filter(func.lower(Violation.standard).like(f"%{keyword_lower}%"))
            
            if min_penalty:
                query = query.filter(Violation.current_penalty >= min_penalty)
            
            # Apply pagination
            query = query.offset(offset).limit(limit)
            
            df = pd.read_sql(query.statement, session.bind)
            return df
        finally:
            session.close()
    
    def count_violations(
        self,
        state: Optional[str] = None,
        naics_prefix: Optional[str] = None,
        year: Optional[int] = None,
        keyword: Optional[str] = None,
        min_penalty: Optional[float] = None
    ) -> int:
        """Count violations matching filters (for pagination)."""
        from sqlalchemy import func
        
        session = self.db.get_session()
        try:
            query = session.query(func.count(Violation.id)).filter(Violation.agency == "OSHA")
            
            if state:
                query = query.filter(Violation.site_state == state.upper())
            if naics_prefix:
                query = query.filter(Violation.naics_code.like(f"{naics_prefix}%"))
            if year:
                query = query.filter(Violation.year == year)
            if keyword:
                keyword_lower = keyword.lower()
                query = query.filter(func.lower(Violation.standard).like(f"%{keyword_lower}%"))
            if min_penalty:
                query = query.filter(Violation.current_penalty >= min_penalty)
            
            return query.scalar() or 0
        finally:
            session.close()
    
    @cached(ttl=1800)  # Cache for 30 minutes
    def top_violations(self, n: int = 10, year: Optional[int] = None) -> pd.DataFrame:
        """Get most frequently cited OSHA standards using database query."""
        session = self.db.get_session()
        try:
            query = session.query(
                Violation.standard,
                func.count(Violation.id).label('citation_count'),
                func.avg(Violation.current_penalty).label('avg_penalty')
            ).filter(Violation.agency == "OSHA")
            
            if year:
                query = query.filter(Violation.year == year)
            # Filter out NULL standards
            query = query.filter(Violation.standard.isnot(None))
            query = query.filter(Violation.standard != "")
            
            results = query.group_by(Violation.standard).order_by(
                func.count(Violation.id).desc()
            ).limit(n).all()
            
            if not results:
                return pd.DataFrame(columns=["standard", "citation_count", "avg_penalty"])
            
            df = pd.DataFrame([{
                "standard": r.standard,
                "citation_count": r.citation_count,
                "avg_penalty": round(r.avg_penalty, 2) if r.avg_penalty else 0
            } for r in results])
            
            return df
        finally:
            session.close()
    
    @cached(ttl=1800)  # Cache for 30 minutes
    def violations_by_state(self, year: Optional[int] = None) -> pd.DataFrame:
        """Get violation counts by state using database query."""
        session = self.db.get_session()
        try:
            query = session.query(
                Violation.site_state.label('state'),
                func.count(Violation.id).label('violation_count'),
                func.sum(Violation.current_penalty).label('total_penalties')
            ).filter(Violation.agency == "OSHA")
            
            if year:
                query = query.filter(Violation.year == year)
            
            # Filter out NULL and empty states
            query = query.filter(Violation.site_state.isnot(None))
            query = query.filter(Violation.site_state != "")
            
            results = query.group_by(Violation.site_state).all()
            
            if not results:
                return pd.DataFrame(columns=["state", "violation_count", "total_penalties"])
            
            df = pd.DataFrame([{
                "state": r.state,
                "violation_count": r.violation_count,
                "total_penalties": round(r.total_penalties, 2) if r.total_penalties else 0
            } for r in results])
            
            return df.sort_values("violation_count", ascending=False)
        finally:
            session.close()
    
    def _classify_unknown_naics(self, company_name: str, company_name_normalized: Optional[str] = None, 
                                  session=None) -> Optional[str]:
        """
        Classify unknown NAICS codes using multiple methods:
        1. Match to known NAICS codes for the same company
        2. Keyword matching on company name
        
        Returns 2-digit NAICS sector code or None.
        """
        if not company_name:
            return None
        
        # Method 1: Try to match by company name to known violations
        if session and company_name_normalized:
            from .database import Violation
            known_sector = session.query(
                func.substr(Violation.naics_code, 1, 2).label('sector')
            ).filter(
                Violation.agency == "OSHA",
                Violation.company_name_normalized == company_name_normalized,
                Violation.naics_code.isnot(None),
                Violation.naics_code != "",
                Violation.naics_code != "0",
                Violation.naics_code != "0.0",
                ~Violation.naics_code.like("0%"),
                func.length(Violation.naics_code) >= 2
            ).distinct().first()
            
            if known_sector and known_sector[0]:
                return known_sector[0]
        
        # Method 2: Keyword matching
        company_upper = company_name.upper()
        
        # Industry keyword mappings (order matters - more specific first)
        keyword_mappings = [
            # Public Administration (92)
            (["POSTAL SERVICE", "VETERANS ADMINISTRATION", "DEPARTMENT OF", "FEDERAL", "GOVERNMENT"], "92"),
            # Healthcare (62)
            (["HOSPITAL", "MEDICAL CENTER", "CLINIC", "HEALTH", "CARE CENTER"], "62"),
            # Education (61)
            (["SCHOOL", "UNIVERSITY", "COLLEGE", "EDUCATION"], "61"),
            # Transportation (48)
            (["TRANSPORT", "SHIPPING", "LOGISTICS", "DELIVERY", "PARCEL SERVICE", "RAILROAD", "AIRLINE"], "48"),
            # Retail Trade (44, 45)
            (["STORE", "RETAIL", "MARKET", "SUPERMARKET", "SHOPPING"], "44"),
            # Manufacturing (31, 32, 33)
            (["STEEL", "MANUFACTURING", "FACTORY", "PAPER", "CHEMICAL", "ELECTRIC", "MOTOR", "AUTOMOTIVE"], "33"),
            # Construction (23)
            (["CONSTRUCTION", "BUILDING", "CONTRACTOR"], "23"),
            # Mining (21)
            (["MINING", "MINE", "COAL"], "21"),
            # Utilities (22)
            (["POWER", "ELECTRIC UTILITY", "GAS COMPANY", "WATER COMPANY"], "22"),
            # Accommodation/Food (72)
            (["HOTEL", "RESTAURANT", "FOOD SERVICE", "LODGING"], "72"),
        ]
        
        for keywords, sector_code in keyword_mappings:
            if any(keyword in company_upper for keyword in keywords):
                return sector_code
        
        return None
    
    @cached(ttl=1800)  # Cache for 30 minutes
    def violations_by_industry(self, year: Optional[int] = None, n: int = 15, classify_unknown: bool = True) -> pd.DataFrame:
        """Get violation counts by NAICS industry code using database query."""
        session = self.db.get_session()
        try:
            # First, get violations with known NAICS codes
            query_known = session.query(
                func.substr(Violation.naics_code, 1, 2).label('naics_sector'),
                func.count(Violation.id).label('violation_count'),
                func.avg(Violation.current_penalty).label('avg_penalty')
            ).filter(
                Violation.agency == "OSHA",
                Violation.naics_code.isnot(None),
                Violation.naics_code != "",
                Violation.naics_code != "0",
                Violation.naics_code != "0.0",
                ~Violation.naics_code.like("0%"),
                func.length(Violation.naics_code) >= 2
            )
            
            if year:
                query_known = query_known.filter(Violation.year == year)
            
            known_results = query_known.group_by('naics_sector').all()
            
            # Get unknown violations and classify them if requested
            unknown_results = []
            unclassified_count = 0
            if classify_unknown:
                query_unknown = session.query(
                    Violation.company_name,
                    func.count(Violation.id).label('violation_count'),
                    func.avg(Violation.current_penalty).label('avg_penalty')
                ).filter(
                    Violation.agency == "OSHA",
                    Violation.naics_code.in_(["0", "0.0"])
                )
                
                if year:
                    query_unknown = query_unknown.filter(Violation.year == year)
                
                # Get company name normalized for better matching
                query_unknown_with_norm = session.query(
                    Violation.company_name,
                    Violation.company_name_normalized,
                    func.count(Violation.id).label('violation_count'),
                    func.avg(Violation.current_penalty).label('avg_penalty')
                ).filter(
                    Violation.agency == "OSHA",
                    Violation.naics_code.in_(["0", "0.0"])
                )
                
                if year:
                    query_unknown_with_norm = query_unknown_with_norm.filter(Violation.year == year)
                
                unknown_data = query_unknown_with_norm.group_by(
                    Violation.company_name, Violation.company_name_normalized
                ).all()
                
                # Classify each company
                classified = {}
                total_classified = 0
                for company_name, company_name_normalized, count, avg_penalty in unknown_data:
                    sector = self._classify_unknown_naics(
                        company_name, 
                        company_name_normalized, 
                        session=session
                    )
                    if sector:
                        if sector not in classified:
                            classified[sector] = {'count': 0, 'penalty_sum': 0, 'penalty_count': 0}
                        classified[sector]['count'] += count
                        total_classified += count
                        if avg_penalty:
                            classified[sector]['penalty_sum'] += avg_penalty * count
                            classified[sector]['penalty_count'] += count
                
                # Convert classified to results format
                for sector, data in classified.items():
                    avg_penalty = (data['penalty_sum'] / data['penalty_count']) if data['penalty_count'] > 0 else 0
                    unknown_results.append((sector, data['count'], avg_penalty))
                
                # Calculate remaining unclassified
                total_unknown = sum(count for _, count, _ in unknown_data)
                unclassified_count = total_unknown - total_classified
            
            # Combine known and classified unknown results
            all_results = {}
            for sector, count, avg_penalty in known_results:
                if sector not in all_results:
                    all_results[sector] = {'count': 0, 'penalty_sum': 0, 'penalty_count': 0}
                all_results[sector]['count'] += count
                if avg_penalty:
                    all_results[sector]['penalty_sum'] += avg_penalty * count
                    all_results[sector]['penalty_count'] += count
            
            for sector, count, avg_penalty in unknown_results:
                if sector not in all_results:
                    all_results[sector] = {'count': 0, 'penalty_sum': 0, 'penalty_count': 0}
                all_results[sector]['count'] += count
                if avg_penalty:
                    all_results[sector]['penalty_sum'] += avg_penalty * count
                    all_results[sector]['penalty_count'] += count
            
            # Add remaining unknown (unclassified) if any
            if classify_unknown and unclassified_count > 0:
                if "00" not in all_results:
                    all_results["00"] = {'count': 0, 'penalty_sum': 0, 'penalty_count': 0}
                all_results["00"]['count'] += unclassified_count
            
            if not all_results:
                return pd.DataFrame(columns=["naics_sector", "violation_count", "sector_name", "avg_penalty"])
            
            # Convert to list and sort
            results_list = []
            for sector, data in all_results.items():
                avg_penalty = (data['penalty_sum'] / data['penalty_count']) if data['penalty_count'] > 0 else 0
                results_list.append((sector, data['count'], avg_penalty))
            
            results_list.sort(key=lambda x: x[1], reverse=True)
            results_list = results_list[:n]  # Limit to top n
            
            # Add sector names
            sector_names = {
                "00": "Unknown",  # For unclassified violations
                "11": "Agriculture", "21": "Mining", "22": "Utilities",
                "23": "Construction", "31": "Manufacturing", "32": "Manufacturing",
                "33": "Manufacturing", "42": "Wholesale Trade", "44": "Retail Trade",
                "45": "Retail Trade", "48": "Transportation", "49": "Warehousing",
                "51": "Information", "52": "Finance", "53": "Real Estate",
                "54": "Professional Services", "55": "Management", "56": "Admin Services",
                "61": "Education", "62": "Healthcare", "71": "Arts/Entertainment",
                "72": "Accommodation/Food", "81": "Other Services", "92": "Public Admin"
            }
            
            df = pd.DataFrame([{
                "naics_sector": r[0],
                "violation_count": r[1],
                "sector_name": sector_names.get(r[0], "Unknown"),
                "avg_penalty": round(r[2], 2) if r[2] else 0
            } for r in results_list])
            
            return df
        finally:
            session.close()
    
    def penalty_summary(self, group_by: str = "viol_type") -> pd.DataFrame:
        """Summarize penalties by grouping variable using database query."""
        session = self.db.get_session()
        try:
            # Map group_by to column
            column_map = {
                "viol_type": Violation.viol_type,
                "standard": Violation.standard,
                "state": Violation.site_state,
            }
            
            if group_by not in column_map:
                return pd.DataFrame()
            
            group_column = column_map[group_by]
            
            query = session.query(
                group_column.label('group_value'),
                func.count(Violation.id).label('count'),
                func.sum(Violation.current_penalty).label('total_penalty'),
                func.avg(Violation.current_penalty).label('avg_penalty'),
                func.max(Violation.current_penalty).label('max_penalty')
            ).filter(Violation.agency == "OSHA")
            
            # Filter out NULL values for group column
            query = query.filter(group_column.isnot(None))
            query = query.filter(group_column != "")
            
            results = query.group_by(group_column).order_by(
                func.sum(Violation.current_penalty).desc()
            ).all()
            
            if not results:
                return pd.DataFrame(columns=[group_by, "count", "total_penalty", "avg_penalty", "max_penalty"])
            
            df = pd.DataFrame([{
                group_by: r.group_value,
                "count": r.count,
                "total_penalty": round(r.total_penalty, 2) if r.total_penalty else 0,
                "avg_penalty": round(r.avg_penalty, 2) if r.avg_penalty else 0,
                "max_penalty": round(r.max_penalty, 2) if r.max_penalty else 0
            } for r in results])
            
            return df
        finally:
            session.close()
    
    def trend_analysis(self, metric: str = "violations") -> pd.DataFrame:
        """Analyze trends over time using database query."""
        session = self.db.get_session()
        try:
            if metric == "violations":
                # Use pd.read_sql to avoid SQLAlchemy query evaluation issues
                sql = """
                    SELECT year, COUNT(*) as count
                    FROM violations
                    WHERE agency = 'OSHA'
                      AND year IS NOT NULL
                      AND year >= 2000
                    GROUP BY year
                    ORDER BY year
                """
                df = pd.read_sql(sql, session.bind)
                df.columns = ['year', 'count']
                
            elif metric == "inspections":
                # Use pd.read_sql to avoid SQLAlchemy query evaluation issues
                sql = """
                    SELECT year, COUNT(*) as count
                    FROM inspections
                    WHERE year IS NOT NULL
                      AND year >= 2000
                    GROUP BY year
                    ORDER BY year
                """
                df = pd.read_sql(sql, session.bind)
                df.columns = ['year', 'count']
                
            elif metric == "penalties":
                # Use pd.read_sql to avoid SQLAlchemy query evaluation issues
                sql = """
                    SELECT year, COALESCE(SUM(current_penalty), 0) as total_penalty
                    FROM violations
                    WHERE agency = 'OSHA'
                      AND year IS NOT NULL
                      AND year >= 2000
                    GROUP BY year
                    ORDER BY year
                """
                df = pd.read_sql(sql, session.bind)
                df.columns = ['year', 'total_penalty']
                # Ensure numeric type before rounding
                df['total_penalty'] = pd.to_numeric(df['total_penalty'], errors='coerce').round(2)
            else:
                return pd.DataFrame()
            
            return df
        finally:
            session.close()
    
    def industry_benchmark(self, naics_code: str) -> Dict[str, Any]:
        """Compare a specific industry to national averages using database query."""
        session = self.db.get_session()
        try:
            naics_prefix = naics_code[:2]
            
            # Industry-specific query
            industry_query = session.query(
                func.count(Violation.id).label('count'),
                func.avg(Violation.current_penalty).label('avg_penalty')
            ).filter(
                Violation.agency == "OSHA",
                Violation.naics_code.like(f"{naics_prefix}%")
            )
            
            industry_result = industry_query.first()
            
            # National query
            national_query = session.query(
                func.count(Violation.id).label('count'),
                func.avg(Violation.current_penalty).label('avg_penalty')
            ).filter(Violation.agency == "OSHA")
            
            national_result = national_query.first()
            
            industry_count = industry_result.count if industry_result else 0
            national_count = national_result.count if national_result else 0
            
            benchmark = {
                "naics_code": naics_code,
                "industry_violation_count": industry_count,
                "national_violation_count": national_count,
                "industry_pct_of_total": round(industry_count / national_count * 100, 2) if national_count > 0 else 0,
                "industry_avg_penalty": round(industry_result.avg_penalty, 2) if industry_result and industry_result.avg_penalty else 0,
                "national_avg_penalty": round(national_result.avg_penalty, 2) if national_result and national_result.avg_penalty else 0
            }
            
            return benchmark
        finally:
            session.close()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        return self.db.get_stats()

