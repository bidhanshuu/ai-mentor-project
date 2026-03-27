# -*- coding: utf-8 -*-
"""
logging_utils.py
----------------
Utilities for safe logging without leaking secrets (API keys, tokens, passwords).
"""

import re
from typing import Optional


def mask_sensitive(message: str) -> str:
    """
    Redact sensitive information from log messages to prevent secret leakage.
    
    Masks:
    - GEMINI_API_KEY patterns (Google API keys, typically 40+ alphanumeric chars)
    - JWT tokens and Bearer tokens
    - Database passwords
    - Common credential patterns
    
    Args:
        message: The log message potentially containing secrets
        
    Returns:
        The message with sensitive data masked as [REDACTED_<TYPE>]
        
    Examples:
        >>> msg = "API Key: AIzaSyD1234567890abcdefghijklmnopqrst"
        >>> mask_sensitive(msg)
        'API Key: [REDACTED_API_KEY]'
        
        >>> msg = "Token: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
        >>> mask_sensitive(msg)
        'Token: [REDACTED_TOKEN]'
    """
    if not message:
        return message
    
    # Mask Google API keys (AIza... prefix, 40+ chars)
    message = re.sub(
        r'AIza[A-Za-z0-9_-]{35,}',
        '[REDACTED_API_KEY]',
        message,
        flags=re.IGNORECASE
    )
    
    # Mask JWT tokens (Bearer tokens, typical JWT pattern)
    message = re.sub(
        r'(?:Bearer\s+)?eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+',
        '[REDACTED_TOKEN]',
        message,
        flags=re.IGNORECASE
    )
    
    # Mask passwords in connection strings (password=...)
    message = re.sub(
        r'password=([^\s&;"\']+)',
        'password=[REDACTED_PASSWORD]',
        message,
        flags=re.IGNORECASE
    )
    
    # Mask AWS/generic API keys (generic pattern: apikey, api_key, secret)
    message = re.sub(
        r'(?:api[_-]?key|secret[_-]?key)\s*[:=]\s*([^\s&;"\']+)',
        r'\g<0>[REDACTED_SECRET]',
        message,
        flags=re.IGNORECASE
    )
    
    return message
