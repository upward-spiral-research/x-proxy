from flask import jsonify, current_app
from api import api_bp
from auth import token_required
import logging

logger = logging.getLogger(__name__)


@api_bp.route('/api/get_follower_count', methods=['GET'])
@token_required
def get_follower_count():
    """Get follower count for @singularryai"""
    username = 'singularryai'
    try:
        result = current_app.x_service.tweet_service.get_user_metrics(username)

        if not result or 'followers_count' not in result:
            logger.error("No follower count available in response")
            return jsonify({
                'error': 'Follower count not available',
                'follower_count': 0  # Fallback value
            }), 200  # Still return 200 to avoid client errors

        return jsonify({'follower_count': result['followers_count']}), 200

    except Exception as e:
        logger.error(f"Error retrieving follower count: {str(e)}",
                     exc_info=True)
        # Return last known count or 0 instead of error
        return jsonify({
            'follower_count': 0,  # Fallback value
            'error': 'Error retrieving follower count'
        }), 200  # Still return 200 to avoid client errors
