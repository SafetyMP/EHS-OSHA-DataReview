#!/usr/bin/env python3
"""
Validate environment variables for production deployment.
Checks that all required variables are set and have valid values.
"""

import os
import sys
from pathlib import Path
from typing import List, Tuple

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

REQUIRED_VARS = {
    'production': [
        'DATABASE_URL',
        'SECRET_KEY',
        'LOG_LEVEL',
    ],
    'development': [
        # Development has fewer requirements
    ],
}

OPTIONAL_VARS = [
    'DATA_DIR',
    'REDIS_URL',
    'OPENAI_API_KEY',
    'CACHE_TTL',
    'CACHE_MAX_SIZE',
    'DATABASE_POOL_SIZE',
    'DATABASE_MAX_OVERFLOW',
    'API_RATE_LIMIT',
    'API_MAX_QUERY_ROWS',
    'FUZZY_THRESHOLD',
    'ENABLE_CACHING',
    'ENABLE_CONNECTION_POOLING',
    'STREAMLIT_SERVER_PORT',
    'STREAMLIT_SERVER_ADDRESS',
    'CORS_ORIGINS',
    'ENVIRONMENT',
    'DEBUG',
]


def validate_database_url(url: str) -> Tuple[bool, str]:
    """Validate database URL format."""
    if not url:
        return False, "Database URL is empty"
    
    valid_schemes = ['sqlite', 'postgresql', 'mysql', 'postgresql+psycopg2']
    scheme = url.split('://')[0] if '://' in url else None
    
    if scheme not in valid_schemes:
        return False, f"Invalid database scheme: {scheme}. Must be one of {valid_schemes}"
    
    return True, "Valid"


def validate_secret_key(key: str) -> Tuple[bool, str]:
    """Validate secret key strength."""
    if not key:
        return False, "Secret key is empty"
    
    if len(key) < 32:
        return False, f"Secret key too short ({len(key)} chars). Minimum 32 characters required."
    
    if key == "CHANGE_THIS_TO_A_RANDOM_SECRET_KEY":
        return False, "Secret key is still using the default placeholder value"
    
    return True, "Valid"


def validate_log_level(level: str) -> Tuple[bool, str]:
    """Validate log level."""
    valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
    if level.upper() not in valid_levels:
        return False, f"Invalid log level: {level}. Must be one of {valid_levels}"
    return True, "Valid"


def validate_port(port_str: str) -> Tuple[bool, str]:
    """Validate port number."""
    try:
        port = int(port_str)
        if port < 1 or port > 65535:
            return False, f"Port {port} out of range (1-65535)"
        return True, "Valid"
    except ValueError:
        return False, f"Invalid port number: {port_str}"


VALIDATORS = {
    'DATABASE_URL': validate_database_url,
    'SECRET_KEY': validate_secret_key,
    'LOG_LEVEL': validate_log_level,
    'STREAMLIT_SERVER_PORT': validate_port,
}


def check_environment(environment: str = None) -> Tuple[bool, List[str]]:
    """
    Check environment variables.
    
    Args:
        environment: 'production' or 'development'. If None, detects from ENVIRONMENT var.
    
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    if environment is None:
        environment = os.getenv('ENVIRONMENT', 'development').lower()
    
    errors = []
    warnings = []
    
    # Check required variables
    required = REQUIRED_VARS.get(environment, [])
    for var in required:
        value = os.getenv(var)
        if not value:
            errors.append(f"Required environment variable {var} is not set")
        else:
            # Run validator if available
            if var in VALIDATORS:
                is_valid, message = VALIDATORS[var](value)
                if not is_valid:
                    errors.append(f"{var}: {message}")
    
    # Check optional variables and validate if set
    for var in OPTIONAL_VARS:
        value = os.getenv(var)
        if value and var in VALIDATORS:
            is_valid, message = VALIDATORS[var](value)
            if not is_valid:
                warnings.append(f"{var}: {message}")
    
    # Production-specific checks
    if environment == 'production':
        if os.getenv('DEBUG', 'false').lower() == 'true':
            warnings.append("DEBUG is enabled in production. This is not recommended.")
        
        if not os.getenv('CORS_ORIGINS'):
            warnings.append("CORS_ORIGINS not set. API will allow all origins (security risk).")
        
        db_url = os.getenv('DATABASE_URL', '')
        if db_url.startswith('sqlite'):
            warnings.append("Using SQLite in production. Consider PostgreSQL or MySQL for better performance.")
    
    return len(errors) == 0, errors + warnings


def main():
    """Main validation function."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Validate environment variables')
    parser.add_argument(
        '--environment',
        choices=['production', 'development'],
        default=None,
        help='Environment to validate for (default: detect from ENVIRONMENT var)'
    )
    parser.add_argument(
        '--load-env',
        type=str,
        help='Load environment variables from .env file'
    )
    
    args = parser.parse_args()
    
    # Load .env file if specified
    if args.load_env:
        from dotenv import load_dotenv
        env_file = Path(args.load_env)
        if env_file.exists():
            load_dotenv(env_file)
            print(f"Loaded environment from {env_file}")
        else:
            print(f"Warning: {env_file} not found")
    
    # Check environment
    is_valid, messages = check_environment(args.environment)
    
    # Print results
    if messages:
        for msg in messages:
            if 'Required' in msg or 'too short' in msg or 'placeholder' in msg:
                print(f"❌ ERROR: {msg}")
            else:
                print(f"⚠️  WARNING: {msg}")
    
    if is_valid:
        print("\n✅ Environment variables are valid!")
        sys.exit(0)
    else:
        print("\n❌ Environment validation failed!")
        sys.exit(1)


if __name__ == '__main__':
    main()

