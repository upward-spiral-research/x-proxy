from functools import wraps
from tweepy.errors import TooManyRequests
import time

MAX_RETRIES = 3
INITIAL_RETRY_DELAY = 5  # seconds

class RateLimitExceeded(Exception):
    def __init__(self, message, retry_after):
        super().__init__(message)
        self.retry_after = retry_after

def handle_rate_limit(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        retries = 0
        while retries < MAX_RETRIES:
            try:
                return func(*args, **kwargs)
            except TooManyRequests as e:
                retries += 1
                if retries == MAX_RETRIES:
                    raise RateLimitExceeded(
                        'Rate limit exceeded. Please try again later.',
                        retry_after=e.response.headers.get('Retry-After', INITIAL_RETRY_DELAY)
                    )
                retry_delay = INITIAL_RETRY_DELAY * (2 ** (retries - 1))
                time.sleep(retry_delay)
    return wrapper