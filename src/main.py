#!/usr/bin/env python3
"""
DailyYoutubeDigest - Main Entry Point

This script is the main entry point for the DailyYoutubeDigest application.
It orchestrates the process of fetching new videos from YouTube channels,
generating summaries, and posting them to various platforms.
"""

import json
import logging
import os
from datetime import datetime, timedelta

from dotenv import load_dotenv

from services.openai_service import generate_summary
from services.twitter_service import post_to_twitter
from services.youtube_service import get_channel_videos, get_video_transcript
from utils.config import load_config
from utils.db import get_processed_videos, mark_video_as_processed

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


def process_video(video, channel_config):
    """Process a single video by generating a summary and posting it."""
    video_id = video["id"]["videoId"]
    video_title = video["snippet"]["title"]
    channel_name = video["snippet"]["channelTitle"]

    logger.info(f"Processing video: {video_title} ({video_id})")

    # Get video transcript
    transcript = get_video_transcript(video_id)
    if not transcript:
        logger.warning(f"Could not get transcript for video {video_id}")
        return False

    # Generate summary
    summary_style = channel_config.get(
        "summary_style", config["global_settings"]["default_summary_style"]
    )
    summary_length = channel_config.get(
        "summary_length", config["global_settings"]["default_summary_length"]
    )
    include_timestamps = channel_config.get(
        "include_timestamps", config["global_settings"]["default_include_timestamps"]
    )

    summary = generate_summary(
        transcript,
        style=summary_style,
        max_length=summary_length,
        include_timestamps=include_timestamps,
        video_title=video_title,
        channel_name=channel_name,
    )

    if not summary:
        logger.warning(f"Could not generate summary for video {video_id}")
        return False

    # Post to Twitter if configured
    if channel_config.get("post_to_twitter", False):
        twitter_success = post_to_twitter(summary, video_id, video_title, channel_name)
        if not twitter_success:
            logger.warning(f"Failed to post to Twitter for video {video_id}")

    # Post to blog if configured (to be implemented)
    if channel_config.get("post_to_blog", False):
        # Placeholder for blog posting functionality
        logger.info(f"Would post to blog for video {video_id}")

    # Mark video as processed
    mark_video_as_processed(video_id, channel_name, summary)

    logger.info(f"Successfully processed video {video_id}")
    return True


def lambda_handler(event, context):
    """AWS Lambda handler function."""
    try:
        main()
        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Processing completed successfully"}),
        }
    except Exception as e:
        logger.error(f"Error in lambda_handler: {str(e)}")
        return {"statusCode": 500, "body": json.dumps({"message": f"Error: {str(e)}"})}


def main():
    """Main function to process videos from all configured channels."""
    global config
    config = load_config()

    # Get list of already processed videos
    processed_videos = get_processed_videos()

    # Calculate the date to look back for new videos
    days_to_look_back = config["global_settings"].get("days_to_look_back", 1)
    published_after = (
        datetime.utcnow() - timedelta(days=days_to_look_back)
    ).isoformat() + "Z"

    # Process each channel
    for channel in config["channels"]:
        channel_id = channel["channel_id"]
        channel_name = channel["name"]

        logger.info(f"Processing channel: {channel_name}")

        # Get recent videos from the channel
        videos = get_channel_videos(
            channel_id,
            max_results=config["global_settings"].get("max_videos_per_channel", 3),
            published_after=published_after,
        )

        if not videos:
            logger.info(f"No new videos found for channel {channel_name}")
            continue

        # Process each video
        for video in videos:
            video_id = video["id"]["videoId"]

            # Skip if already processed
            if video_id in processed_videos:
                logger.info(f"Video {video_id} already processed, skipping")
                continue

            process_video(video, channel)


if __name__ == "__main__":
    main()
