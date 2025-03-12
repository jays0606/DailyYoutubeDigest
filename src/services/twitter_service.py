"""
Twitter Service

This module handles posting summaries to X (Twitter).
"""

import logging
import os

import tweepy

from src.services.openai_service import generate_tweet

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Get Twitter API credentials from environment variables
TWITTER_API_KEY = os.getenv("TWITTER_API_KEY")
TWITTER_API_SECRET = os.getenv("TWITTER_API_SECRET")
TWITTER_ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN")
TWITTER_ACCESS_TOKEN_SECRET = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")


def get_twitter_client():
    """Create and return a Twitter API client."""
    if not all(
        [
            TWITTER_API_KEY,
            TWITTER_API_SECRET,
            TWITTER_ACCESS_TOKEN,
            TWITTER_ACCESS_TOKEN_SECRET,
        ]
    ):
        logger.error("Twitter API credentials not found in environment variables")
        return None

    try:
        # Initialize the Twitter client
        client = tweepy.Client(
            consumer_key=TWITTER_API_KEY,
            consumer_secret=TWITTER_API_SECRET,
            access_token=TWITTER_ACCESS_TOKEN,
            access_token_secret=TWITTER_ACCESS_TOKEN_SECRET,
        )
        return client
    except Exception as e:
        logger.error(f"Error creating Twitter client: {str(e)}")
        return None


def post_to_twitter(summary, video_id, video_title, channel_name):
    """
    Post a summary of a YouTube video to X (Twitter).

    Args:
        summary (str): The full summary of the video
        video_id (str): The YouTube video ID
        video_title (str): The title of the video
        channel_name (str): The name of the YouTube channel

    Returns:
        bool: True if successful, False otherwise
    """
    client = get_twitter_client()
    if not client:
        return False

    try:
        # Generate a tweet-sized summary
        tweet_content = generate_tweet(summary, video_title, video_id, channel_name)

        if not tweet_content:
            logger.error("Failed to generate tweet content")
            return False

        # Post the tweet
        response = client.create_tweet(text=tweet_content)

        if response and hasattr(response, "data") and "id" in response.data:
            tweet_id = response.data["id"]
            logger.info(f"Successfully posted tweet with ID: {tweet_id}")
            return True
        else:
            logger.error("Failed to post tweet: Unexpected response format")
            return False

    except tweepy.TweepyException as e:
        logger.error(f"Tweepy error: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Error posting to Twitter: {str(e)}")
        return False
