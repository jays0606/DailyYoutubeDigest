"""
YouTube Service

This module handles interactions with the YouTube API and transcript retrieval.
"""

import logging
import os

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from youtube_transcript_api import (
    YouTubeTranscriptApi,
    TranscriptsDisabled,
    NoTranscriptFound,
)

logger = logging.getLogger(__name__)

# Get YouTube API key from environment variables
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")


def get_youtube_client():
    """Create and return a YouTube API client."""
    if not YOUTUBE_API_KEY:
        logger.error("YouTube API key not found in environment variables")
        return None

    try:
        youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
        return youtube
    except Exception as e:
        logger.error(f"Error creating YouTube client: {str(e)}")
        return None


def get_channel_videos(channel_id, max_results=5, published_after=None):
    """
    Get recent videos from a YouTube channel.

    Args:
        channel_id (str): The YouTube channel ID
        max_results (int): Maximum number of videos to return
        published_after (str): ISO 8601 timestamp (e.g., 2023-01-01T00:00:00Z)

    Returns:
        list: List of video items or None if an error occurs
    """
    youtube = get_youtube_client()
    if not youtube:
        return None

    try:
        # Build the search request
        search_params = {
            "part": "snippet",
            "channelId": channel_id,
            "maxResults": max_results,
            "order": "date",
            "type": "video",
        }

        # Add publishedAfter parameter if provided
        if published_after:
            search_params["publishedAfter"] = published_after

        # Execute the search request
        search_response = youtube.search().list(**search_params).execute()

        return search_response.get("items", [])

    except HttpError as e:
        logger.error(f"YouTube API error: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Error fetching videos for channel {channel_id}: {str(e)}")
        return None


def get_video_transcript(video_id, language_code="en"):
    """
    Get the transcript for a YouTube video.

    Args:
        video_id (str): The YouTube video ID
        language_code (str): Preferred language code (default: "en")

    Returns:
        str: Concatenated transcript text or None if an error occurs
    """
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

        # Try to get the transcript in the specified language
        try:
            transcript = transcript_list.find_transcript([language_code])
        except NoTranscriptFound:
            # If not found, try to get any available transcript and translate it
            try:
                transcript = transcript_list.find_transcript([])
                transcript = transcript.translate(language_code)
            except Exception as e:
                logger.error(
                    f"Error translating transcript for video {video_id}: {str(e)}"
                )
                return None

        # Get the transcript data
        transcript_data = transcript.fetch()

        # Concatenate the transcript text
        full_transcript = " ".join([entry["text"] for entry in transcript_data])

        return full_transcript

    except TranscriptsDisabled:
        logger.warning(f"Transcripts are disabled for video {video_id}")
        return None
    except NoTranscriptFound:
        logger.warning(f"No transcript found for video {video_id}")
        return None
    except Exception as e:
        logger.error(f"Error fetching transcript for video {video_id}: {str(e)}")
        return None


def get_video_details(video_id):
    """
    Get detailed information about a YouTube video.

    Args:
        video_id (str): The YouTube video ID

    Returns:
        dict: Video details or None if an error occurs
    """
    youtube = get_youtube_client()
    if not youtube:
        return None

    try:
        video_response = (
            youtube.videos()
            .list(part="snippet,contentDetails,statistics", id=video_id)
            .execute()
        )

        if not video_response.get("items"):
            logger.warning(f"No video details found for video {video_id}")
            return None

        return video_response["items"][0]

    except HttpError as e:
        logger.error(f"YouTube API error: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Error fetching video details for {video_id}: {str(e)}")
        return None
