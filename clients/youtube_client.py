"""
YouTube API client for searching basketball highlights
"""
import logging
from typing import List, Dict, Any

from exceptions import APIError, APIAuthenticationError, APINotAvailableError

logger = logging.getLogger(__name__)

class YouTubeClient:
    """
    Client for searching YouTube API for basketball highlights
    """

    def __init__(self, api_key: str) -> None:
        """
        Initialize YouTube client.

        Args:
            api_key: YouTube API key

        Raises:
            APINotAvailableError: If googleapiclient is not available or API key is invalid
        """
        try:
            from googleapiclient.discovery import build  # type: ignore
        except ImportError:
            raise APINotAvailableError("google-api-python-client is required for YouTube functionality")

        self.api_key = api_key

        try:
            self.api: Any = build(
                "youtube",
                "v3",
                developerKey=api_key,
                cache_discovery=False,
            )  # type: ignore
        except Exception as e:
            raise APINotAvailableError(f"Failed to initialize YouTube client: {e}") from e

        # Test API key on initialization
        self.test_api_key()

    def test_api_key(self) -> None:
        """
        Test YouTube API key by performing a simple search.

        Raises:
            APIAuthenticationError: If API key is invalid
            APIError: For other API errors
        """
        try:
            response = self.api.search().list(  # type: ignore
                part="snippet",
                q="test",
                maxResults=1,
            ).execute()  # type: ignore
            logger.debug("YouTube API test successful")
        except Exception as e:
            error_str = str(e).lower()
            if "api key" in error_str or "keyinvalid" in error_str:
                raise APIAuthenticationError("YouTube API key is invalid") from e
            elif "quota" in error_str:
                api_key_preview = self.api_key[:10] + "..." if len(self.api_key) > 10 else self.api_key
                logger.warning(f"YouTube API key invalid or missing. Key starts with: {api_key_preview}")
                raise APIAuthenticationError("YouTube API key invalid or quota exceeded") from e
            else:
                logger.error(f"YouTube API test failed: {e}")
                raise APIError(f"YouTube API error: {e}") from e

    def search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """
        Search for basketball highlights on YouTube.

        Args:
            query: Search query string
            max_results: Maximum number of results to return

        Returns:
            List of result dictionaries with platform, title, url, upload_date, score, etc.

        Raises:
            APIAuthenticationError: If API key issues
            APIError: For other API errors
        """
        results: List[Dict[str, Any]] = []

        if not self.api:
            raise APINotAvailableError("YouTube client not initialized")

        try:
            # Search for videos
            search_response: Any = self.api.search().list(  # type: ignore
                q=f"{query} basketball highlights",
                part="snippet",
                type="video",
                maxResults=max_results,
                videoDefinition="high",  # Only HD videos
                order="date",  # Sort by date for recency
                relevanceLanguage="en",  # English results
                safeSearch="none",  # Allow all content
            ).execute()  # type: ignore

            # Get video IDs for detailed info
            video_ids: List[str] = [
                item["id"]["videoId"]
                for item in search_response.get("items", [])
                if "id" in item and "videoId" in item["id"]
            ]

            if not video_ids:
                logger.debug("No videos found in YouTube search")
                return results

            # Get detailed video information (including statistics)
            videos_response: Any = self.api.videos().list(  # type: ignore
                part="snippet,statistics",
                id=",".join(video_ids)
            ).execute()  # type: ignore

            # Create results
            for item in videos_response.get("items", []):
                stats = item.get("statistics", {})
                snippet = item.get("snippet", {})

                results.append(
                    {
                        "platform": "YouTube",
                        "title": snippet.get("title", ""),
                        "url": f"https://www.youtube.com/watch?v={item.get('id', '')}",
                        "upload_date": snippet.get("publishedAt", ""),
                        "score": int(stats.get("viewCount", 0)),  # Use view count as score
                        "description": snippet.get("description", ""),
                        "views": stats.get("viewCount", 0),
                        "likes": stats.get("likeCount", 0),
                    }
                )

        except Exception as e:
            error_str = str(e).lower()
            if "api key" in error_str or "keyinvalid" in error_str or "403" in error_str:
                raise APIAuthenticationError("YouTube API authentication failed") from e
            elif "quota" in error_str:
                logger.warning("YouTube API quota exceeded")
                raise APIAuthenticationError("YouTube API quota exceeded") from e
            else:
                logger.error(f"YouTube API search error: {e}")
                raise APIError(f"YouTube search failed: {e}") from e

        return results
