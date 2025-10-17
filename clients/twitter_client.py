"""
Twitter API client for searching basketball highlights
"""
import logging
from typing import List, Dict, Any, Optional, cast
from datetime import datetime
import requests
from bs4 import BeautifulSoup  # type: ignore

from exceptions import APIError, APIAuthenticationError, RateLimitError, APINotAvailableError

logger = logging.getLogger(__name__)

class TwitterClient:
    """
    Client for searching Twitter API for basketball highlights.
    Includes fallback scraping capability.
    """

    def __init__(self, api_key: str, api_secret: str, access_token: str, access_token_secret: str) -> None:
        """
        Initialize Twitter client.

        Args:
            api_key: Twitter API key
            api_secret: Twitter API secret
            access_token: Twitter access token
            access_token_secret: Twitter access token secret

        Raises:
            APINotAvailableError: If tweepy is not available
        """
        try:
            import tweepy  # type: ignore
        except ImportError:
            raise APINotAvailableError("tweepy is required for Twitter functionality")

        self.api_key = api_key
        self.api_secret = api_secret
        self.access_token = access_token
        self.access_token_secret = access_token_secret

        # Initialize client
        auth = tweepy.OAuthHandler(api_key, api_secret)
        auth.set_access_token(access_token, access_token_secret)  # type: ignore
        self.api: Any = tweepy.API(auth, wait_on_rate_limit=True)  # type: ignore

        # Test credentials on initialization
        self.test_credentials()

    def test_credentials(self) -> None:
        """
        Test Twitter credentials by verifying authentication.

        Raises:
            APIAuthenticationError: If authentication fails
        """
        try:
            self.api.verify_credentials()
            logger.debug("Twitter authentication successful")
        except Exception as e:
            logger.error(f"Twitter authentication failed: {e}")
            raise APIAuthenticationError("Twitter authentication failed") from e

    def search(self, query: str, max_results: int = 5, use_fallback: bool = True) -> List[Dict[str, Any]]:
        """
        Search for basketball highlights on Twitter.

        Args:
            query: Search query string
            max_results: Maximum number of results to return
            use_fallback: Whether to use scraping fallback if API fails

        Returns:
            List of result dictionaries with platform, title, url, upload_date, score

        Raises:
            RateLimitError: If rate limit is exceeded
            APIError: For other API errors
            APINotAvailableError: If neither API nor fallback is available
        """
        try:
            return self._search_api(query, max_results)
        except (APIError, APIAuthenticationError) as e:
            if not use_fallback:
                raise
            logger.warning(f"Twitter API search failed, trying fallback: {e}")
            try:
                return self._scrape_fallback(query, max_results)
            except Exception as fallback_error:
                logger.error(f"Fallback scraping also failed: {fallback_error}")
                raise APINotAvailableError("Twitter search unavailable: both API and fallback failed") from fallback_error
        except Exception as e:
            logger.error(f"Unexpected error in Twitter search: {e}")
            raise APIError("Unexpected error during Twitter search") from e

    def _search_api(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """
        Search using Twitter API v1.1
        """
        results: List[Dict[str, Any]] = []

        search_query = f"{query} basketball highlights filter:videos lang:en"
        try:
            tweets = cast(List[Any], self.api.search_tweets(
                q=search_query,
                count=max_results * 2,  # Request more to account for filtering
                tweet_mode="extended",
                result_type="recent",
            ))
        except Exception as e:
            if 'Rate limit exceeded' in str(e):
                raise RateLimitError("Twitter rate limit exceeded")
            elif 'access level' in str(e).lower():
                raise APIAuthenticationError("Access level does not allow this operation")
            else:
                raise APIError(f"Twitter API error: {e}") from e

        for tweet in tweets:
            # Extract media URLs
            media = cast(List[Dict[str, Any]], getattr(tweet, "entities", {}).get("media", []))
            urls = cast(List[Dict[str, Any]], getattr(tweet, "entities", {}).get("urls", []))

            # Get the best available URL
            video_url: Optional[str] = None
            if media and len(media) > 0:
                video_url = cast(str, media[0].get("expanded_url"))
            elif urls and len(urls) > 0:
                video_url = cast(str, urls[0].get("expanded_url"))

            if video_url:
                results.append(
                    {
                        "platform": "Twitter",
                        "title": getattr(tweet, "full_text", "")[:100] + "...",
                        "url": video_url,
                        "upload_date": getattr(getattr(tweet, "created_at", None), "isoformat", lambda: "")(),
                        "score": getattr(tweet, "favorite_count", 0)
                        + getattr(tweet, "retweet_count", 0),
                    }
                )

            if len(results) >= max_results:
                break

        return results

    def _scrape_fallback(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """
        Fallback method using web scraping when API is unavailable
        """
        results: List[Dict[str, Any]] = []

        try:
            search_url = f"https://twitter.com/search?q={query} basketball highlights filter:videos lang:en&src=typed_query"
            response = requests.get(search_url, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            # Debug: save response for analysis if needed
            # with open("twitter_search_response.html", "w", encoding="utf-8") as f:
            #     f.write(soup.prettify())

            tweets = soup.find_all("div", {"data-testid": "tweet"})
            for tweet in tweets[:max_results]:
                text_div = tweet.find("div", {"lang": "en"})
                text = text_div.get_text() if text_div else ""
                link_tag = tweet.find("a", {"role": "link"})
                video_url = (
                    f"https://twitter.com{link_tag['href']}"
                    if link_tag and link_tag.has_attr("href") else None
                )

                # Check if the tweet contains a video
                media = tweet.find("div", {"class": "AdaptiveMedia-video"})
                if media and video_url:
                    results.append(
                        {
                            "platform": "Twitter",
                            "title": text[:100] + "...",  # Truncate long tweets
                            "url": video_url,
                            "upload_date": datetime.now().isoformat(),  # Use current date as placeholder
                            "score": 0,  # No engagement data available
                        }
                    )

                if len(results) >= max_results:
                    break

        except requests.RequestException as e:
            raise APIError("Twitter scraping failed due to network error") from e
        except Exception as e:
            raise APIError("Twitter scraping failed") from e

        return results
