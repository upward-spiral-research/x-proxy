from functools import wraps
from tweepy.errors import TooManyRequests, TwitterServerError
import time
from datetime import datetime, timedelta
import logging
from threading import Lock

class RateLimitExceeded(Exception):
    def __init__(self, message, retry_after=None):
        super().__init__(message)
        self.retry_after = retry_after

class RateLimitHandler:
    def __init__(self):
        # App-level limits (OAuth 2.0 Bearer Token)
        self.app_limits = {
            'tweets_per_day': 1667,          # POST tweets per day
            'get_tweets': 15,                # GET tweets per 15-min window
            'search_tweets': 60,             # Search requests per 15-min window
            'get_user': 500,                 # GET user requests per 24h
            'get_user_data': 500            # GET user data requests per 24h
        }

        # User-level limits (OAuth 1.0a)
        self.user_limits = {
            'tweets_per_day': 100,           # POST tweets per day
            'get_tweets': 15,                # GET tweets per 15-min window
            'search_tweets': 60,             # Search requests per 15-min window
            'get_user': 100,                 # GET user requests per 24h
            'get_user_data': 100            # GET user data requests per 24h
        }

        # Tracking timestamps for app-level requests
        self.app_timestamps = {
            'tweets': [],           # Daily tweet posting
            'get_tweets': [],       # 15-min window GET requests
            'search_tweets': [],    # 15-min window search requests
            'get_user': [],         # 24h window user requests
            'get_user_data': []     # 24h window user data requests
        }

        # Tracking timestamps for user-level requests
        self.user_timestamps = {
            'tweets': [],           # Daily tweet posting
            'get_tweets': [],       # 15-min window GET requests
            'search_tweets': [],    # 15-min window search requests
            'get_user': [],         # 24h window user requests
            'get_user_data': []     # 24h window user data requests
        }

        self.lock = Lock()
        self.logger = logging.getLogger('RateLimitHandler')
        self.logger.setLevel(logging.INFO)

    def _clean_old_timestamps(self, timestamps, time_window):
        """Remove timestamps older than the given time window"""
        current_time = datetime.now()
        return [ts for ts in timestamps if current_time - ts < time_window]

    def check_rate_limit(self, action, user_auth=False):
        """
        Check if an action is allowed within rate limits

        Args:
            action: The type of action ('tweets', 'get_tweets', 'search_tweets', 'get_user', 'get_user_data')
            user_auth: Whether this is a user-authenticated request (True) or app-only (False)

        Returns:
            tuple: (bool: can_proceed, int: wait_time_seconds)
        """
        with self.lock:
            current_time = datetime.now()

            # Select appropriate limits and timestamps based on auth type
            limits = self.user_limits if user_auth else self.app_limits
            timestamps = self.user_timestamps if user_auth else self.app_timestamps

            # Determine time window based on action
            if action == 'tweets':
                window = timedelta(days=1)
                limit = limits['tweets_per_day']
            elif action in ['get_tweets', 'search_tweets']:
                window = timedelta(minutes=15)
                limit = limits[action]
            elif action in ['get_user', 'get_user_data']:
                window = timedelta(days=1)
                limit = limits[action]
            else:
                self.logger.warning(f"Unknown action type: {action}")
                return True, 0

            # Clean and check timestamps
            timestamps[action] = self._clean_old_timestamps(timestamps[action], window)

            if len(timestamps[action]) >= limit:
                oldest = timestamps[action][0]
                wait_time = (oldest + window - current_time).seconds
                self.logger.warning(
                    f"Rate limit reached for {action} ({'user' if user_auth else 'app'} auth). "
                    f"Wait time: {wait_time}s"
                )
                return False, wait_time

            timestamps[action].append(current_time)
            return True, 0

def handle_rate_limit(func):
    rate_limit_handler = RateLimitHandler()

    @wraps(func)
    def wrapper(*args, **kwargs):
        retries = 0
        MAX_RETRIES = 3
        INITIAL_RETRY_DELAY = 60

        # Get user_auth from kwargs or default to False
        user_auth = kwargs.get('user_auth', False)

        while retries < MAX_RETRIES:
            try:
                # Determine the type of request and check rate limit
                func_name = func.__name__

                if func_name == 'post_tweet':
                    action = 'tweets'
                elif func_name in ['get_tweet', 'get_tweets']:
                    action = 'get_tweets'
                elif 'search' in func_name:
                    action = 'search_tweets'
                elif func_name == 'get_user_data':
                    action = 'get_user_data'
                elif 'user' in func_name:
                    action = 'get_user'
                else:
                    action = None

                if action:
                    can_proceed, wait_time = rate_limit_handler.check_rate_limit(action, user_auth)
                    if not can_proceed:
                        rate_limit_handler.logger.warning(
                            f"Local rate limit hit for {action} ({'user' if user_auth else 'app'} auth). "
                            f"Wait time: {wait_time}s"
                        )
                        raise RateLimitExceeded(
                            f"Rate limit exceeded for {action}. Please wait {wait_time} seconds.",
                            retry_after=wait_time
                        )

                return func(*args, **kwargs)

            except (TooManyRequests, TwitterServerError) as e:
                retries += 1
                retry_after = int(e.response.headers.get('x-rate-limit-reset', 0)) - int(time.time())
                retry_after = max(retry_after, INITIAL_RETRY_DELAY * (2 ** (retries - 1)))

                if retries == MAX_RETRIES:
                    raise RateLimitExceeded(
                        'Twitter API rate limit exceeded. Please try again later.',
                        retry_after=retry_after
                    )

                rate_limit_handler.logger.warning(
                    f"Twitter rate limit hit, waiting {retry_after} seconds. Retry {retries}/{MAX_RETRIES}"
                )
                time.sleep(retry_after)

            except Exception as e:
                rate_limit_handler.logger.error(f"Unexpected error: {str(e)}", exc_info=True)
                raise

    return wrapper