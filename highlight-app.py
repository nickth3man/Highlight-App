import tkinter as tk
from tkinter import ttk, messagebox
import threading
import webbrowser
import os
from datetime import datetime
from typing import List, Dict, Any
import requests
from bs4 import BeautifulSoup # type: ignore

# Load environment variables
try:
    from dotenv import load_dotenv
    # Get the directory containing the script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    env_path = os.path.join(script_dir, '.env')
    
    # Check if .env file exists and read its contents
    if not os.path.exists(env_path):
        raise FileNotFoundError(f".env file not found at {env_path}")
    
    # Read and display .env file contents (excluding sensitive data)
    print(f"\nReading .env file from: {env_path}")
    with open(env_path, 'r', encoding='utf-8-sig') as f:  # Use utf-8-sig to handle BOM
        env_contents = f.read()
        # Print first line to verify format
        first_line = env_contents.split('\n')[0]
        print(f"First line of .env: {first_line}")
    
    # Load environment variables
    success = load_dotenv(env_path, override=True)
    if not success:
        raise RuntimeError("Failed to load .env file")
    
    # Debug: Print actual loaded environment variables
    print("\nActual loaded environment variables:")
    youtube_key = os.environ.get('YOUTUBE_API_KEY', '')
    twitter_key = os.environ.get('TWITTER_API_KEY', '')
    print(f"YOUTUBE_API_KEY: {youtube_key[:10]}..." if youtube_key else "YOUTUBE_API_KEY: Not found")
    print(f"TWITTER_API_KEY: {twitter_key[:10]}..." if twitter_key else "TWITTER_API_KEY: Not found")
    
    # Verify that required environment variables are set
    required_vars = [
        'TWITTER_API_KEY',
        'TWITTER_API_SECRET',
        'TWITTER_BEARER_TOKEN',
        'TWITTER_ACCESS_TOKEN',
        'TWITTER_ACCESS_TOKEN_SECRET',
        'YOUTUBE_API_KEY'
    ]
    
    # Check environment variables directly
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

except ImportError:
    print("Installing python-dotenv...")
    os.system('pip install python-dotenv')
    from dotenv import load_dotenv
    load_dotenv()

# Optional imports with error handling
APIS_AVAILABLE = {
    'youtube': False,
    'twitter': False,
    'reddit': False,
    'spacy': False,
    'transformers': False
}

try:
    from googleapiclient.discovery import build
    APIS_AVAILABLE['youtube'] = True
except ImportError:
    print("YouTube API not available. Install with: pip install google-api-python-client")

try:
    import tweepy
    APIS_AVAILABLE['twitter'] = True
except ImportError:
    print("Installing tweepy...")
    os.system('pip install tweepy')
    import tweepy
    APIS_AVAILABLE['twitter'] = True

class APIKeys:
    """Manages API keys from environment variables"""
    def __init__(self):
        # Twitter credentials are now set from environment variables
        self.twitter_api_key = os.getenv('TWITTER_API_KEY')
        self.twitter_api_secret = os.getenv('TWITTER_API_SECRET')
        self.twitter_bearer_token = os.getenv('TWITTER_BEARER_TOKEN')
        self.twitter_access_token = os.getenv('TWITTER_ACCESS_TOKEN')
        self.twitter_access_token_secret = os.getenv('TWITTER_ACCESS_TOKEN_SECRET')
        
        # Other API keys (if you add them later)
        self.youtube_key = os.getenv('YOUTUBE_API_KEY')
        self.reddit_client_id = os.getenv('REDDIT_CLIENT_ID')
        self.reddit_client_secret = os.getenv('REDDIT_CLIENT_SECRET')
        self.reddit_user_agent = os.getenv('REDDIT_USER_AGENT', 'HighlightApp/1.0')

        # Debug information
        print("\nAPI Keys Debug Information:")
        print(f"YouTube API Key: {self.youtube_key[:10]}..." if self.youtube_key else "YouTube API Key: None")
        print(f"Twitter API Key: {self.twitter_api_key[:10]}..." if self.twitter_api_key else "Twitter API Key: None")
        
        # Verify keys are not empty
        if not self.youtube_key or self.youtube_key.startswith('your_'):
            print("Warning: YouTube API key is missing or invalid")
        if not self.twitter_api_key or self.twitter_api_key.startswith('your_'):
            print("Warning: Twitter API key is missing or invalid")

class HighlightSearcher:
    """Handles searching across different platforms"""
    def __init__(self):
        self.api_keys = APIKeys()
        self.clients = {}
        self.last_error = None  # Add this attribute to store the last error
        self._initialize_clients()

    def _initialize_clients(self):
        """Initialize API clients with error handling"""
        self._initialize_twitter_client()
        self._initialize_youtube_client()

    def _initialize_twitter_client(self):
        """Initialize Twitter client with error handling"""
        if APIS_AVAILABLE['twitter'] and self.api_keys.twitter_api_key:
            try:
                auth = tweepy.OAuthHandler(
                    self.api_keys.twitter_api_key,
                    self.api_keys.twitter_api_secret
                )
                auth.set_access_token(
                    self.api_keys.twitter_access_token,
                    self.api_keys.twitter_access_token_secret
                )
                self.clients['twitter'] = tweepy.API(auth, wait_on_rate_limit=True)
                self._test_twitter_credentials()
            except Exception as e:
                print(f"Failed to initialize Twitter client: {e}")
                print("Twitter functionality will be disabled")

    def _test_twitter_credentials(self):
        """Test Twitter credentials"""
        try:
            self.clients['twitter'].verify_credentials()
            print("Twitter authentication successful!")
        except tweepy.errors.Unauthorized:
            print("Twitter authentication failed - invalid credentials")
            del self.clients['twitter']

    def _initialize_youtube_client(self):
        """Initialize YouTube client with error handling"""
        if APIS_AVAILABLE['youtube']:
            print(f"Attempting YouTube initialization with key: {self.api_keys.youtube_key[:5]}...")
            try:
                self.clients['youtube'] = build(
                    'youtube', 
                    'v3',
                    developerKey=self.api_keys.youtube_key,
                    cache_discovery=False
                )
                self._test_youtube_api_key()
            except Exception as e:
                print(f"YouTube client creation failed: {str(e)}")
                if 'youtube' in self.clients:
                    del self.clients['youtube']
        else:
            print("YouTube API not available")

    def _test_youtube_api_key(self):
        """Test YouTube API key"""
        try:
            self.clients['youtube'].search().list(
                part='snippet',
                q='test',
                maxResults=1
            ).execute()
            print("YouTube API test successful!")
        except Exception as e:
            print(f"YouTube API test failed: {str(e)}")
            if "quota" in str(e).lower():
                print("YouTube API quota exceeded")
            elif "key" in str(e).lower():
                print(f"YouTube API key invalid or missing. Key starts with: {self.api_keys.youtube_key[:5]}")
            del self.clients['youtube']

    def search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Aggregate search results from all available platforms"""
        results = []
        self.last_error = None  # Reset last error before starting a new search
        
        # Twitter search with enhanced error handling
        if 'twitter' in self.clients:
            try:
                twitter_results = self._search_twitter(query, max_results)
                print(f"Found {len(twitter_results)} Twitter results")
                results.extend(twitter_results)
            except Exception as e:
                self.last_error = e
                print(f"Twitter search error: {e}")
        
        # YouTube search
        if 'youtube' in self.clients:
            try:
                youtube_results = self._search_youtube(query, max_results)
                print(f"Found {len(youtube_results)} YouTube results")
                results.extend(youtube_results)
            except Exception as e:
                self.last_error = e
                print(f"YouTube search error: {e}")
        
        # Reddit search
        if 'reddit' in self.clients:
            try:
                reddit_results = self._search_reddit(query, max_results)
                print(f"Found {len(reddit_results)} Reddit results")
                results.extend(reddit_results)
            except Exception as e:
                self.last_error = e
                print(f"Reddit search error: {e}")

        return self._sort_results(results)

    def _search_twitter(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """
        Search Twitter for basketball highlights with enhanced functionality
        """
        results = []
        try:
            # Using Twitter API v1.1 search
            search_query = f"{query} basketball highlights filter:videos lang:en"
            tweets = self.clients['twitter'].search_tweets(
                q=search_query,
                count=max_results * 2,  # Request more to account for filtering
                tweet_mode="extended",
                result_type="recent"
            )
            
            for tweet in tweets:
                # Extract media URLs
                media = tweet.entities.get('media', [])
                urls = tweet.entities.get('urls', [])
                
                # Get the best available URL
                video_url = None
                if (media):
                    video_url = media[0].get('expanded_url')
                elif (urls):
                    video_url = urls[0].get('expanded_url')
                
                if (video_url):
                    results.append({
                        "platform": "Twitter",
                        "title": tweet.full_text[:100] + "...",  # Truncate long tweets
                        "url": video_url,
                        "upload_date": tweet.created_at.isoformat(),
                        "score": tweet.favorite_count + tweet.retweet_count  # Rank by engagement
                    })
                
                if (len(results) >= max_results):
                    break
                    
        except tweepy.errors.TweepyException as e:  # Changed to TweepyException
            self.last_error = e  # Store the last error
            print(f"Twitter API error: {e}")
            if "Rate limit exceeded" in str(e):
                messagebox.showwarning("Rate Limit", 
                                     "Twitter rate limit reached. Please try again later.")
            elif "access level" in str(e):
                self.last_error = e  # Store the last error
                return []  # Return an empty list to indicate no results due to access level
        except Exception as e:
            self.last_error = e  # Store the last error
            print(f"Unexpected Twitter error: {e}")
            
        return results

    def _scrape_twitter(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """
        Scrape Twitter for basketball highlights as a fallback
        """
        results = []
        try:
            search_url = f"https://twitter.com/search?q={query} basketball highlights filter:videos lang:en&src=typed_query"
            response = requests.get(search_url)
            response.raise_for_status()  # Raise an error for bad status codes
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Log the response for debugging
            with open("twitter_search_response.html", "w", encoding="utf-8") as file:
                file.write(soup.prettify())
            
            tweets = soup.find_all('div', {'data-testid': 'tweet'})
            for tweet in tweets[:max_results]:
                text = tweet.find('div', {'lang': 'en'}).get_text()
                video_url = tweet.find('a', {'role': 'link'})['href']
                video_url = f"https://twitter.com{video_url}"
                
                # Check if the tweet contains a video
                media = tweet.find('div', {'class': 'AdaptiveMedia-video'})
                if media:
                    results.append({
                        "platform": "Twitter",
                        "title": text[:100] + "...",  # Truncate long tweets
                        "url": video_url,
                        "upload_date": datetime.now().isoformat(),  # Use current date as a placeholder
                        "score": 0  # No engagement data available
                    })
                
                if len(results) >= max_results:
                    break
                    
        except requests.RequestException as e:
            self.last_error = e  # Store the last error
            print(f"Twitter scraping error: {e}")
        except Exception as e:
            self.last_error = e  # Store the last error
            print(f"Unexpected error during Twitter scraping: {e}")
            
        return results

    def _search_youtube(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """Search YouTube for basketball highlights with enhanced metadata"""
        results = []
        if 'youtube' not in self.clients:
            print("YouTube search skipped - client not initialized")
            return results
            
        try:
            # Search for videos with more metadata
            search_response = self.clients['youtube'].search().list(
                q=f"{query} basketball highlights",
                part='snippet',
                type='video',
                maxResults=max_results,
                videoDefinition='high',  # Only HD videos
                order='date',  # Sort by date
                relevanceLanguage='en',  # English results
                safeSearch='none'  # Allow all content
            ).execute()
            
            # Get video IDs for detailed info
            video_ids = [item['id']['videoId'] for item in search_response.get('items', [])]
            
            if video_ids:
                # Get detailed video information
                videos_response = self.clients['youtube'].videos().list(
                    part='snippet,statistics',
                    id=','.join(video_ids)
                ).execute()
                
                # Create results with more metadata
                for item in videos_response.get('items', []):
                    stats = item.get('statistics', {})
                    results.append({
                        "platform": "YouTube",
                        "title": item['snippet']['title'],
                        "url": f"https://www.youtube.com/watch?v={item['id']}",
                        "upload_date": item['snippet']['publishedAt'],
                        "score": int(stats.get('viewCount', 0)),  # Use view count as score
                        "description": item['snippet']['description'],
                        "views": stats.get('viewCount', 0),
                        "likes": stats.get('likeCount', 0)
                    })
                
        except Exception as e:
            self.last_error = e
            print(f"YouTube API error: {str(e)}")
            if "quota" in str(e).lower():
                print("YouTube API quota exceeded. Please try again later.")
            
        return results

    def _search_reddit(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """
        Search Reddit for basketball highlights
        """
        results = []
        try:
            subreddit = self.clients['reddit'].subreddit("basketball")
            for submission in subreddit.search(query, limit=max_results):
                if submission.is_video:
                    results.append({
                        "platform": "Reddit",
                        "title": submission.title,
                        "url": submission.url,
                        "upload_date": datetime.fromtimestamp(submission.created_utc).isoformat(),
                        "score": submission.score
                    })
                
        except Exception as e:
            self.last_error = e  # Store the last error
            print(f"Reddit API error: {e}")
            
        return results

    def _sort_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Sort results by score and date"""
        return sorted(results, 
                     key=lambda x: (x.get("score", 0), x.get("upload_date", "")), 
                     reverse=True)

class HighlightApp(tk.Tk):
    """Main application window"""
    def __init__(self):
        super().__init__()
        self.title("Basketball Highlights Aggregator")
        self.geometry("1000x600")
        self.searcher = HighlightSearcher()
        self._create_widgets()
        
    def _create_widgets(self):
        """Create and arrange GUI elements"""
        # Search frame
        search_frame = ttk.Frame(self, padding="5")
        search_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Add status label
        self.status_label = ttk.Label(search_frame, text="Ready to search")
        self.status_label.pack(side=tk.RIGHT)
        
        self.search_entry = ttk.Entry(search_frame, width=50)
        self.search_entry.pack(side=tk.LEFT, padx=(0, 5))
        self.search_entry.bind("<Return>", lambda e: self.start_search())
        
        # Make sure entry is enabled and focused
        self.search_entry.config(state='normal')
        self.search_entry.focus_set()
        
        self.search_button = ttk.Button(search_frame, 
                                      text="Search", 
                                      command=self.start_search)
        self.search_button.pack(side=tk.LEFT)
        
        # Results tree
        self.tree = ttk.Treeview(self, columns=("Platform", "Title", "Date", "URL"), 
                                show="headings")
        self.tree.heading("Platform", text="Platform")
        self.tree.heading("Title", text="Title")
        self.tree.heading("Date", text="Upload Date")
        self.tree.heading("URL", text="URL")
        
        # Column widths
        self.tree.column("Platform", width=100)
        self.tree.column("Title", width=400)
        self.tree.column("Date", width=150)
        self.tree.column("URL", width=300)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # Pack tree and scrollbar
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=5)
        
        # Bind double-click
        self.tree.bind("<Double-1>", self.on_item_double_click)
        
    def start_search(self):
        """Start search in a separate thread"""
        query = self.search_entry.get().strip()
        if not query:
            messagebox.showwarning("Input Required", 
                                 "Please enter search keywords.")
            self.search_entry.focus_set()  # Return focus to search entry
            return
            
        self.search_button.configure(state='disabled')
        self.search_entry.configure(state='disabled')  # Disable entry during search
        self.status_label.configure(text="Searching...")
        self.tree.delete(*self.tree.get_children())
        
        threading.Thread(target=self._run_search, 
                        args=(query,), 
                        daemon=True).start()
        
    def _run_search(self, query: str):
        """Execute search and update results"""
        try:
            results = self.searcher.search(query)
            if not results:
                # Check if the last error was due to access level
                if self.searcher.last_error and "access level" in str(self.searcher.last_error):
                    self.after(0, lambda: messagebox.showerror("Access Level Error", 
                        "Your Twitter API access level does not allow this operation. "
                        "Please apply for elevated access."))
                elif self.searcher.last_error:
                    self.after(0, lambda: messagebox.showerror("Search Error", 
                        f"Search failed: {self.searcher.last_error}"))
                else:
                    self.after(0, lambda: messagebox.showinfo("No Results", 
                        "No highlights found. Please try different keywords."))
            else:
                self.after(0, self._update_results, results)
        except Exception as e:
            self.after(0, self._show_error, str(e))
        finally:
            self.after(0, lambda: self.search_button.configure(state='normal'))
            self.after(0, lambda: self.search_entry.configure(state='normal'))
            self.after(0, lambda: self.status_label.configure(text="Ready"))
            self.after(0, lambda: self.search_entry.focus_set())  # Return focus after search
            
    def _update_results(self, results: List[Dict[str, Any]]):
        """Update tree with search results"""
        for result in results:
            self.tree.insert("", tk.END, values=(
                result["platform"],
                result["title"],
                result["upload_date"],
                result["url"]
            ))
            
    def _show_error(self, message: str):
        """Show error message"""
        messagebox.showerror("Error", f"Search failed: {message}")
        
    def on_item_double_click(self, event):
        """Handle double-click on result"""
        selection = self.tree.selection()
        if selection:
            item = selection[0]
            url = self.tree.item(item)["values"][2]  # updated index from 3 to 2
            webbrowser.open_new_tab(url)

def main():
    app = HighlightApp()
    app.mainloop()

if __name__ == "__main__":
    main()
    # Add your main application logic here
    print("Highlight App is running")
