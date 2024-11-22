import os
from config import Config
from .process_x_response import process_x_response
from .rate_limit_handler import handle_rate_limit
import logging
from datetime import datetime, timedelta
from threading import Lock


class FollowerCache:

    def __init__(self, cache_file="follower_cache.json"):
        self.cache_file = cache_file
        self.lock = Lock()
        self.cache = self._load_cache()
        self.cache_duration = timedelta(hours=6)
        self.min_update_interval = timedelta(hours=1)

    def _load_cache(self):
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r') as f:
                    data = json.load(f)
                    return {
                        k: {
                            'count': v['count'],
                            'timestamp': datetime.fromisoformat(v['timestamp'])
                        }
                        for k, v in data.items()
                    }
            return {}
        except Exception as e:
            logger.error(f"Error loading cache: {e}")
            return {}

    def _save_cache(self):
        try:
            with open(self.cache_file, 'w') as f:
                data = {
                    k: {
                        'count': v['count'],
                        'timestamp': v['timestamp'].isoformat()
                    }
                    for k, v in self.cache.items()
                }
                json.dump(data, f)
        except Exception as e:
            logger.error(f"Error saving cache: {e}")

    def get(self, username):
        with self.lock:
            cached_data = self.cache.get(username)
            if cached_data:
                return cached_data['count']
            return None

    def set(self, username, count):
        with self.lock:
            self.cache[username] = {
                'count': count,
                'timestamp': datetime.now()
            }
            self._save_cache()

    def needs_update(self, username):
        with self.lock:
            cached_data = self.cache.get(username)
            if not cached_data:
                return True
            now = datetime.now()
            age = now - cached_data['timestamp']
            return age > self.cache_duration


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
        self.follower_cache = FollowerCache()

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
    #@handle_rate_limit
    def get_user_metrics(self, username):
        """Get user metrics with aggressive caching"""
        try:
            # Always check cache first
            cached_count = self.follower_cache.get(username)

            # If we have cached data and don't need an update, return it
            if cached_count is not None and not self.follower_cache.needs_update(
                    username):
                self.logger.debug(
                    f"Returning cached count for {username}: {cached_count}")
                return {'followers_count': cached_count}

            # Only try to update if we need to
            try:
                # Make API request
                client = self.oauth2_handler.get_client()
                response = client.get_user(username=username,
                                           user_fields=['public_metrics'],
                                           user_auth=False)

                if response.data and hasattr(response.data, 'public_metrics'):
                    metrics = response.data.public_metrics
                    if 'followers_count' in metrics:
                        self.follower_cache.set(username,
                                                metrics['followers_count'])
                        return metrics

            except TooManyRequests:
                self.logger.warning(
                    f"Rate limit hit while updating {username}")
                if cached_count is not None:
                    return {'followers_count': cached_count}
                raise
            except Exception as e:
                self.logger.error(
                    f"Error updating metrics for {username}: {e}")
                if cached_count is not None:
                    return {'followers_count': cached_count}
                raise

            # If we got here and have cached data, return it
            if cached_count is not None:
                return {'followers_count': cached_count}

            raise ValueError("Could not retrieve follower count")

        except Exception as e:
            self.logger.error(f"Error in get_user_metrics: {str(e)}")
            if cached_count is not None:
                return {'followers_count': cached_count}
            raise
