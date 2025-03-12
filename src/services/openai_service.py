"""
OpenAI Service

This module handles interactions with the OpenAI API for generating summaries.
"""

import logging
import os

from openai import OpenAI

logger = logging.getLogger(__name__)

# Get OpenAI API key from environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)


def generate_summary(
    transcript,
    style="concise",
    max_length=500,
    include_timestamps=True,
    video_title=None,
    channel_name=None,
    model="gpt-4-turbo",
):
    """
    Generate a summary of a YouTube video transcript using OpenAI's API.

    Args:
        transcript (str): The video transcript text
        style (str): Summary style - "concise", "detailed", or "bullet_points"
        max_length (int): Maximum length of the summary in words
        include_timestamps (bool): Whether to include timestamps in the summary
        video_title (str): The title of the video
        channel_name (str): The name of the YouTube channel
        model (str): The OpenAI model to use

    Returns:
        str: Generated summary or None if an error occurs
    """
    if not OPENAI_API_KEY:
        logger.error("OpenAI API key not found in environment variables")
        return None

    if not transcript:
        logger.error("No transcript provided for summarization")
        return None

    try:
        # Prepare the prompt based on the style and other parameters
        timestamps_instruction = (
            "Include key timestamps for important points."
            if include_timestamps
            else "Do not include timestamps."
        )

        # Add video title and channel name to the prompt if available
        context = ""
        if video_title and channel_name:
            context = f"The video is titled '{video_title}' from the channel '{channel_name}'. "

        prompt = f"{context}Summarize the following YouTube video transcript in a {style} style with a maximum of {max_length} words. {timestamps_instruction}\n\nTRANSCRIPT:\n{transcript}"

        # Truncate the prompt if it's too long (OpenAI has token limits)
        max_prompt_length = 16000  # A conservative limit
        if len(prompt) > max_prompt_length:
            logger.warning(
                f"Transcript too long ({len(prompt)} chars), truncating to {max_prompt_length} chars"
            )
            prompt = (
                prompt[:max_prompt_length] + "... [transcript truncated due to length]"
            )

        # Call the OpenAI API
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant that summarizes YouTube videos accurately and concisely.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.5,
            max_tokens=1000,
        )

        # Extract and return the summary
        summary = response.choices[0].message.content.strip()
        return summary

    except Exception as e:
        logger.error(f"Error generating summary with OpenAI: {str(e)}")
        return None


def generate_tweet(summary, video_title, video_id, channel_name, max_length=280):
    """
    Generate a tweet-sized summary for posting to X (Twitter).

    Args:
        summary (str): The full summary of the video
        video_title (str): The title of the video
        video_id (str): The YouTube video ID
        channel_name (str): The name of the YouTube channel
        max_length (int): Maximum length of the tweet

    Returns:
        str: Tweet-sized summary or None if an error occurs
    """
    if not OPENAI_API_KEY:
        logger.error("OpenAI API key not found in environment variables")
        return None

    try:
        # Calculate the length of the video URL and attribution
        video_url = f"https://youtu.be/{video_id}"
        attribution = f" - {channel_name}"

        # Calculate the available length for the summary
        # Account for spaces between components and a buffer
        available_length = max_length - len(video_url) - len(attribution) - 3

        if available_length <= 50:
            logger.warning("Not enough space for a meaningful tweet summary")
            return None

        prompt = f"""
        Create a concise and engaging tweet about this YouTube video that will make people want to watch it.
        Video title: {video_title}
        Channel: {channel_name}
        Summary: {summary}
        
        The tweet must be no longer than {available_length} characters as I will add the video URL and attribution separately.
        Do not include hashtags, the URL, or the channel name in your response.
        """

        # Call the OpenAI API
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",  # Using a smaller model for efficiency
            messages=[
                {
                    "role": "system",
                    "content": "You are a social media expert who creates engaging tweets.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_tokens=100,
        )

        # Extract the tweet content
        tweet_content = response.choices[0].message.content.strip()

        # Ensure the tweet is within the length limit
        if len(tweet_content) > available_length:
            tweet_content = tweet_content[: available_length - 3] + "..."

        # Combine with the video URL and attribution
        full_tweet = f"{tweet_content} {video_url}{attribution}"

        return full_tweet

    except Exception as e:
        logger.error(f"Error generating tweet with OpenAI: {str(e)}")
        return None
