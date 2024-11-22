from datetime import timedelta
import os
from config import Config
from .process_x_response import process_x_response
from .rate_limit_handler import handle_rate_limit
import logging
from threading import Lock

logging.basicConfig(level=logging.INFO)
metrics_logger = logging.getLogger('metrics')


class MetricsCache:

    def __init__(self, cache_duration=timedelta(minutes=15)):
        self.cache = {}
        self.cache_duration = cache_duration
        self.lock = Lock()

    def get(self, username):
        with self.lock:
            cached_data = self.cache.get(username)
            if cached_data:
                timestamp, metrics = cached_data
                if datetime.now() - timestamp < self.cache_duration:
                    metrics_logger.debug(f"Cache hit for {username}")
                    return metrics
            metrics_logger.debug(f"Cache miss for {username}")
            return None

    def set(self, username, metrics):
        with self.lock:
            self.cache[username] = (datetime.now(), metrics)
            metrics_logger.debug(f"Updated cache for {username}")


class TweetService:
    # Common tweet fields to request
    TWEET_FIELDS = [
        'author_id', 'note_tweet', 'public_metrics', 'referenced_tweets',
        'conversation_id', 'created_at', 'attachments'
    ]

    # Common expansions to request
    EXPANSIONS = [
        'author_id', 'referenced_tweets.id', 'referenced_tweets.id.author_id',
        'edit_history_tweet_ids', 'in_reply_to_user_id',
        'attachments.media_keys', 'attachments.poll_ids', 'geo.place_id',
        'entities.mentions.username'
    ]

    # Common user fields to request
    USER_FIELDS = [
        'created_at', 'description', 'entities', 'id', 'location',
        'most_recent_tweet_id', 'name', 'pinned_tweet_id', 'profile_image_url',
        'protected', 'public_metrics', 'url', 'username', 'verified',
        'verified_type', 'withheld'
    ]

    def __init__(self, oauth2_handler, media_service):
        self.oauth2_handler = oauth2_handler
        self.media_service = media_service
        self.metrics_cache = MetricsCache()

    @handle_rate_limit
    def post_reply(self, tweet_id, text):
        client = self.oauth2_handler.get_client()
        response = client.create_tweet(text=text,
                                       in_reply_to_tweet_id=tweet_id)
        return response.data['id']

    @handle_rate_limit
    def pull_mentions(self):
        client = self.oauth2_handler.get_client()
        response = client.get_users_mentions(
            id=Config.TWITTER_USER_ID,
            max_results=10,  # default is 10
            # since_id (int | str | None) – Returns results with a Tweet ID greater than (that is, more recent than) the specified ‘since’ Tweet ID. There are limits to the number of Tweets that can be accessed through the API. If the limit of Tweets has occurred since the since_id, the since_id will be forced to the oldest ID available.
            # start_time (datetime.datetime | str | None) – YYYY-MM-DDTHH:mm:ssZ (ISO 8601/RFC 3339). The oldest UTC timestamp from which the Tweets will be provided. Timestamp is in second granularity and is inclusive (for example, 12:00:01 includes the first second of the minute).
            expansions=self.EXPANSIONS,
            tweet_fields=self.TWEET_FIELDS,
            user_fields=self.USER_FIELDS)
        return process_x_response(response)

    @handle_rate_limit
    def post_tweet(self, text, in_reply_to_tweet_id=None, media_url=None):
        client = self.oauth2_handler.get_client()
        media_ids = None

        if media_url:
            temp_file_path = self.media_service.download_media(media_url)
            if temp_file_path:
                try:
                    media_id = self.media_service.upload_media(temp_file_path)
                    if media_id:
                        media_ids = [media_id]
                finally:
                    os.unlink(temp_file_path)

        response = client.create_tweet(
            text=text,
            in_reply_to_tweet_id=in_reply_to_tweet_id,
            media_ids=media_ids,
            user_auth=False)
        return response.data['id']

    @handle_rate_limit
    def get_tweet(self, tweet_id):
        client = self.oauth2_handler.get_client()
        response = client.get_tweet(id=tweet_id,
                                    expansions=self.EXPANSIONS,
                                    tweet_fields=self.TWEET_FIELDS,
                                    user_fields=self.USER_FIELDS)
        return process_x_response(response)

    @handle_rate_limit
    def search_recent_tweets(self, query):
        client = self.oauth2_handler.get_client()
        response = client.search_recent_tweets(query,
                                               expansions=self.EXPANSIONS,
                                               tweet_fields=self.TWEET_FIELDS,
                                               user_fields=self.USER_FIELDS)
        return process_x_response(response)

    @handle_rate_limit
    def get_conversation_thread(self, tweet_id):
        client = self.oauth2_handler.get_client()

        # Get the requested tweet
        requested_tweet = self.get_tweet(tweet_id)
        if not requested_tweet:
            return None

        conversation_id = requested_tweet.get('conversation_id')
        if not conversation_id:
            # If there's no conversation_id, return just the requested tweet
            return [requested_tweet]

        # Get the root tweet of the conversation
        root_tweet = self.get_tweet(conversation_id)
        if not root_tweet:
            # If we can't get the root tweet, return just the requested tweet
            return [requested_tweet]

        # Search for all tweets in the conversation
        query = f"conversation_id:{conversation_id}"
        response = client.search_recent_tweets(
            query,
            max_results=100,  # Adjust as needed
            expansions=self.EXPANSIONS,
            tweet_fields=self.TWEET_FIELDS,
            user_fields=self.USER_FIELDS)
        thread = process_x_response(response)

        # If no tweets were found in the conversation, return just the requested tweet
        if not thread:
            return [requested_tweet]

        # Ensure both the requested tweet and root tweet are in the thread
        thread = self.add_tweet_if_missing(thread, requested_tweet)
        thread = self.add_tweet_if_missing(thread, root_tweet)

        # Sort the thread by created_at timestamp
        thread.sort(key=lambda x: x['created_at'])

        return thread

    def add_tweet_if_missing(self, thread, tweet):
        if not any(t['id'] == tweet['id'] for t in thread):
            thread.append(tweet)
        return thread

    @handle_rate_limit
    def get_home_timeline(self, max_results=15, pagination_token=None):
        client = self.oauth2_handler.get_client()
        response = client.get_home_timeline(max_results=max_results,
                                            pagination_token=pagination_token,
                                            expansions=self.EXPANSIONS,
                                            tweet_fields=self.TWEET_FIELDS,
                                            user_fields=self.USER_FIELDS,
                                            user_auth=False)
        return process_x_response(response)

    @handle_rate_limit
    def get_user_by_username(self, username):
        client = self.oauth2_handler.get_client()
        # Remove @ symbol if present
        username = username.lstrip('@')
        response = client.get_user(username=username, user_auth=False)
        return response.data

    @handle_rate_limit
    def follow_user(self, username):
        client = self.oauth2_handler.get_client()
        # First, get the user ID from the username
        user_data = self.get_user_by_username(username)
        if not user_data:
            raise ValueError(f"User with username {username} not found")

        # Now follow the user using their ID
        response = client.follow_user(user_data.id, user_auth=False)
        return response.data

    @handle_rate_limit
    def unfollow_user(self, username):
        client = self.oauth2_handler.get_client()
        # First, get the user ID from the username
        user_data = self.get_user_by_username(username)
        if not user_data:
            raise ValueError(f"User with username {username} not found")

        # Now unfollow the user using their ID
        response = client.unfollow_user(user_data.id, user_auth=False)
        return response.data

    # services/tweet_service.py - Add the new method
    @handle_rate_limit
    def get_user_metrics(self, username):
        """Get user metrics from Twitter API v2 with caching"""
        try:
            # Remove @ symbol if present
            username = username.lstrip('@')
            metrics_logger.debug(f"Getting metrics for {username}")

            # Check cache first
            cached_metrics = self.metrics_cache.get(username)
            if cached_metrics is not None:
                metrics_logger.debug(f"Using cached metrics for {username}")
                return cached_metrics

            # If not in cache, fetch from Twitter
            metrics_logger.debug(f"Fetching fresh metrics for {username}")
            client = self.oauth2_handler.get_client()
            response = client.get_user(username=username,
                                       user_fields=['public_metrics'],
                                       user_auth=False)

            if not response.data or not hasattr(response.data,
                                                'public_metrics'):
                raise ValueError("No public metrics found in user data")

            metrics = response.data.public_metrics

            # Update cache with new metrics
            self.metrics_cache.set(username, metrics)

            return metrics

        except Exception as e:
            metrics_logger.error(f"Error getting user metrics: {str(e)}")
            # Try to return cached data if available
            cached_metrics = self.metrics_cache.get(username)
            if cached_metrics is not None:
                metrics_logger.info(
                    f"Returning cached metrics after error for {username}")
                return cached_metrics
            raise
