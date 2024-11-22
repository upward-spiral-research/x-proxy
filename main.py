import os
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
from flask import Flask, request, redirect
from api import api_bp
from config import Config
from services.x_service import XService
from services.oauth_setup import setup_and_validate_oauth
from services.airtable_service import AirtableService
from services.combined_services import CombinedServices
from error_handlers import register_error_handlers

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    app.debug = False  # Enable debug mode

    print("Registered routes:")

    @app.route('/auth/twitter/start')
    def start_oauth():
        print("Starting OAuth flow")
        oauth2_handler, oauth1_handler = setup_and_validate_oauth(app.config)
        app.oauth2_handler = oauth2_handler
        app.oauth1_handler = oauth1_handler
        auth_url = oauth2_handler.get_auth_url()
        return redirect(auth_url)

    @app.route('/auth/twitter/callback')
    def oauth_callback():
        print("Callback received", request.url)
        if not app.oauth2_handler:
            return "OAuth flow not initiated", 400

        try:
            app.oauth2_handler.initial_oauth2_setup(request.url)
            app.oauth2_handler.start_refresh_thread()

            x_service = XService(app.oauth2_handler, app.oauth1_handler.api)
            app.x_service = x_service
            airtable_service = AirtableService(app.config)
            app.airtable_service = airtable_service
            app.combined_services = CombinedServices(airtable_service, x_service)

            return "Authentication successful!"
        except Exception as e:
            print(f"Callback error: {str(e)}")
            return f"Authentication failed: {str(e)}", 400

    @app.route('/')
    def hello():
        return "API is running. Visit /auth/twitter/start to initialize."

    app.register_blueprint(api_bp, url_prefix='/api')
    register_error_handlers(app)

    print([str(r) for r in app.url_map.iter_rules()])  # Print all registered routes
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000)