# api/get_follower_count_route.py
from flask import jsonify, current_app
from api import api_bp
from auth import token_required

@api_bp.route('/get_follower_count', methods=['GET'])
@token_required
def get_follower_count():
    """Get follower count for @singularryai"""
    try:
        metrics = current_app.x_service.tweet_service.get_user_metrics('singularryai')
        current_app.logger.info(f"Retrieved metrics: {metrics}")

        if not metrics or 'followers_count' not in metrics:
            raise ValueError("No follower count available in metrics")

        return jsonify({
            'follower_count': metrics['followers_count']
        })
    except Exception as e:
        current_app.logger.error(f"Error retrieving follower count: {str(e)}")
        return jsonify({
            'error': 'An error occurred while retrieving follower count',
            'detail': str(e)
        }), 500