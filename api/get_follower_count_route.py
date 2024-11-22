from flask import jsonify, current_app
from api import api_bp
from auth import token_required


@api_bp.route('/get_follower_count', methods=['GET'])  # Removed /api prefix
@token_required
def get_follower_count():
    """Get follower count for @singularryai"""
    username = 'singularryai'
    try:
        result = current_app.x_service.tweet_service.get_user_metrics(username)

        if not result or 'followers_count' not in result:
            return jsonify({
                'error': 'Follower count not available',
                'follower_count': 0
            }), 200

        return jsonify({'follower_count': result['followers_count']}), 200

    except Exception as e:
        return jsonify({'follower_count': 0, 'error': str(e)}), 200
