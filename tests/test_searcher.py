"""
Tests for HighlightSearcher
"""
import unittest
import sys
import os
from typing import List

# Define search result structure for type safety
try:
    from typing import TypedDict
except ImportError:
    from typing_extensions import TypedDict

# Add parent directory to path for importing
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from highlight_app import HighlightSearcher

class HighlightResult(TypedDict, total=False):
    platform: str
    title: str
    url: str
    score: int


class MockClient:
    """Mock client that returns predefined results"""

    def __init__(self, name: str, results: List[HighlightResult], should_fail: bool = False):
        self.name = name
        self.results = results
        self.should_fail = should_fail

    def search(self, query: str, max_results: int = 5) -> List[HighlightResult]:
        if self.should_fail:
            raise Exception(f"{self.name} search failed")
        return self.results


class TestHighlightSearcher(unittest.TestCase):

    def test_empty_searcher(self):
        """Test searcher with no clients"""
        searcher = HighlightSearcher()
        results = searcher.search("test")
        self.assertEqual(results, [])

    def test_single_client_success(self):
        """Test with one successful mock client"""
        mock_results: List[HighlightResult] = [
            {"platform": "mock", "title": "Test highlight", "url": "http://test.com", "score": 10}
        ]
        client = MockClient("mock", mock_results)
        searcher = HighlightSearcher({"mock": client})
        results = searcher.search("test")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["platform"], "mock")

    def test_multiple_clients(self):
        """Test aggregation from multiple clients"""
        mock1_results: List[HighlightResult] = [{"platform": "m1", "title": "title1", "url": "url1", "score": 5}]
        mock2_results: List[HighlightResult] = [
            {"platform": "m2", "title": "title2", "url": "url2", "score": 10},
            {"platform": "m2", "title": "title3", "url": "url3", "score": 1}
        ]
        clients = {
            "mock1": MockClient("mock1", mock1_results),
            "mock2": MockClient("mock2", mock2_results)
        }
        searcher = HighlightSearcher(clients)
        results = searcher.search("test")
        self.assertEqual(len(results), 3)
        # Should be sorted by score desc, then date
        self.assertEqual(results[0]["platform"], "mock1")  # score 5 but earlier?

    def test_client_failure(self):
        """Test handling of client failures"""
        mock_success: List[HighlightResult] = [{"platform": "good", "score": 1}]
        mock_fail = MockClient("bad", [], should_fail=True)
        clients = {
            "good": MockClient("good", mock_success),
            "bad": mock_fail
        }
        searcher = HighlightSearcher(clients)
        results = searcher.search("test")
        # Should get results from good client only
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["platform"], "good")
        # Should have set last_error
        self.assertIsNotNone(searcher.last_error)


if __name__ == '__main__':
    unittest.main()
