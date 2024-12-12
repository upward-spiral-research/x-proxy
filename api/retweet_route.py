from flask import request, jsonify, current_app
from api import api_bp
from auth import token_required

@api_bp.route('/retweet', methods=['POST'])
@token_required
def retweet():
    data = request.json
    tweet_id = data.get('tweet_id')

    if not tweet_id:
        return jsonify({'error': 'Missing tweet_id'}), 400

    try:
        result = current_app.x_service.retweet(tweet_id)

        if not result:
            return jsonify({
                'success': False,
                'error': 'Failed to retweet',
                'message': 'The retweet operation was unsuccessful'
            }), 400

        return jsonify({
            'success': True,
            'message': f'Successfully retweeted tweet {tweet_id}',
            'retweeted': result.get('retweeted', True)
        }), 200

    except ValueError as ve:
        return jsonify({
            'success': False,
            'error': 'Tweet not found',
            'message': str(ve)
        }), 404
    except Exception as e:
        current_app.logger.error(f"Error retweeting tweet {tweet_id}: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'An error occurred while retweeting the tweet',
            'message': str(e)
        }), 500