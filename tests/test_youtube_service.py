"""
Tests for the YouTube service module.
"""

import os
import unittest
from unittest.mock import MagicMock, patch

import pytest
from googleapiclient.errors import HttpError

# Add the src directory to the Python path
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.youtube_service import (
    get_channel_videos,
    get_video_transcript,
    get_video_details,
    get_youtube_client,
)


class TestYoutubeService(unittest.TestCase):
    """Test cases for the YouTube service module."""

    @patch("src.services.youtube_service.build")
    def test_get_youtube_client_success(self, mock_build):
        """Test successful creation of YouTube client."""
        # Set up the mock
        mock_build.return_value = MagicMock()

        # Set environment variable
        with patch.dict(os.environ, {"YOUTUBE_API_KEY": "test_api_key"}):
            # Call the function
            client = get_youtube_client()

            # Verify the result
            self.assertIsNotNone(client)
            mock_build.assert_called_once_with(
                "youtube", "v3", developerKey="test_api_key"
            )

    @patch("src.services.youtube_service.build")
    def test_get_youtube_client_no_api_key(self, mock_build):
        """Test YouTube client creation with no API key."""
        # Set up the mock
        mock_build.return_value = MagicMock()

        # Ensure the environment variable is not set
        with patch.dict(os.environ, {}, clear=True):
            # Call the function
            client = get_youtube_client()

            # Verify the result
            self.assertIsNone(client)
            mock_build.assert_not_called()

    @patch("src.services.youtube_service.build")
    def test_get_youtube_client_exception(self, mock_build):
        """Test YouTube client creation with an exception."""
        # Set up the mock to raise an exception
        mock_build.side_effect = Exception("Test exception")

        # Set environment variable
        with patch.dict(os.environ, {"YOUTUBE_API_KEY": "test_api_key"}):
            # Call the function
            client = get_youtube_client()

            # Verify the result
            self.assertIsNone(client)

    @patch("src.services.youtube_service.get_youtube_client")
    def test_get_channel_videos_success(self, mock_get_client):
        """Test successful retrieval of channel videos."""
        # Set up the mock
        mock_client = MagicMock()
        mock_search = MagicMock()
        mock_search_list = MagicMock()
        mock_search_list.list.return_value.execute.return_value = {
            "items": [{"id": {"videoId": "test_video_id"}}]
        }
        mock_client.search.return_value = mock_search_list
        mock_get_client.return_value = mock_client

        # Call the function
        videos = get_channel_videos("test_channel_id")

        # Verify the result
        self.assertEqual(len(videos), 1)
        self.assertEqual(videos[0]["id"]["videoId"], "test_video_id")
        mock_search_list.list.assert_called_once_with(
            part="snippet",
            channelId="test_channel_id",
            maxResults=5,
            order="date",
            type="video",
        )

    @patch("src.services.youtube_service.get_youtube_client")
    def test_get_channel_videos_with_published_after(self, mock_get_client):
        """Test retrieval of channel videos with publishedAfter parameter."""
        # Set up the mock
        mock_client = MagicMock()
        mock_search_list = MagicMock()
        mock_search_list.list.return_value.execute.return_value = {
            "items": [{"id": {"videoId": "test_video_id"}}]
        }
        mock_client.search.return_value = mock_search_list
        mock_get_client.return_value = mock_client

        # Call the function
        videos = get_channel_videos(
            "test_channel_id", max_results=3, published_after="2023-01-01T00:00:00Z"
        )

        # Verify the result
        self.assertEqual(len(videos), 1)
        mock_search_list.list.assert_called_once_with(
            part="snippet",
            channelId="test_channel_id",
            maxResults=3,
            order="date",
            type="video",
            publishedAfter="2023-01-01T00:00:00Z",
        )

    @patch("src.services.youtube_service.get_youtube_client")
    def test_get_channel_videos_no_client(self, mock_get_client):
        """Test retrieval of channel videos with no client."""
        # Set up the mock
        mock_get_client.return_value = None

        # Call the function
        videos = get_channel_videos("test_channel_id")

        # Verify the result
        self.assertIsNone(videos)

    @patch("src.services.youtube_service.get_youtube_client")
    def test_get_channel_videos_http_error(self, mock_get_client):
        """Test retrieval of channel videos with HTTP error."""
        # Set up the mock
        mock_client = MagicMock()
        mock_search_list = MagicMock()
        mock_search_list.list.return_value.execute.side_effect = HttpError(
            resp=MagicMock(status=403), content=b'{"error": {"message": "Test error"}}'
        )
        mock_client.search.return_value = mock_search_list
        mock_get_client.return_value = mock_client

        # Call the function
        videos = get_channel_videos("test_channel_id")

        # Verify the result
        self.assertIsNone(videos)

    @patch("src.services.youtube_service.YouTubeTranscriptApi")
    def test_get_video_transcript_success(self, mock_transcript_api):
        """Test successful retrieval of video transcript."""
        # Set up the mock
        mock_transcript_list = MagicMock()
        mock_transcript = MagicMock()
        mock_transcript.fetch.return_value = [
            {"text": "This is a test transcript."},
            {"text": "It has multiple entries."},
        ]
        mock_transcript_list.find_transcript.return_value = mock_transcript
        mock_transcript_api.list_transcripts.return_value = mock_transcript_list

        # Call the function
        transcript = get_video_transcript("test_video_id")

        # Verify the result
        self.assertEqual(
            transcript, "This is a test transcript. It has multiple entries."
        )
        mock_transcript_api.list_transcripts.assert_called_once_with("test_video_id")
        mock_transcript_list.find_transcript.assert_called_once_with(["en"])

    @patch("src.services.youtube_service.get_youtube_client")
    def test_get_video_details_success(self, mock_get_client):
        """Test successful retrieval of video details."""
        # Set up the mock
        mock_client = MagicMock()
        mock_videos_list = MagicMock()
        mock_videos_list.list.return_value.execute.return_value = {
            "items": [{"id": "test_video_id", "snippet": {"title": "Test Video"}}]
        }
        mock_client.videos.return_value = mock_videos_list
        mock_get_client.return_value = mock_client

        # Call the function
        video_details = get_video_details("test_video_id")

        # Verify the result
        self.assertEqual(video_details["id"], "test_video_id")
        self.assertEqual(video_details["snippet"]["title"], "Test Video")
        mock_videos_list.list.assert_called_once_with(
            part="snippet,contentDetails,statistics", id="test_video_id"
        )


if __name__ == "__main__":
    unittest.main()
