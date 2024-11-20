import tweepy
import json
import os
import time
import threading

class MyOAuth2UserHandler(tweepy.OAuth2UserHandler):
    def refresh_token(self, refresh_token):
        new_token = super().refresh_token(
            "https://api.twitter.com/2/oauth2/token",
            refresh_token=refresh_token,
            body=f"grant_type=refresh_token&client_id={self.client_id}",
        )
        return new_token

class OAuth2Handler:
    def __init__(self, client_id, client_secret, redirect_uri):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.oauth2_token = None
        self.setup_oauth2_handler()
        self.refresh_lock = threading.Lock()
        self.refresh_thread = None
        self.auth_url = None

    def setup_oauth2_handler(self):
        self.oauth2_user_handler = MyOAuth2UserHandler(
            client_id=self.client_id,
            redirect_uri=self.redirect_uri,
            scope=[
                "tweet.read", "tweet.write", "tweet.moderate.write",
                "users.read", "follows.read", "follows.write",
                "offline.access", "space.read", "mute.read",
                "mute.write", "like.read", "like.write",
                "list.read", "list.write", "block.read",
                "block.write", "bookmark.read", "bookmark.write"
            ],
            client_secret=self.client_secret
        )

    def load_oauth2_token(self):
        if os.path.exists('oauth2_token.json'):
            with open('oauth2_token.json', 'r') as f:
                self.oauth2_token = json.load(f)
            print("Loaded existing OAuth2 token from file.")
            return True
        else:
            print("oauth2_token.json not found.")
            return False

    def save_oauth2_token(self):
        with open('oauth2_token.json', 'w') as f:
            json.dump(self.oauth2_token, f)
        print("OAuth2 token saved to file.")

    def get_auth_url(self):
        self.auth_url = self.oauth2_user_handler.get_authorization_url()
        return self.auth_url

    def initial_oauth2_setup(self, callback_url):
        self.oauth2_token = self.oauth2_user_handler.fetch_token(callback_url)
        self.oauth2_token['expires_at'] = time.time() + self.oauth2_token['expires_in'] - 300
        self.save_oauth2_token()
        return self.oauth2_token

    def refresh_token(self):
        with self.refresh_lock:
            try:
                print("Attempting to refresh OAuth2 token...")
                new_token = self.oauth2_user_handler.refresh_token(self.oauth2_token['refresh_token'])
                self.oauth2_token.update(new_token)
                self.oauth2_token['expires_at'] = time.time() + new_token['expires_in'] - 300
                self.save_oauth2_token()
                print("OAuth2 token has been successfully refreshed and updated.")
                return True
            except Exception as e:
                print(f"Error refreshing token: {e}")
                return False

    def ensure_oauth2_token(self):
        if not self.oauth2_token:
            if not self.load_oauth2_token():
                return False

        current_time = time.time()
        if self.oauth2_token.get('expires_at', 0) - current_time < 600:
            print("Token close to expiry, attempting to refresh...")
            if not self.refresh_token():
                return False
        return True

    def start_refresh_thread(self):
        def refresh_loop():
            while True:
                if self.ensure_oauth2_token():
                    time_to_expiry = self.oauth2_token.get('expires_at', 0) - time.time()
                    sleep_time = min(time_to_expiry - 600, 3600)
                    time.sleep(max(sleep_time, 60))
                else:
                    time.sleep(60)

        self.refresh_thread = threading.Thread(target=refresh_loop, daemon=True)
        self.refresh_thread.start()

    def get_client(self):
        if self.ensure_oauth2_token():
            return tweepy.Client(self.oauth2_token['access_token'])
        return None