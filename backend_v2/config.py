# -*- coding: utf-8 -*-
import os
import logging
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load .env file
load_dotenv(override=False)

# Required Config
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.1-pro-preview")

# Tunable Settings
GEMINI_TIMEOUT_SECONDS: int = int(os.getenv("GEMINI_TIMEOUT_SECONDS", "25"))
GEMINI_MAX_RETRIES: int = int(os.getenv("GEMINI_MAX_RETRIES", "2"))
SKIP_API_VALIDATION: bool = os.getenv("AUTOMENTOR_SKIP_API_VALIDATION", "").lower() in {
    "1", "true", "yes", "on"
}

def validate_env() -> None:
    """Check for required variables at startup."""
    errors = []
    if not GEMINI_API_KEY:
        errors.append("GEMINI_API_KEY is missing from .env")
    
    if GEMINI_TIMEOUT_SECONDS < 5 or GEMINI_TIMEOUT_SECONDS > 120:
        errors.append(f"GEMINI_TIMEOUT_SECONDS ({GEMINI_TIMEOUT_SECONDS}) is out of range [5, 120]")

    if errors:
        error_msg = "\n - ".join(errors)
        raise EnvironmentError(f"\n[AutoMentor] Configuration Errors:\n - {error_msg}")
    
    logger.info(f"[Config] Validation passed. Model: {GEMINI_MODEL}")
    if SKIP_API_VALIDATION:
        logger.info("[Config] Skipping live API validation due to AUTOMENTOR_SKIP_API_VALIDATION")
        return
    validate_api_key()  # Test that API key actually works


# =============================================================================
# KEY VALIDATION: Test API connectivity at startup
# =============================================================================

def validate_api_key() -> None:
    """
    Verify GEMINI_API_KEY is valid and GEMINI_MODEL is available.
    Called once at app startup. Fails fast if key or model is broken.
    """
    import google.genai as genai
    
    client = genai.Client(api_key=GEMINI_API_KEY)
    
    try:
        # List available models to confirm API key works
        models = client.models.list()
        model_names = [m.name for m in models]
        
        # Check if our target model exists
        model_path = f"models/{GEMINI_MODEL.replace('models/', '')}"
        if not any(model_path in name for name in model_names):
            raise ValueError(f"Model '{GEMINI_MODEL}' not found in available models")
        
        logger.info(f"✓ [Config] API key validated | Model '{GEMINI_MODEL}' available ✓")
    
    except Exception as e:
        raise EnvironmentError(
            f"\n[AutoMentor] API Key Validation Failed:\n"
            f"  - Key: {GEMINI_API_KEY[:10]}...***\n"
            f"  - Model: {GEMINI_MODEL}\n"
            f"  - Error: {e}"
        )
