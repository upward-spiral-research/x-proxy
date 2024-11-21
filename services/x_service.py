from .tweet_service import TweetService
from .media_service import MediaService


class XService:

    def __init__(self, oauth2_handler, oauth1_api):
        self.media_service = MediaService(oauth1_api)
        self.tweet_service = TweetService(oauth2_handler, self.media_service)

    def get_tweet_with_thread(self, tweet_id):
        thread = self.tweet_service.get_conversation_thread(tweet_id)

        if not thread:
            return None

        requested_tweet = next(
            (tweet for tweet in thread if tweet['id'] == tweet_id), None)

        if not requested_tweet:
            return None

        ancestor_chain = self.build_ancestor_chain(requested_tweet, thread)
        sibling_tweets = self.get_sibling_tweets(requested_tweet, thread)
        children_tweets = self.get_children_tweets(requested_tweet, thread)

        return {
            'requested_tweet': requested_tweet,
            'root_tweet':
            ancestor_chain[0] if ancestor_chain else requested_tweet,
            'ancestor_chain': ancestor_chain,
            'sibling_tweets': sibling_tweets,
            'children_tweets': children_tweets
        }

    def build_ancestor_chain(self, tweet, thread):
        chain = []
        current_tweet = tweet

        while True:
            parent_id = self.get_parent_tweet_id(current_tweet)
            if not parent_id:
                break

            parent_tweet = next((t for t in thread if t['id'] == parent_id),
                                None)
            if not parent_tweet:
                break

            chain.insert(0, parent_tweet)
            current_tweet = parent_tweet

        return chain

    def get_sibling_tweets(self, tweet, thread):
        parent_id = self.get_parent_tweet_id(tweet)
        if not parent_id:
            return []  # No parent, so no siblings

        siblings = [
            t for t in thread if self.get_parent_tweet_id(t) == parent_id
            and t['id'] != tweet['id']
        ]
        siblings.sort(key=lambda x: x['created_at'])
        return siblings

    def get_children_tweets(self, tweet, thread):
        children = [
            t for t in thread if self.get_parent_tweet_id(t) == tweet['id']
        ]
        children.sort(key=lambda x: x['created_at'])
        return children

    def get_parent_tweet_id(self, tweet):
        referenced_tweets = tweet.get('referenced_tweets', [])
        replied_to = next(
            (ref for ref in referenced_tweets if ref['type'] == 'replied_to'),
            None)
        return replied_to['id'] if replied_to else None

    def get_user_data(self, username):
        """
        Get user data from Twitter API v2
        Args:
            username (str): Twitter username without @ symbol
        Returns:
            dict: User data including public metrics
        """
        # Get user by username first
        lookup_url = f"https://api.twitter.com/2/users/by/username/{username}"
        params = {
            "user.fields":
            "public_metrics"  # Explicitly request public_metrics
        }

        response = self.tweet_service.oauth2_handler.get(lookup_url,
                                                         params=params)
        response.raise_for_status()

        # Log the response for debugging
        self.tweet_service.logger.info(
            f"Twitter API response: {response.text}")

        user_data = response.json().get('data', {})

        if not user_data:
            raise ValueError(f"No user data found for username {username}")

        return user_data

    def __getattr__(self, name):
        return getattr(self.tweet_service, name)
