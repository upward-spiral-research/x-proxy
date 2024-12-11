from flask import request, jsonify, current_app
from api import api_bp
from auth import token_required
from urllib.parse import unquote_plus

@api_bp.route('/get_user_profile', methods=['GET'])
@token_required
def get_user_profile():
    username = request.args.get('username')
    user_id = request.args.get('user_id')

    if username:
        username = unquote_plus(username)  # Decode URL-encoded username

    if not username and not user_id:
        return jsonify({'error': 'Missing username or user_id'}), 400

    try:
        if username:
            user_profile = current_app.x_service.tweet_service.get_user_by_username(username)
        else:
            user_profile = current_app.x_service.tweet_service.get_user_by_id(user_id)

        if user_profile:
            return jsonify(user_profile), 200
        else:
            return jsonify({'error': 'User not found'}), 404

    except Exception as e:
        current_app.logger.error(f"Error retrieving user profile: {str(e)}", exc_info=True)
        return jsonify({'error': 'An error occurred while retrieving the user profile'}), 500