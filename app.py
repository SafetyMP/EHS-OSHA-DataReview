"""
Multi-Agency Compliance Analyzer Dashboard
Interactive Streamlit app for exploring EHS compliance data across OSHA, EPA, MSHA, FDA and more.
"""

# Standard library imports
import sys
from pathlib import Path

# Third-party imports
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from sqlalchemy import func

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

# Local imports
from src.analyzer import OSHAAnalyzer, get_standard_description, COMMON_STANDARDS
from src.compliance_analyzer import ComplianceAnalyzer
from src.violation_impact_viz import plot_violation_timeline, plot_rate_comparison, plot_impact_summary

# Page config
st.set_page_config(
    page_title="Multi-Agency Compliance Analyzer",
    page_icon="🔍",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .metric-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
    }
    .big-number {
        font-size: 36px;
        font-weight: bold;
        color: #1f4e79;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def load_analyzer():
    """Load OSHA analyzer with caching - uses database backend for performance."""
    data_dir = Path(__file__).parent / "data"
    
    # Check if database exists, use it if available
    db_path = data_dir / "compliance.db"
    if db_path.exists():
        # Use database backend (much faster)
        from src.analyzer_db import OSHAAnalyzerDB
        return OSHAAnalyzerDB(data_dir=data_dir)
    else:
        # Fallback to CSV-based analyzer
        return OSHAAnalyzer()


@st.cache_resource
def load_compliance_analyzer():
    """Load multi-agency compliance analyzer with caching."""
    data_dir = Path(__file__).parent / "data"
    return ComplianceAnalyzer(data_dir=data_dir)


def main():
    st.title("🔍 Multi-Agency Compliance Analyzer")
    st.markdown("*Explore environmental, health, and safety compliance across OSHA, EPA, MSHA, FDA and more*")
    
    # Check if data exists
    data_dir = Path(__file__).parent / "data"
    if not data_dir.exists() or not any(data_dir.glob("*.csv")):
        st.warning("⚠️ Data not found. Please run `python src/data_loader.py` first to download OSHA data.")
        st.code("python src/data_loader.py", language="bash")
        return
    
    # Load data
    with st.spinner("Loading OSHA data..."):
        try:
            analyzer = load_analyzer()
        except Exception as e:
            st.error(f"Error loading data: {e}")
            return
    
    # Sidebar filters
    st.sidebar.header("Filters")
    
    # Year filter - handle both CSV and database analyzers
    years = []
    if hasattr(analyzer, 'inspections') and analyzer.inspections is not None:
        # CSV-based analyzer
        if "year" in analyzer.inspections.columns:
            years = sorted(analyzer.inspections["year"].dropna().unique())
            years = [int(y) for y in years if y >= 2000]
    elif hasattr(analyzer, 'db'):
        # Database analyzer - query for available years
        try:
            from src.database import Inspection
            session = analyzer.db.get_session()
            try:
                year_results = session.query(Inspection.year).distinct().filter(Inspection.year >= 2000).all()
                years = sorted([int(y[0]) for y in year_results if y[0] is not None])
            finally:
                session.close()
        except Exception:
            years = []
    
    selected_year = st.sidebar.selectbox(
        "Year",
        options=["All Years"] + years[::-1],
        index=0
    )
    # Convert to integer if not "All Years"
    year_filter = None if selected_year == "All Years" else int(selected_year)
    
    # State filter - handle both CSV and database analyzers
    states = []
    if hasattr(analyzer, 'violations') and analyzer.violations is not None:
        # CSV-based analyzer
        if "site_state" in analyzer.violations.columns:
            states = sorted(analyzer.violations["site_state"].dropna().unique())
    elif hasattr(analyzer, 'db'):
        # Database analyzer - query for available states
        try:
            from src.database import Violation
            session = analyzer.db.get_session()
            try:
                state_results = session.query(Violation.site_state).distinct().filter(Violation.site_state.isnot(None)).all()
                states = sorted([s[0] for s in state_results if s[0]])
            finally:
                session.close()
        except Exception:
            states = []
    
    selected_state = st.sidebar.selectbox(
        "State",
        options=["All States"] + list(states),
        index=0
    )
    state_filter = None if selected_state == "All States" else selected_state
    
    # Main content tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Overview", 
        "🏭 By Industry", 
        "📍 By State",
        "🔎 Search",
        "🏢 Company Comparison"
    ])
    
    # TAB 1: Overview
    with tab1:
        st.header("Enforcement Overview")
        
        # Key metrics
        col1, col2, col3, col4 = st.columns(4)
        
        # Get violations metrics - handle both CSV and database analyzers
        if hasattr(analyzer, 'violations') and analyzer.violations is not None:
            # CSV-based analyzer
            violations_df = analyzer.violations.copy()
            if year_filter:
                violations_df = violations_df[violations_df["year"] == year_filter]
            if state_filter:
                violations_df = violations_df[violations_df["site_state"] == state_filter]
            
            total_violations = len(violations_df)
            total_penalties = violations_df["current_penalty"].sum() if "current_penalty" in violations_df.columns else 0
            avg_penalty = violations_df["current_penalty"].mean() if "current_penalty" in violations_df.columns else 0
        else:
            # Database analyzer - use aggregate queries for accurate counts
            from src.database import Violation
            session = analyzer.db.get_session()
            try:
                # Build query for counts and aggregates
                query = session.query(
                    func.count(Violation.id).label('total'),
                    func.sum(Violation.current_penalty).label('total_penalty'),
                    func.avg(Violation.current_penalty).label('avg_penalty')
                ).filter(Violation.agency == "OSHA")
                
                if year_filter:
                    query = query.filter(Violation.year == year_filter)
                if state_filter:
                    query = query.filter(Violation.site_state == state_filter.upper())
                
                result = query.first()
                total_violations = result.total or 0
                total_penalties = result.total_penalty or 0
                avg_penalty = result.avg_penalty or 0
            finally:
                session.close()
        
        with col1:
            st.metric("Total Violations", f"{total_violations:,}")
        
        with col2:
            st.metric("Total Penalties", f"${total_penalties:,.2f}")
        
        with col3:
            st.metric("Avg Penalty", f"${avg_penalty:,.0f}")
        
        with col4:
            # Get unique establishments count - query inspections table for database analyzer
            if hasattr(analyzer, 'db'):
                # Database analyzer - query inspections table
                try:
                    from src.database import Inspection
                    session = analyzer.db.get_session()
                    try:
                        # Count unique establishments with filters
                        query = session.query(func.count(func.distinct(Inspection.estab_name)))
                        if year_filter:
                            query = query.filter(Inspection.year == year_filter)
                        if state_filter:
                            query = query.filter(Inspection.site_state == state_filter.upper())
                        query = query.filter(Inspection.estab_name.isnot(None))
                        query = query.filter(Inspection.estab_name != "")
                        unique_establishments = query.scalar() or 0
                    finally:
                        session.close()
                except Exception:
                    # Fallback to company_name from violations
                    unique_establishments = violations_df["company_name"].nunique() if "company_name" in violations_df.columns else 0
            else:
                # CSV-based analyzer
                if "estab_name" in violations_df.columns:
                    unique_establishments = violations_df["estab_name"].nunique()
                elif "company_name" in violations_df.columns:
                    unique_establishments = violations_df["company_name"].nunique()
                else:
                    unique_establishments = 0
            st.metric("Establishments", f"{unique_establishments:,}")
        
        st.markdown("---")
        
        # Trend chart
        st.subheader("Inspection Trends Over Time")
        trend_data = analyzer.trend_analysis("violations")
        if not trend_data.empty:
            trend_data = trend_data[trend_data["year"] >= 2000]
            fig = px.line(
                trend_data, 
                x="year", 
                y="count",
                title="Violations by Year",
                labels={"year": "Year", "count": "Number of Violations"}
            )
            fig.update_traces(line_color="#1f4e79")
            st.plotly_chart(fig, use_container_width=True)
        
        # Top violations
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Most Cited Standards")
            top_violations = analyzer.top_violations(n=10, year=year_filter)
            if not top_violations.empty:
                top_violations["description"] = top_violations["standard"].apply(get_standard_description)
                fig = px.bar(
                    top_violations,
                    x="citation_count",
                    y="standard",
                    orientation="h",
                    title="Top 10 Cited Standards",
                    labels={"standard": "OSHA Standard", "citation_count": "Citations"},
                    hover_data=["description"]
                )
                fig.update_layout(yaxis=dict(autorange="reversed"))
                fig.update_traces(marker_color="#1f4e79")
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.subheader("Penalties by Violation Type")
            penalty_summary = analyzer.penalty_summary("viol_type")
            if not penalty_summary.empty:
                fig = px.pie(
                    penalty_summary,
                    values="total_penalty",
                    names="viol_type",
                    title="Total Penalties by Type"
                )
                st.plotly_chart(fig, use_container_width=True)
    
    # TAB 2: By Industry
    with tab2:
        st.header("Industry Analysis")
        
        industry_data = analyzer.violations_by_industry(year=year_filter, n=15, classify_unknown=True)
        if not industry_data.empty:
            col1, col2 = st.columns(2)
            
            with col1:
                fig = px.bar(
                    industry_data,
                    x="violation_count",
                    y="sector_name",
                    orientation="h",
                    title="Violations by Industry Sector",
                    labels={"sector_name": "Industry", "violation_count": "Violations"}
                )
                fig.update_layout(yaxis=dict(autorange="reversed"))
                fig.update_traces(marker_color="#1f4e79")
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                if "avg_penalty" in industry_data.columns:
                    fig = px.bar(
                        industry_data.sort_values("avg_penalty", ascending=True),
                        x="avg_penalty",
                        y="sector_name",
                        orientation="h",
                        title="Average Penalty by Industry",
                        labels={"sector_name": "Industry", "avg_penalty": "Avg Penalty ($)"}
                    )
                    fig.update_layout(yaxis=dict(autorange="reversed"))
                    fig.update_traces(marker_color="#c44e52")
                    st.plotly_chart(fig, use_container_width=True)
            
            # Data table
            st.subheader("Industry Data")
            st.dataframe(industry_data, use_container_width=True)
    
    # TAB 3: By State
    with tab3:
        st.header("Geographic Analysis")
        
        state_data = analyzer.violations_by_state(year=year_filter)
        if not state_data.empty:
            # Map
            fig = px.choropleth(
                state_data,
                locations="state",
                locationmode="USA-states",
                color="violation_count",
                scope="usa",
                title="Violations by State",
                color_continuous_scale="Blues",
                labels={"violation_count": "Violations"}
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Top states table
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Top 10 States by Violations")
                st.dataframe(state_data.head(10), use_container_width=True)
            
            with col2:
                if "total_penalties" in state_data.columns:
                    st.subheader("Top 10 States by Penalties")
                    penalty_sorted = state_data.sort_values("total_penalties", ascending=False).head(10)
                    st.dataframe(penalty_sorted, use_container_width=True)
    
    # TAB 4: Search
    with tab4:
        st.header("Search Violations")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            search_states = list(states) if states else []
            search_state = st.selectbox("State", options=["Any"] + search_states, key="search_state")
        
        with col2:
            search_keyword = st.text_input("Standard/Keyword", placeholder="e.g., 1910.134")
        
        with col3:
            min_penalty = st.number_input("Minimum Penalty ($)", min_value=0, value=0, step=1000)
        
        # Pagination controls
        page_size = st.selectbox("Results per page", [50, 100, 250, 500, 1000], index=1)
        
        search_clicked = st.button("Search", type="primary", key="search_button")
        
        # Get current page
        page = st.session_state.get('search_page', 1)
        offset = (page - 1) * page_size
        
        # Reset to page 1 on new search
        if search_clicked:
            st.session_state.search_page = 1
            page = 1
            offset = 0
            st.session_state.search_executed = True
        
        # Execute search if button clicked or if we're on a page > 1 (after initial search)
        if search_clicked or (page > 1 and st.session_state.get('search_executed', False)):
            # Get total count if available (for database backend)
            total_count = None
            if hasattr(analyzer, 'count_violations'):
                try:
                    total_count = analyzer.count_violations(
                        state=search_state if search_state != "Any" else None,
                        year=year_filter,
                        keyword=search_keyword if search_keyword else None,
                        min_penalty=min_penalty if min_penalty > 0 else None,
                    )
                except:
                    pass
            
            results = analyzer.search_violations(
                state=search_state if search_state != "Any" else None,
                year=year_filter,
                keyword=search_keyword if search_keyword else None,
                min_penalty=min_penalty if min_penalty > 0 else None,
                limit=page_size,
                offset=offset
            )
            
            if not results.empty:
                    result_count = len(results)
                    if total_count:
                        st.success(f"Found {total_count:,} violations (showing {result_count} on page {page})")
                    else:
                        st.success(f"Found {result_count} violations")
                    
                    # Display columns
                    display_cols = ["estab_name", "site_state", "standard", "viol_type", "current_penalty"]
                    display_cols = [c for c in display_cols if c in results.columns]
                    
                    st.dataframe(results[display_cols], use_container_width=True)
                    
                    # Pagination controls
                    if total_count and total_count > page_size:
                        total_pages = (total_count + page_size - 1) // page_size
                        col1, col2, col3 = st.columns([1, 2, 1])
                        with col1:
                            if st.button("◀ Previous", disabled=(page <= 1), key="prev_page"):
                                st.session_state.search_page = page - 1
                                st.rerun()
                        with col2:
                            st.write(f"Page {page} of {total_pages}")
                        with col3:
                            if st.button("Next ▶", disabled=(page >= total_pages), key="next_page"):
                                st.session_state.search_page = page + 1
                                st.rerun()
                    
                    # Download button (downloads current page results)
                    csv = results.to_csv(index=False)
                    st.download_button(
                        "Download Results (CSV)",
                        csv,
                        "osha_search_results.csv",
                        "text/csv"
                    )
            else:
                st.warning("No violations found matching your criteria.")
    
    # TAB 5: Company Comparison
    with tab5:
        st.header("Cross-Agency Company Compliance")
        st.markdown("Search for a company and compare compliance records across multiple regulatory agencies.")
        
        # Load compliance analyzer
        try:
            comp_analyzer = load_compliance_analyzer()
            available_agencies = comp_analyzer.get_available_agencies()
            
            if not available_agencies:
                st.warning("⚠️ No agency data available. Please ensure data files are downloaded.")
                st.info("OSHA data can be downloaded by running: `python src/data_loader.py`")
                st.info("EPA, MSHA, and FDA data loaders are included but require data integration.")
            else:
                st.info(f"📋 Available agencies: {', '.join(available_agencies)}")
                
                # Company search
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    company_search = st.text_input(
                        "Company Name",
                        placeholder="Enter company name (e.g., Acme Corporation)",
                        key="company_search"
                    )
                
                with col2:
                    st.write("")  # Spacing
                    st.write("")  # Spacing
                    search_button = st.button("Search Company", type="primary")
                
                # Agency selection
                selected_agencies = st.multiselect(
                    "Select Agencies to Search",
                    options=available_agencies,
                    default=available_agencies,
                    help="Select which agencies to include in the search"
                )
                
                # Fuzzy matching threshold
                fuzzy_threshold = st.slider(
                    "Fuzzy Matching Threshold",
                    min_value=50,
                    max_value=100,
                    value=75,
                    help="Minimum similarity score (0-100). Lower = more matches, Higher = stricter matching"
                )
                
                if search_button and company_search:
                    with st.spinner(f"Searching for '{company_search}' across agencies..."):
                        results = comp_analyzer.search_company(
                            company_search,
                            agencies=selected_agencies if selected_agencies else None,
                            use_fuzzy=True,
                            fuzzy_threshold=fuzzy_threshold
                        )
                        
                        if not results.empty:
                            # Show fuzzy matching info
                            if 'similarity_score' in results.columns:
                                avg_similarity = results['similarity_score'].mean()
                                st.success(
                                    f"Found {len(results)} violations for '{company_search}' "
                                    f"(Avg similarity: {avg_similarity:.1f}%)"
                                )
                                
                                # Show top matches with similarity scores
                                if len(results) > 0:
                                    top_matches = results.groupby(
                                        results.get('company_name', results.get('estab_name', results.get('facility_name', pd.Series(['']))))
                                    )['similarity_score'].max().sort_values(ascending=False).head(5)
                                    
                                    if len(top_matches) > 1:
                                        st.info(f"**Top matches:** {', '.join([f'{name} ({score:.0f}%)' for name, score in top_matches.items()][:3])}")
                            else:
                                st.success(f"Found {len(results)} violations for '{company_search}'")
                            
                            # Get summary with risk score
                            summary = comp_analyzer.compare_company_across_agencies(
                                company_search,
                                agencies=selected_agencies if selected_agencies else None,
                                include_risk_score=True,
                                use_fuzzy=True
                            )
                            
                            # Display summary metrics
                            col1, col2, col3, col4, col5 = st.columns(5)
                            
                            with col1:
                                st.metric("Total Violations", f"{summary['total_violations']:,}")
                            
                            with col2:
                                st.metric("Total Penalties", f"${summary['total_penalties']:,.0f}")
                            
                            with col3:
                                st.metric("Agencies with Violations", len(summary['agencies']))
                            
                            with col4:
                                st.metric("Company Name", company_search)
                            
                            # Risk Score
                            with col5:
                                if 'risk_score' in summary:
                                    risk_score = summary['risk_score']['composite_score']
                                    risk_level = summary['risk_score']['risk_level']
                                    
                                    # Color based on risk level
                                    if risk_level == 'Critical':
                                        delta_color = "inverse"
                                        delta_value = "Critical Risk"
                                    elif risk_level == 'High':
                                        delta_color = "inverse"
                                        delta_value = "High Risk"
                                    elif risk_level == 'Medium':
                                        delta_color = "off"
                                        delta_value = "Medium Risk"
                                    else:
                                        delta_color = "normal"
                                        delta_value = "Low Risk"
                                    
                                    st.metric(
                                        "Risk Score",
                                        f"{risk_score:.0f}/100",
                                        delta=delta_value,
                                        delta_color=delta_color
                                    )
                                else:
                                    st.metric("Risk Score", "N/A")
                            
                            # Risk Score Details
                            if 'risk_score' in summary:
                                st.markdown("---")
                                st.subheader("📊 Risk Score Breakdown")
                                
                                risk_data = summary['risk_score']
                                
                                col1, col2 = st.columns(2)
                                
                                with col1:
                                    # Risk level badge
                                    risk_level = risk_data['risk_level']
                                    risk_colors = {
                                        'Critical': '🔴',
                                        'High': '🟠',
                                        'Medium': '🟡',
                                        'Low': '🟢'
                                    }
                                    st.markdown(
                                        f"### {risk_colors.get(risk_level, '⚪')} **Risk Level: {risk_level}** "
                                        f"(Score: {risk_data['composite_score']:.1f}/100)"
                                    )
                                    
                                    # Component scores
                                    st.markdown("**Component Scores:**")
                                    components = risk_data['component_scores']
                                    for component, score in components.items():
                                        component_name = component.replace('_', ' ').title()
                                        st.progress(score / 100, text=f"{component_name}: {score:.1f}")
                                
                                with col2:
                                    # Risk factors
                                    st.markdown("**Risk Factors:**")
                                    factors = risk_data['factors']
                                    
                                    st.markdown(f"- **Violations:** {factors.get('violation_count', 0):,}")
                                    st.markdown(f"- **Total Penalties:** ${factors.get('total_penalties', 0):,.2f}")
                                    st.markdown(f"- **Avg Penalty:** ${factors.get('avg_penalty', 0):,.2f}")
                                    st.markdown(f"- **Agencies:** {factors.get('unique_agencies', 0)} ({', '.join(factors.get('agencies', []))})")
                                    if factors.get('most_recent_violation'):
                                        st.markdown(f"- **Most Recent:** {factors['most_recent_violation']}")
                            
                            st.markdown("---")
                            
                            # Agency breakdown
                            if summary['agencies']:
                                st.subheader("Violations by Agency")
                                
                                # Create comparison chart
                                agency_data = []
                                for agency, data in summary['agencies'].items():
                                    agency_data.append({
                                        "Agency": agency,
                                        "Violations": data["violation_count"],
                                        "Total Penalties": data["penalties"].get("total", 0) if "penalties" in data else 0,
                                        "Avg Penalty": data["penalties"].get("average", 0) if "penalties" in data else 0
                                    })
                                
                                agency_df = pd.DataFrame(agency_data)
                                
                                col1, col2 = st.columns(2)
                                
                                with col1:
                                    fig = px.bar(
                                        agency_df,
                                        x="Agency",
                                        y="Violations",
                                        title="Violation Count by Agency",
                                        color="Agency",
                                        color_discrete_map={
                                            "OSHA": "#1f4e79",
                                            "EPA": "#2e7d32",
                                            "MSHA": "#d32f2f",
                                            "FDA": "#1976d2"
                                        }
                                    )
                                    st.plotly_chart(fig, use_container_width=True)
                                
                                with col2:
                                    if agency_df["Total Penalties"].sum() > 0:
                                        fig = px.bar(
                                            agency_df,
                                            x="Agency",
                                            y="Total Penalties",
                                            title="Total Penalties by Agency",
                                            color="Agency",
                                            color_discrete_map={
                                                "OSHA": "#1f4e79",
                                                "EPA": "#2e7d32",
                                                "MSHA": "#d32f2f",
                                                "FDA": "#1976d2"
                                            }
                                        )
                                        st.plotly_chart(fig, use_container_width=True)
                                
                                # Detailed agency breakdown
                                st.subheader("Detailed Agency Breakdown")
                                
                                for agency, data in summary['agencies'].items():
                                    with st.expander(f"{agency} - {data['violation_count']} violations"):
                                        col1, col2, col3 = st.columns(3)
                                        
                                        with col1:
                                            st.metric("Violations", data['violation_count'])
                                        
                                        if "penalties" in data and data["penalties"]:
                                            with col2:
                                                st.metric("Total Penalties", f"${data['penalties'].get('total', 0):,.0f}")
                                            with col3:
                                                st.metric("Avg Penalty", f"${data['penalties'].get('average', 0):,.0f}")
                                        
                                        # Show violation details if available
                                        if agency in summary.get('violations_by_agency', {}):
                                            violations_df = summary['violations_by_agency'][agency]
                                            
                                            # Display key columns
                                            display_cols = []
                                            for col in ["estab_name", "facility_name", "mine_name", "firm_name", 
                                                       "standard", "viol_type", "current_penalty", "penalty_amount",
                                                       "year", "site_state", "state"]:
                                                if col in violations_df.columns:
                                                    display_cols.append(col)
                                            
                                            if display_cols:
                                                st.dataframe(
                                                    violations_df[display_cols].head(100),
                                                    use_container_width=True,
                                                    height=300
                                                )
                                
                                # Violation Impact Analysis
                                st.markdown("---")
                                st.subheader("📈 Violation Impact Analysis")
                                st.markdown("Analyze whether violations increased or reduced subsequent violations.")
                                
                                # Use a stable key for session state
                                # Convert selected_agencies to a stable string representation
                                agencies_str = str(sorted(selected_agencies)) if selected_agencies else "all"
                                impact_key = f"impact_analysis_{company_search}_{agencies_str}"
                                
                                # Initialize session state key if it doesn't exist
                                if impact_key not in st.session_state:
                                    st.session_state[impact_key] = None
                                
                                # Button row
                                col_btn1, col_btn2 = st.columns([1, 4])
                                
                                # Perform analysis when button is clicked
                                with col_btn1:
                                    analyze_clicked = st.button("Analyze Violation Impact", type="secondary", key=f"analyze_btn_{company_search}")
                                
                                if analyze_clicked:
                                    with st.spinner("Analyzing violation impact..."):
                                        try:
                                            impact_analysis = comp_analyzer.analyze_violation_impact(
                                                company_search,
                                                agencies=selected_agencies if selected_agencies else None,
                                                use_fuzzy=True
                                            )
                                            st.session_state[impact_key] = impact_analysis
                                        except Exception as e:
                                            st.error(f"Error performing impact analysis: {e}")
                                            st.session_state[impact_key] = {'error': str(e)}
                                
                                # Create dedicated results column/container
                                if impact_key in st.session_state and st.session_state[impact_key] is not None:
                                    # Results container with border/styling
                                    st.markdown("---")
                                    st.markdown("### 📊 Analysis Results")
                                    
                                    impact_analysis = st.session_state[impact_key]
                                    
                                    # Clear button
                                    with col_btn2:
                                        if st.button("Clear Results", key=f"clear_{impact_key}"):
                                            st.session_state[impact_key] = None
                                            st.rerun()
                                    
                                    # Display results
                                    if 'error' not in impact_analysis:
                                        analyses = impact_analysis.get('impact_analysis', {}).get('analyses', [])
                                        summary = impact_analysis.get('impact_analysis', {}).get('summary', {})
                                        
                                        if analyses and len(analyses) > 0:
                                            # Display summary metrics
                                            if summary:
                                                col1, col2, col3, col4 = st.columns(4)
                                                with col1:
                                                    st.metric("Analyses Performed", summary.get('total_analyses', 0))
                                                with col2:
                                                    st.metric("Increased", summary.get('increased_violations', 0), 
                                                             delta="Violations increased", delta_color="inverse")
                                                with col3:
                                                    st.metric("Reduced", summary.get('reduced_violations', 0),
                                                             delta="Violations reduced", delta_color="normal")
                                                with col4:
                                                    st.metric("Avg Change", f"{summary.get('avg_rate_change_pct', 0):.1f}%")
                                            
                                            # Display individual analyses
                                            for idx, analysis in enumerate(analyses):
                                                impact = analysis.get('impact', {})
                                                analysis_type = analysis.get('analysis_type', 'violation')
                                                
                                                with st.expander(f"Analysis {idx + 1}: {analysis_type.replace('_', ' ').title()}", expanded=idx == 0):
                                                    col1, col2 = st.columns(2)
                                                    
                                                    with col1:
                                                        st.markdown("**Before Period**")
                                                        before = analysis.get('before_period', {})
                                                        st.write(f"- Duration: {before.get('days', 0)} days")
                                                        st.write(f"- Violations: {before.get('violation_count', 0)}")
                                                        st.write(f"- Rate: {before.get('rate_per_year', 0):.2f} per year")
                                                    
                                                    with col2:
                                                        st.markdown("**After Period**")
                                                        after = analysis.get('after_period', {})
                                                        st.write(f"- Duration: {after.get('days', 0)} days")
                                                        st.write(f"- Violations: {after.get('violation_count', 0)}")
                                                        st.write(f"- Rate: {after.get('rate_per_year', 0):.2f} per year")
                                                    
                                                    st.markdown("---")
                                                    
                                                    impact_type = impact.get('type', 'Unknown')
                                                    rate_change = impact.get('rate_change_pct', 0)
                                                    strength = impact.get('strength', 'Unknown')
                                                    significant = impact.get('statistically_significant', False)
                                                    p_value = impact.get('p_value', 1.0)
                                                    
                                                    # Impact indicator
                                                    if impact_type == "Increased":
                                                        st.error(f"🔴 **Impact: {impact_type}** ({strength})")
                                                        st.write(f"Violation rate increased by {abs(rate_change):.1f}%")
                                                    elif impact_type == "Reduced":
                                                        st.success(f"🟢 **Impact: {impact_type}** ({strength})")
                                                        st.write(f"Violation rate reduced by {abs(rate_change):.1f}%")
                                                    else:
                                                        st.info(f"⚪ **Impact: {impact_type}**")
                                                    
                                                    # Statistical significance
                                                    if significant:
                                                        st.success(f"✓ Statistically significant (p = {p_value:.4f})")
                                                    else:
                                                        st.warning(f"⚠ Not statistically significant (p = {p_value:.4f})")
                                                    
                                                    # Violation date
                                                    if analysis.get('violation_date'):
                                                        st.write(f"**Analyzed violation date:** {analysis['violation_date']}")
                                                    
                                                    # Visualizations
                                                    st.markdown("**Visualizations:**")
                                                    
                                                    # Rate comparison chart
                                                    try:
                                                        rate_fig = plot_rate_comparison(
                                                            analysis.get('before_period', {}),
                                                            analysis.get('after_period', {}),
                                                            analysis.get('impact', {})
                                                        )
                                                        st.plotly_chart(rate_fig, use_container_width=True)
                                                    except Exception as e:
                                                        st.warning(f"Could not generate rate comparison chart: {e}")
                                                    
                                                    # Timeline visualization (if we have violation data)
                                                    if results is not None and not results.empty:
                                                        try:
                                                            timeline_fig = plot_violation_timeline(
                                                                results,
                                                                analysis.get('violation_date', ''),
                                                                analysis.get('before_period', {}),
                                                                analysis.get('after_period', {})
                                                            )
                                                            st.plotly_chart(timeline_fig, use_container_width=True)
                                                        except Exception as e:
                                                            pass  # Silently skip if timeline can't be generated
                                            
                                            # Summary visualization
                                            if len(analyses) > 1:
                                                st.markdown("---")
                                                st.subheader("Impact Analysis Summary")
                                                try:
                                                    summary_fig = plot_impact_summary(analyses)
                                                    st.plotly_chart(summary_fig, use_container_width=True)
                                                except Exception as e:
                                                    st.warning(f"Could not generate summary visualization: {e}")
                                            else:
                                                st.info("⚠️ Unable to perform impact analysis. Company may have too few violations or insufficient time period data.")
                                                if 'total_violations' in impact_analysis:
                                                    st.write(f"Found {impact_analysis.get('total_violations', 0)} violations, but analysis requires at least 3 violations with valid dates.")
                                    else:
                                        error_msg = impact_analysis.get('error', 'Unknown error')
                                        st.error(f"❌ Error: {error_msg}")
                                        if 'total_violations' in impact_analysis:
                                            st.info(f"Found {impact_analysis.get('total_violations', 0)} violations for this company.")
                                
                                # Download results
                                st.markdown("---")
                                csv = results.to_csv(index=False)
                                st.download_button(
                                    "Download All Results (CSV)",
                                    csv,
                                    f"{company_search.replace(' ', '_')}_compliance_results.csv",
                                    "text/csv",
                                    key="download_company_results"
                                )
                            else:
                                st.info("No violations found in the selected agencies.")
                        else:
                            st.warning(f"No violations found for '{company_search}' in the selected agencies.")
                            st.info("💡 Try different variations of the company name or check spelling.")
                
                # Show companies with cross-agency violations
                st.markdown("---")
                st.subheader("Companies with Violations Across Multiple Agencies")
                st.markdown("Discover companies that have compliance issues with multiple regulatory agencies.")
                
                if st.button("Find Cross-Agency Violations", type="secondary"):
                    with st.spinner("Analyzing companies with multi-agency violations..."):
                        cross_agency_df = comp_analyzer.get_companies_with_cross_agency_violations(
                            min_violations=1,
                            agencies=selected_agencies if selected_agencies else None
                        )
                        
                        if not cross_agency_df.empty:
                            st.success(f"Found {len(cross_agency_df)} companies with violations across multiple agencies")
                            st.dataframe(
                                cross_agency_df.sort_values(
                                    by=[col for col in cross_agency_df.columns if col != "company_name_normalized"],
                                    ascending=False
                                ).head(50),
                                use_container_width=True
                            )
                            
                            csv = cross_agency_df.to_csv(index=False)
                            st.download_button(
                                "Download Cross-Agency Companies (CSV)",
                                csv,
                                "cross_agency_violations.csv",
                                "text/csv"
                            )
                        else:
                            st.info("No companies found with violations across multiple agencies (or insufficient data).")
        
        except Exception as e:
            st.error(f"Error loading compliance analyzer: {e}")
            st.info("Make sure OSHA data is available by running: `python src/data_loader.py`")
    
    # Footer
    st.markdown("---")
    st.markdown(
        "*Data source: [U.S. Department of Labor](https://enforcedata.dol.gov/views/data_catalogs.php) | "
        "Built by [Sage Hart](https://linkedin.com/in/shporter)*"
    )


if __name__ == "__main__":
    main()
