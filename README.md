# X-Proxy

X-Proxy is an API for simplifying X (formerly Twitter) requests for a single authenticated account. This project provides a set of endpoints that wrap around the X API, making it easier to interact with X's features programmatically. It handles renewing authentication tokens, albeit

## Features

-   Get tweets by ID
-   Search for tweets
-   Post new tweets (with optional media)
-   Manage draft tweets
-   Pull mentions
-   Follow and unfollow users
-   Retrieve home timeline
-   Secure authentication using bearer tokens

## API Endpoints

### Overview

This section covers the API routes implemented using Flask in this project. These routes include functionalities to get tweets, search for tweets, post tweets, manage draft tweets, pull mentions, follow users, and unfollow users. Authentication is handled using a token.

### Authentication

All routes are protected and require an Authorization header with a bearer token. The token is validated against the `API_SECRET_KEY` set in your environment variables.

### Endpoints

1. **Get Tweet**

    - **Endpoint:** `/api/get_tweet`
    - **Method:** `GET`
    - **Headers:**
        ```http
        Authorization: Bearer <API_SECRET_KEY>
        ```
    - **Query Parameters:**
        - `tweet_id` (string): The ID of the tweet to retrieve.
    - **Response:** Returns tweet details including author information, referenced tweets, and media.

2. **Search Tweets**

    - **Endpoint:** `/api/search_tweets`
    - **Method:** `GET`
    - **Headers:**
        ```http
        Authorization: Bearer <API_SECRET_KEY>
        ```
    - **Query Parameters:**
        - `query` (string): The search query.
    - **Response:** Returns a list of tweets matching the search query.

3. **Post Tweet**

    - **Endpoint:** `/api/post_tweet`
    - **Method:** `POST`
    - **Headers:**
        ```http
        Authorization: Bearer <API_SECRET_KEY>
        ```
    - **Request Body:** JSON object with `text`, optional `in_reply_to_tweet_id`, and optional `media_url`.
    - **Response:** Returns the ID of the posted tweet.

4. **Get Drafts**

    - **Endpoint:** `/api/get_drafts`
    - **Method:** `GET`
    - **Headers:**
        ```http
        Authorization: Bearer <API_SECRET_KEY>
        ```
    - **Response:** Returns a list of draft tweets.

5. **Post Draft Tweet**

    - **Endpoint:** `/api/post_draft_tweet`
    - **Method:** `POST`
    - **Headers:**
        ```http
        Authorization: Bearer <API_SECRET_KEY>
        ```
    - **Request Body:** JSON object with `draft_tweet_record_id`.
    - **Response:** Returns the ID and URL of the posted tweet.

6. **Pull Mentions**

    - **Endpoint:** `/api/pull_mentions`
    - **Method:** `GET`
    - **Headers:**
        ```http
        Authorization: Bearer <API_SECRET_KEY>
        ```
    - **Response:** Returns a list of mentions for the authenticated user.

7. **Follow User**

    - **Endpoint:** `/api/follow_user`
    - **Method:** `POST`
    - **Headers:**
        ```http
        Authorization: Bearer <API_SECRET_KEY>
        ```
    - **Request Body:** JSON object with `username`.
    - **Response:** Returns the result of the follow action.

8. **Unfollow User**
    - **Endpoint:** `/api/unfollow_user`
    - **Method:** `POST`
    - **Headers:**
        ```http
        Authorization: Bearer <API_SECRET_KEY>
        ```
    - **Request Body:** JSON object with `username`.
    - **Response:** Returns the result of the unfollow action.

For more detailed information about expected request and response formats for each endpoint, please refer to the [api.md](api.md) file in the project repository.

## Getting Started

### Prerequisites

-   Python 3.10 or higher
-   Poetry (for dependency management)

### Installation

1. Clone the repository:

    ```
    git clone https://github.com/virtuous-cycles/x-proxy.git
    cd x-proxy
    ```

2. Install dependencies:

    ```
    poetry install --no-root
    ```

3. Set up environment variables:
    - Copy the `.env.example` file to create a new `.env` file:
        ```
        cp .env.example .env
        ```
    - Open the `.env` file and fill in the necessary environment variables as defined in `config.py`. The `.env.example` file provides a template with placeholder values for all required variables.

### Running the Application

To start the application, run:

```
poetry run python main.py
```

## Project Structure

The X-Proxy project is organized into several key directories and files:

-   `api/`: Contains route definitions and API logic

    -   `__init__.py`: Initializes the API blueprint and imports all route modules
    -   Individual route modules (e.g., `get_tweet_route.py`, `post_tweet_route.py`, etc.)

-   `services/`: Houses service classes for interacting with X API and other functionalities

    -   `x_service.py`: Handles interactions with the X (Twitter) API
    -   `airtable_service.py`: Manages operations with Airtable
    -   `combined_services.py`: Coordinates operations involving both X and Airtable
    -   `oauth_setup.py`: Sets up and validates OAuth for X API
    -   `media_service.py`: Handles media-related operations (upload, download)
    -   `process_x_response.py`: Processes and enriches X API responses

-   `config.py`: Contains configuration settings and environment variable management

-   `main.py`: Main application entry point, sets up the Flask app and services

-   `error_handlers.py`: Defines custom error handlers for the application

-   `.env.example`: Template for required environment variables

-   `pyproject.toml`: Defines project dependencies and configuration for Poetry

-   `README.md`: Project documentation and setup instructions

-   `api.md`: Detailed API documentation

The project follows a modular structure, separating concerns into different directories and files:

1. API routes are defined in the `api/` directory, with each endpoint having its own file.
2. Business logic and external service interactions are encapsulated in the `services/` directory.
3. Configuration is centralized in `config.py`, pulling from environment variables.
4. The main application setup and running logic is in `main.py`.
5. Dependencies and project metadata are managed through `pyproject.toml` using Poetry.

This structure promotes maintainability, scalability, and separation of concerns, making it easier to extend and modify the project as needed.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License

Copyright (c) 2024 virtuous-cycles

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

## Acknowledgements

-   X API Documentation
-   Flask
-   Tweepy
