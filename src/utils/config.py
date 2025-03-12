"""
Configuration Utility

This module handles loading and validating configuration for the application.
"""

import json
import logging
import os
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

# Default configuration file path
DEFAULT_CONFIG_PATH = "config.json"

# AWS S3 configuration
S3_CONFIG_BUCKET = os.getenv("S3_CONFIG_BUCKET")
S3_CONFIG_KEY = os.getenv("S3_CONFIG_KEY", "channels.json")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")


def load_config_from_file(config_path=DEFAULT_CONFIG_PATH):
    """
    Load configuration from a local JSON file.

    Args:
        config_path (str): Path to the configuration file

    Returns:
        dict: Configuration data or None if an error occurs
    """
    try:
        config_path = Path(config_path)
        if not config_path.exists():
            logger.error(f"Configuration file not found: {config_path}")
            return None

        with open(config_path, "r") as f:
            config = json.load(f)

        return config

    except json.JSONDecodeError as e:
        logger.error(f"Error parsing configuration file: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Error loading configuration from file: {str(e)}")
        return None


def load_config_from_s3():
    """
    Load configuration from an S3 bucket.

    Returns:
        dict: Configuration data or None if an error occurs
    """
    if not S3_CONFIG_BUCKET or not S3_CONFIG_KEY:
        logger.warning("S3 configuration not set, skipping S3 config load")
        return None

    try:
        s3_client = boto3.client("s3", region_name=AWS_REGION)
        response = s3_client.get_object(Bucket=S3_CONFIG_BUCKET, Key=S3_CONFIG_KEY)
        config_content = response["Body"].read().decode("utf-8")
        config = json.loads(config_content)

        logger.info(
            f"Successfully loaded configuration from S3: {S3_CONFIG_BUCKET}/{S3_CONFIG_KEY}"
        )
        return config

    except ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchKey":
            logger.warning(
                f"Configuration file not found in S3: {S3_CONFIG_BUCKET}/{S3_CONFIG_KEY}"
            )
        else:
            logger.error(f"AWS S3 error: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Error loading configuration from S3: {str(e)}")
        return None


def validate_config(config):
    """
    Validate the configuration data.

    Args:
        config (dict): Configuration data to validate

    Returns:
        bool: True if valid, False otherwise
    """
    if not config:
        logger.error("Configuration is empty")
        return False

    # Check for required top-level keys
    required_keys = ["channels", "global_settings"]
    for key in required_keys:
        if key not in config:
            logger.error(f"Missing required configuration key: {key}")
            return False

    # Check if channels is a list and not empty
    if not isinstance(config["channels"], list) or not config["channels"]:
        logger.error("Channels configuration must be a non-empty list")
        return False

    # Check each channel for required fields
    for i, channel in enumerate(config["channels"]):
        if not isinstance(channel, dict):
            logger.error(f"Channel at index {i} is not a dictionary")
            return False

        if "channel_id" not in channel or "name" not in channel:
            logger.error(
                f"Channel at index {i} is missing required fields (channel_id, name)"
            )
            return False

    # Check global settings for required fields
    required_global_settings = [
        "default_summary_style",
        "default_summary_length",
        "default_include_timestamps",
    ]

    for key in required_global_settings:
        if key not in config["global_settings"]:
            logger.error(f"Missing required global setting: {key}")
            return False

    return True


def load_config():
    """
    Load configuration from S3 or local file, with validation.

    Returns:
        dict: Validated configuration data
    """
    # Try to load from S3 first
    config = load_config_from_s3()

    # If S3 load failed, try local file
    if not config:
        logger.info("Falling back to local configuration file")
        config = load_config_from_file()

    # Validate the configuration
    if config and validate_config(config):
        return config

    # If all loading attempts failed or validation failed, use default configuration
    logger.warning("Using default configuration")
    return {
        "channels": [
            {
                "name": "Example Channel",
                "channel_id": "UC_x5XG1OV2P6uZZ5FSM9Ttw",  # Google Developers channel
                "summary_style": "concise",
                "summary_length": 500,
                "include_timestamps": True,
                "post_to_twitter": False,
                "post_to_blog": False,
            }
        ],
        "global_settings": {
            "default_summary_style": "concise",
            "default_summary_length": 500,
            "default_include_timestamps": True,
            "max_videos_per_channel": 3,
            "days_to_look_back": 1,
            "openai_model": "gpt-4-turbo",
        },
    }
