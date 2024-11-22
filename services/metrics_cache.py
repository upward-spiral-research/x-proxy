# metrics_cache.py
from datetime import datetime, timedelta
from threading import Lock
import logging
from datetime import datetime, timedelta


class MetricsCache:

    def __init__(self, cache_duration=timedelta(minutes=15)):
        self.cache = {}
        self.cache_duration = cache_duration
        self.lock = Lock()
        self.logger = logging.getLogger('MetricsCache')

    def get(self, username):
        with self.lock:
            cached_data = self.cache.get(username)
            if cached_data:
                timestamp, metrics = cached_data
                if datetime.now() - timestamp < self.cache_duration:
                    self.logger.debug(f"Cache hit for {username}")
                    return metrics
            self.logger.debug(f"Cache miss for {username}")
            return None

    def set(self, username, metrics):
        with self.lock:
            self.cache[username] = (datetime.now(), metrics)
            self.logger.debug(f"Updated cache for {username}")
