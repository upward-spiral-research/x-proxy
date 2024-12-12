from flask import request, jsonify, current_app
from api import api_bp
from auth import token_required

@api_bp.route('/unlike_tweet', methods=['POST'])
@token_required
def unlike_tweet():
    data = request.json
    tweet_id = data.get('tweet_id')

    if not tweet_id:
        return jsonify({'error': 'Missing tweet_id'}), 400

    try:
        result = current_app.x_service.unlike_tweet(tweet_id)

        if not result:
            return jsonify({
                'success': False,
                'error': 'Failed to unlike tweet',
                'message': 'The unlike operation was unsuccessful'
            }), 400

        return jsonify({
            'success': True,
            'message': f'Successfully unliked tweet {tweet_id}',
            'liked': result.get('liked', False)
        }), 200

    except ValueError as ve:
        return jsonify({
            'success': False,
            'error': 'Tweet not found',
            'message': str(ve)
        }), 404
    except Exception as e:
        current_app.logger.error(f"Error unliking tweet {tweet_id}: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'An error occurred while unliking the tweet',
            'message': str(e)
        }), 500