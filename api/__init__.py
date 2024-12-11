from flask import Blueprint

api_bp = Blueprint('api', __name__)

def init_app():
    from . import (
        get_drafts_route,
        pull_mentions_route,
        post_tweet_route,
        post_draft_tweet_route,
        get_tweet_route,
        search_tweets_route,
        get_home_timeline_route,
        follow_user_route,
        unfollow_user_route,
        get_user_profile_route
    )

# Ensure routes are registered when this module is imported
init_app()