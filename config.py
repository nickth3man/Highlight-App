"""
Configuration management for Highlight App
Handles loading and validation of environment variables and API keys.
"""
import os
import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

@dataclass
class APIKeys:
    """Container for API keys loaded from environment variables"""
    twitter_api_key: Optional[str]
    twitter_api_secret: Optional[str]
    twitter_bearer_token: Optional[str]
    twitter_access_token: Optional[str]
    twitter_access_token_secret: Optional[str]
    youtube_key: Optional[str]

def load_api_keys(env_path: Optional[str] = None) -> APIKeys:
    """
    Load and validate API keys from environment variables.

    Args:
        env_path: Optional path to .env file. If provided, loads variables from this file.

    Returns:
        APIKeys: Dataclass containing all API keys

    Raises:
        FileNotFoundError: If env_path is provided but file doesn't exist
        RuntimeError: If .env file fails to load
        ValueError: If required environment variables are missing
    """
    if env_path:
        try:
            from dotenv import load_dotenv
            if not os.path.exists(env_path):
                raise FileNotFoundError(f".env file not found at {env_path}")

            # Load environment variables
            success = load_dotenv(env_path, override=True)
            if not success:
                raise RuntimeError("Failed to load .env file")

            logger.debug("Environment variables loaded from .env file")

        except ImportError:
            logger.error("python-dotenv is required. Install with: pip install python-dotenv")
            raise RuntimeError("python-dotenv is required. See README for setup instructions.")

    # Load required environment variables
    keys = APIKeys(
        twitter_api_key=os.getenv("TWITTER_API_KEY"),
        twitter_api_secret=os.getenv("TWITTER_API_SECRET"),
        twitter_bearer_token=os.getenv("TWITTER_BEARER_TOKEN"),
        twitter_access_token=os.getenv("TWITTER_ACCESS_TOKEN"),
        twitter_access_token_secret=os.getenv("TWITTER_ACCESS_TOKEN_SECRET"),
        youtube_key=os.getenv("YOUTUBE_API_KEY"),
    )

    # Validation
    missing_vars = [
        var for var, value in [
            ("TWITTER_API_KEY", keys.twitter_api_key),
            ("TWITTER_API_SECRET", keys.twitter_api_secret),
            ("TWITTER_BEARER_TOKEN", keys.twitter_bearer_token),
            ("TWITTER_ACCESS_TOKEN", keys.twitter_access_token),
            ("TWITTER_ACCESS_TOKEN_SECRET", keys.twitter_access_token_secret),
            ("YOUTUBE_API_KEY", keys.youtube_key),
        ]
        if not value
    ]

    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

    # Log masked keys for debugging
    logger.debug("API keys loaded successfully")
    masked_youtube = "*" * 8 + keys.youtube_key[-4:] if keys.youtube_key and len(keys.youtube_key) > 4 else "None"
    masked_twitter = "*" * 8 + keys.twitter_api_key[-4:] if keys.twitter_api_key and len(keys.twitter_api_key) > 4 else "None"
    logger.debug(f"YouTube API Key: {masked_youtube}")
    logger.debug(f"Twitter API Key: {masked_twitter}")

    # Additional warnings for invalid-looking keys (development defaults starting with "your_")
    if keys.youtube_key and keys.youtube_key.startswith("your_"):
        logger.warning("YouTube API key appears to be a placeholder (starts with 'your_')")
    if keys.twitter_api_key and keys.twitter_api_key.startswith("your_"):
        logger.warning("Twitter API key appears to be a placeholder (starts with 'your_')")

    return keys
