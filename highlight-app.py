import os
from datetime import datetime
from typing import List, Dict, Any
import requests
from bs4 import BeautifulSoup # type: ignore
import asyncio
import nest_asyncio
import webbrowser
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import QMainWindow, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget, QTableWidget, QTableWidgetItem, QMessageBox
from PyQt5.QtGui import QPainter, QBrush, QPen, QColor
from PyQt5.QtCore import Qt, QSize
nest_asyncio.apply()  # Allow nested event loops

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
    print(f"YOUTUBE_API_KEY: {youtube_key[:10]}..." if youtube_key else "YOUTUBE_API_KEY: Not found")
    
    # Verify that required environment variables are set
    required_vars = [
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
    'nitter': False,
    'twscrape': False,
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
    import aiohttp
    import asyncio
    from bs4 import BeautifulSoup
    APIS_AVAILABLE['nitter'] = True
except ImportError:
    print("Installing aiohttp...")
    os.system('pip install aiohttp')
    import aiohttp
    APIS_AVAILABLE['nitter'] = True

try:
    from twscrape import API, gather
    from twscrape.logger import set_log_level
    APIS_AVAILABLE['twscrape'] = True
except ImportError:
    print("Installing twscrape...")
    os.system('pip install twscrape')
    from twscrape import API, gather
    from twscrape.logger import set_log_level
    APIS_AVAILABLE['twscrape'] = True

from isodate import parse_duration

class APIKeys:
    """Manages API keys from environment variables"""
    def __init__(self):
        # Only YouTube keys are needed now
        self.youtube_key = os.getenv('YOUTUBE_API_KEY')
        self.reddit_client_id = os.getenv('REDDIT_CLIENT_ID')
        self.reddit_client_secret = os.getenv('REDDIT_CLIENT_SECRET')
        self.reddit_user_agent = os.getenv('REDDIT_USER_AGENT', 'HighlightApp/1.0')
        
        # Nitter instance URL
        self.nitter_instance = os.getenv('NITTER_INSTANCE', 'https://nitter.net')

        # Debug information
        print("\nAPI Keys Debug Information:")
        print(f"YouTube API Key: {self.youtube_key[:10]}..." if self.youtube_key else "YouTube API Key: None")
        print(f"Nitter Instance: {self.nitter_instance}")
        
        # Verify keys are not empty
        if not self.youtube_key or self.youtube_key.startswith('your_'):
            print("Warning: YouTube API key is missing or invalid")

class HighlightSearcher:
    """Handles searching across different platforms"""
    def __init__(self):
        self.api_keys = APIKeys()
        self.clients = {}
        self.last_error = None
        self._initialize_youtube_client()  # Directly initialize YouTube client

    def search(self, query: str, max_results: int = 100) -> List[Dict[str, Any]]:
        """Search YouTube for basketball videos with enhanced metadata"""
        results = []
        self.last_error = None
        print(f"Starting search for: {query}")

        # YouTube search
        if 'youtube' in self.clients:
            try:
                youtube_results = self._search_youtube(query, max_results)
                results.extend(youtube_results)
                print(f"Found {len(youtube_results)} YouTube results")
            except Exception as e:
                print(f"YouTube search error: {e}")
                self.last_error = str(e)
        else:
            print("YouTube client not initialized, skipping YouTube search.")

        # Ensure at least 50 results
        if len(results) < 50:
            print("Less than 50 results found, consider broadening your search query.")

        return results

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

    def _search_youtube(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """Search YouTube for basketball videos with enhanced metadata"""
        results = []
        if 'youtube' not in self.clients:
            print("YouTube search skipped - client not initialized")
            return results

        # Define trusted channels
        trusted_channels = [
            "NBA", "House of Highlights", "ESPN", "Bleacher Report",
            "NBA Reel", "ClutchPoints", "NBA Vintage Highlights", "Throwback Hoops",
            "Wilton Reports", "Dunkman827", "MaxaMillion711", "Nick Smith NBA"
        ]

        try:
            print(f"Searching YouTube for: {query}")
            # Search for videos with more metadata
            search_response = self.clients['youtube'].search().list(
                q=query,  # Use the query directly without descriptors
                part='snippet',
                type='video',
                maxResults=100,  # Increase maxResults to 100
                videoDefinition='high',  # Only HD videos
                order='viewCount',  # Sort by most viewed videos
                relevanceLanguage='en',  # English results
                safeSearch='none'  # Allow all content
            ).execute()
            print(f"YouTube search response: {search_response}")

            # Get video IDs for detailed info
            video_ids = [item['id']['videoId'] for item in search_response.get('items', [])]

            if video_ids:
                print(f"Found video IDs: {video_ids}")
                # Get detailed video information
                videos_response = self.clients['youtube'].videos().list(
                    part='snippet,contentDetails,statistics',
                    id=','.join(video_ids)
                ).execute()
                print(f"YouTube videos response: {videos_response}")

                # Create results with more metadata
                for item in videos_response.get('items', []):
                    stats = item.get('statistics', {})
                    content_details = item.get('contentDetails', {})
                    # Parse and format the upload date
                    upload_date = item['snippet']['publishedAt']
                    try:
                        parsed_date = datetime.strptime(upload_date, "%Y-%m-%dT%H:%M:%SZ")
                        formatted_date = parsed_date.strftime("%Y-%m-%d %H:%M")
                    except ValueError:
                        formatted_date = upload_date

                    # Get video duration and convert to HH:MM:SS
                    duration_iso = content_details.get('duration', 'PT0S')
                    duration_td = parse_duration(duration_iso)
                    duration = str(duration_td)

                    # Filter videos with over 50,000 views and duration of at least 1 minute
                    view_count = int(stats.get('viewCount', 0))
                    if view_count < 50000:
                        continue

                    # Ensure video duration is at least 1 minute
                    if duration_td.total_seconds() < 60:
                        continue

                    # Filter by trusted channels
                    channel_title = item['snippet']['channelTitle']
                    if channel_title not in trusted_channels:
                        continue

                    results.append({
                        "platform": "YouTube",
                        "title": item['snippet']['title'],
                        "author": channel_title,
                        "url": f"https://www.youtube.com/watch?v={item['id']}",
                        "upload_date": formatted_date,
                        "duration": duration,
                        "score": view_count,  # Use view count as score
                        "description": item['snippet']['description'],
                        "views": view_count,
                        "likes": stats.get('likeCount', 0)
                    })
            else:
                print("No video IDs found in YouTube search response.")

        except Exception as e:
            self.last_error = e
            print(f"YouTube API error: {str(e)}")
            if "quota" in str(e).lower():
                print("YouTube API quota exceeded. Please try again later.")
            elif "key" in str(e).lower():
                print(f"YouTube API key invalid or missing. Key starts with: {self.api_keys.youtube_key[:5]}")
            else:
                print("An unexpected error occurred during YouTube search.")

        return results

    def _sort_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Sort results by highest engagement (views, likes)"""
        return sorted(results, key=lambda x: (x.get("views", 0) + x.get("likes", 0)), reverse=True)[:100]

class HighlightApp(QMainWindow):
    """Main application using PyQt5"""
    def __init__(self):
        super().__init__()
        self.searcher = HighlightSearcher()
        self.init_ui()

    def init_ui(self):
        """Create the PyQt5 interface"""
        self.setWindowTitle('Basketball Highlights Aggregator')
        self.setGeometry(100, 100, 800, 600)

        # Create layout and widgets
        layout = QVBoxLayout()

        self.search_input = QLineEdit(self)
        self.search_input.setPlaceholderText('Enter search terms...')
        layout.addWidget(self.search_input)

        self.search_button = QPushButton("Search", self)
        self.search_button.clicked.connect(self.start_search)
        layout.addWidget(self.search_button)

        self.results_table = QTableWidget(self)
        self.results_table.setColumnCount(5)
        self.results_table.setHorizontalHeaderLabels(['Platform', 'Posted By', 'Title', 'Duration', 'URL'])
        layout.addWidget(self.results_table)

        self.status_label = QLabel('', self)
        layout.addWidget(self.status_label)

        # Set central widget
        central_widget = QWidget()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

    def start_search(self):
        """Handle search button click"""
        query = self.search_input.text()
        if not query:
            QMessageBox.warning(self, 'Input Required', 'Please enter a search term')
            return

        # Clear previous results
        self.results_table.setRowCount(0)
        self.status_label.setText('Searching...')

        try:
            # Perform search
            results = self.searcher.search(query, max_results=100)

            if not results:
                self.status_label.setText('No highlights found. Please try different keywords.')
                return

            # Display results
            self.status_label.setText(f'Found {len(results)} results')
            self.display_results(results)

            # Generate and save playlist link
            self.save_playlist_link(query, results)

        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Search failed: {str(e)}')
            self.status_label.setText('Search failed')

    def save_playlist_link(self, query: str, results: List[Dict[str, Any]]):
        """Generate a playlist link and save it to a text document"""
        video_ids = [result['url'].split('=')[-1] for result in results]
        playlist_link = f"https://www.youtube.com/watch_videos?video_ids={','.join(video_ids)}"

        # Define the file path
        file_path = os.path.join(r'C:\Users\nickt\Desktop\Highlight App\Videos', f'{query}.txt')

        # Save the playlist link to the file
        with open(file_path, 'w') as file:
            file.write(playlist_link)

        print(f"Playlist link saved to {file_path}")

    def display_results(self, results: List[Dict[str, Any]]):
        """Display search results in the table"""
        self.results_table.setRowCount(len(results))

        for row, result in enumerate(results):
            platform = result.get('platform', 'Unknown')
            posted_by = result.get('author', 'Unknown')
            title = result.get('content', result.get('title', 'No title'))
            duration = result.get('duration', 'Unknown')
            url = result.get('url', '')

            self.results_table.setItem(row, 0, QTableWidgetItem(platform))
            self.results_table.setItem(row, 1, QTableWidgetItem(posted_by))
            self.results_table.setItem(row, 2, QTableWidgetItem(title))
            self.results_table.setItem(row, 3, QTableWidgetItem(duration))
            self.results_table.setItem(row, 4, QTableWidgetItem(url))

            # Store the URL in the table item
            self.results_table.item(row, 4).setData(Qt.UserRole, url)

        # Connect the double-click event to a dedicated method
        self.results_table.cellDoubleClicked.connect(self.on_item_double_click)

    def on_item_double_click(self, row: int, column: int):
        """Handle double-click on result to open the URL"""
        if column == 4:  # Ensure the URL column is double-clicked
            item = self.results_table.item(row, column)
            url = item.data(Qt.UserRole)
            if url:
                webbrowser.open(url)

def main():
    app = QtWidgets.QApplication([])
    window = HighlightApp()
    window.show()
    app.exec_()

if __name__ == "__main__":
    main()
    print("Highlight App is running")
