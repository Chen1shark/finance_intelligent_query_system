import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.services.crawler_service import CrawlerService


class CrawlerServiceTestCase(unittest.TestCase):
    def test_is_crawl_cooling_down_returns_true_within_window(self):
        now = datetime(2026, 3, 24, 12, 0, 0)
        last_crawl_time = now - timedelta(seconds=90)
        self.assertTrue(CrawlerService.is_crawl_cooling_down(last_crawl_time, 180, now=now))

    def test_is_crawl_cooling_down_returns_false_outside_window(self):
        now = datetime(2026, 3, 24, 12, 0, 0)
        last_crawl_time = now - timedelta(seconds=300)
        self.assertFalse(CrawlerService.is_crawl_cooling_down(last_crawl_time, 180, now=now))

    def test_is_crawl_cooling_down_supports_iso_string(self):
        now = datetime(2026, 3, 24, 12, 0, 0)
        last_crawl_time = (now - timedelta(seconds=60)).isoformat(sep=" ")
        self.assertTrue(CrawlerService.is_crawl_cooling_down(last_crawl_time, 180, now=now))


if __name__ == "__main__":
    unittest.main()
