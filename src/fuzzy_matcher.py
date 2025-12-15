"""
Fuzzy Company Name Matching
Advanced company name matching using fuzzy string matching algorithms.
"""

from typing import List, Tuple, Optional
import pandas as pd
from rapidfuzz import fuzz, process
import re


class CompanyNameMatcher:
    """Advanced company name matcher with fuzzy matching capabilities."""
    
    def __init__(self, threshold: int = 75):
        """
        Initialize matcher.
        
        Args:
            threshold: Minimum similarity score (0-100) for matches
        """
        self.threshold = threshold
    
    def normalize_company_name(self, name: str) -> str:
        """
        Normalize company name for matching.
        
        Removes common suffixes, punctuation, and normalizes spacing.
        """
        if pd.isna(name) or not name:
            return ""
        
        name = str(name).upper().strip()
        
        # Remove common suffixes and legal entities
        suffixes = [
            " INC", " LLC", " CORP", " CORPORATION", " LP", " LTD", 
            " COMPANY", " CO", " L.L.C.", " INC.", " CORP.", " CO.",
            " PLC", " PLLC", " LLP", " PA", " PC", " P.C.",
            " LLC.", " INCORPORATED", " LIMITED", " ASSOCIATES",
            " ASSOCIATION", " GROUP", " HOLDINGS", " HOLDING"
        ]
        for suffix in suffixes:
            if name.endswith(suffix):
                name = name[:-len(suffix)].strip()
        
        # Remove punctuation and special characters
        name = re.sub(r'[^\w\s]', ' ', name)
        
        # Normalize whitespace
        name = re.sub(r'\s+', ' ', name).strip()
        
        # Remove common words that don't help matching
        common_words = ["THE", "A", "AN"]
        words = name.split()
        words = [w for w in words if w not in common_words]
        name = " ".join(words)
        
        return name
    
    def calculate_similarity(self, name1: str, name2: str) -> float:
        """
        Calculate similarity score between two company names.
        
        Uses multiple fuzzy matching algorithms and returns the best score.
        
        Returns:
            Similarity score (0-100)
        """
        norm1 = self.normalize_company_name(name1)
        norm2 = self.normalize_company_name(name2)
        
        if not norm1 or not norm2:
            return 0.0
        
        # Use multiple scoring methods and take the best
        scores = [
            fuzz.ratio(norm1, norm2),  # Simple ratio
            fuzz.partial_ratio(norm1, norm2),  # Partial matching
            fuzz.token_sort_ratio(norm1, norm2),  # Token-based (order independent)
            fuzz.token_set_ratio(norm1, norm2),  # Token set (ignores duplicates)
        ]
        
        # Weighted average favoring token-based methods
        weighted_score = (
            scores[0] * 0.2 +  # Simple ratio
            scores[1] * 0.2 +  # Partial ratio
            scores[2] * 0.3 +  # Token sort (best for abbreviations)
            scores[3] * 0.3    # Token set (best for extra words)
        )
        
        return weighted_score
    
    def find_matches(
        self, 
        search_name: str, 
        candidate_names: List[str],
        limit: int = 10,
        threshold: Optional[int] = None
    ) -> List[Tuple[str, float]]:
        """
        Find best matching company names from a list of candidates.
        
        Args:
            search_name: Company name to search for
            candidate_names: List of candidate company names
            limit: Maximum number of matches to return
            threshold: Minimum similarity score (uses self.threshold if None)
        
        Returns:
            List of tuples: (matched_name, similarity_score) sorted by score descending
        """
        threshold = threshold or self.threshold
        normalized_search = self.normalize_company_name(search_name)
        
        if not normalized_search:
            return []
        
        # Use rapidfuzz.process for efficient matching
        matches = process.extract(
            normalized_search,
            candidate_names,
            scorer=fuzz.token_sort_ratio,  # Best for company names
            limit=limit
        )
        
        # Filter by threshold and calculate weighted scores
        results = []
        for candidate, score, _ in matches:
            if score >= threshold:
                # Calculate more sophisticated score
                final_score = self.calculate_similarity(search_name, candidate)
                if final_score >= threshold:
                    results.append((candidate, final_score))
        
        # Sort by score descending
        results.sort(key=lambda x: x[1], reverse=True)
        
        return results[:limit]
    
    def match_dataframe(
        self,
        search_name: str,
        df: pd.DataFrame,
        company_column: str,
        threshold: Optional[int] = None,
        limit: int = 100
    ) -> pd.DataFrame:
        """
        Find matching companies in a DataFrame.
        
        Args:
            search_name: Company name to search for
            df: DataFrame containing company data
            company_column: Name of column containing company names
            threshold: Minimum similarity score
            limit: Maximum number of matches
        
        Returns:
            DataFrame with matched companies and similarity scores
        """
        if df.empty or company_column not in df.columns:
            return pd.DataFrame()
        
        threshold = threshold or self.threshold
        unique_names = df[company_column].dropna().unique().tolist()
        
        if not unique_names:
            return pd.DataFrame()
        
        # Find matches
        matches = self.find_matches(search_name, unique_names, limit=limit * 2, threshold=threshold)
        
        if not matches:
            return pd.DataFrame()
        
        # Create match lookup
        match_dict = {name: score for name, score in matches}
        
        # Filter dataframe to matched companies
        matched_df = df[df[company_column].isin(match_dict.keys())].copy()
        
        # Add similarity scores
        matched_df['similarity_score'] = matched_df[company_column].map(match_dict)
        
        # Sort by similarity score
        matched_df = matched_df.sort_values('similarity_score', ascending=False)
        
        return matched_df.head(limit)
    
    def group_similar_companies(
        self,
        company_names: List[str],
        threshold: int = 85
    ) -> List[List[str]]:
        """
        Group similar company names together.
        
        Useful for identifying duplicate/variant company names in data.
        
        Args:
            company_names: List of company names to group
            threshold: Minimum similarity for grouping
        
        Returns:
            List of groups, where each group contains similar company names
        """
        normalized_names = [(name, self.normalize_company_name(name)) for name in company_names]
        groups = []
        used = set()
        
        for i, (name, norm1) in enumerate(normalized_names):
            if i in used:
                continue
            
            group = [name]
            used.add(i)
            
            for j, (other_name, norm2) in enumerate(normalized_names[i+1:], start=i+1):
                if j in used:
                    continue
                
                score = self.calculate_similarity(norm1, norm2)
                if score >= threshold:
                    group.append(other_name)
                    used.add(j)
            
            if len(group) > 1:  # Only return groups with multiple members
                groups.append(group)
        
        return groups

