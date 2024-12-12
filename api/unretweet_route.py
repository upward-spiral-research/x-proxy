from flask import request, jsonify, current_app
from api import api_bp
from auth import token_required

@api_bp.route('/unretweet', methods=['POST'])
@token_required
def unretweet():
    data = request.json
    source_tweet_id = data.get('source_tweet_id')

    if not source_tweet_id:
        return jsonify({'error': 'Missing source_tweet_id'}), 400

    try:
        result = current_app.x_service.unretweet(source_tweet_id)

        if not result:
            return jsonify({
                'success': False,
                'error': 'Failed to unretweet',
                'message': 'The unretweet operation was unsuccessful for an unknown reason. This is unusual as unretweet requests typically succeed even for non-existent tweets'
            }), 400

        return jsonify({
            'success': True,
            'message': f'Successfully unretweeted tweet {source_tweet_id}. Note: This request succeeds even if you weren\'t retweeting this tweet or if the tweet doesn\'t exist',
            'retweeted': result.get('retweeted', False)
        }), 200

    except ValueError as ve:
        return jsonify({
            'success': False,
            'error': 'Tweet not found',
            'message': str(ve)
        }), 404
    except Exception as e:
        current_app.logger.error(f"Error unretweeting tweet {source_tweet_id}: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'An error occurred while unretweeting the tweet',
            'message': str(e)
        }), 500