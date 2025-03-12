"""
Database Utility

This module handles DynamoDB operations for tracking processed videos.
"""

import json
import logging
import os
from datetime import datetime

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

# DynamoDB configuration
DYNAMODB_TABLE = os.getenv("DYNAMODB_TABLE", "daily-youtube-digest-videos")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")


def get_dynamodb_client():
    """Create and return a DynamoDB client."""
    try:
        dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
        return dynamodb
    except Exception as e:
        logger.error(f"Error creating DynamoDB client: {str(e)}")
        return None


def ensure_table_exists():
    """
    Ensure the DynamoDB table exists, creating it if necessary.

    Returns:
        bool: True if the table exists or was created, False otherwise
    """
    dynamodb = get_dynamodb_client()
    if not dynamodb:
        return False

    try:
        # Check if table exists
        dynamodb_client = boto3.client("dynamodb", region_name=AWS_REGION)
        existing_tables = dynamodb_client.list_tables()["TableNames"]

        if DYNAMODB_TABLE in existing_tables:
            return True

        # Create the table if it doesn't exist
        table = dynamodb.create_table(
            TableName=DYNAMODB_TABLE,
            KeySchema=[
                {"AttributeName": "video_id", "KeyType": "HASH"}  # Partition key
            ],
            AttributeDefinitions=[{"AttributeName": "video_id", "AttributeType": "S"}],
            ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
        )

        # Wait for the table to be created
        table.meta.client.get_waiter("table_exists").wait(TableName=DYNAMODB_TABLE)
        logger.info(f"Created DynamoDB table: {DYNAMODB_TABLE}")

        return True

    except ClientError as e:
        logger.error(f"Error ensuring DynamoDB table exists: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error ensuring DynamoDB table exists: {str(e)}")
        return False


def get_processed_videos():
    """
    Get a list of already processed video IDs from DynamoDB.

    Returns:
        set: Set of processed video IDs
    """
    if not ensure_table_exists():
        logger.warning("DynamoDB table does not exist, returning empty set")
        return set()

    try:
        dynamodb = get_dynamodb_client()
        table = dynamodb.Table(DYNAMODB_TABLE)

        # Scan the table to get all processed videos
        response = table.scan(ProjectionExpression="video_id")

        # Extract video IDs from the response
        video_ids = {item["video_id"] for item in response.get("Items", [])}

        # Handle pagination if there are more items
        while "LastEvaluatedKey" in response:
            response = table.scan(
                ProjectionExpression="video_id",
                ExclusiveStartKey=response["LastEvaluatedKey"],
            )
            video_ids.update({item["video_id"] for item in response.get("Items", [])})

        logger.info(f"Retrieved {len(video_ids)} processed videos from DynamoDB")
        return video_ids

    except ClientError as e:
        logger.error(f"DynamoDB error getting processed videos: {str(e)}")
        return set()
    except Exception as e:
        logger.error(f"Error getting processed videos: {str(e)}")
        return set()


def mark_video_as_processed(video_id, channel_name, summary):
    """
    Mark a video as processed in DynamoDB.

    Args:
        video_id (str): The YouTube video ID
        channel_name (str): The name of the YouTube channel
        summary (str): The generated summary

    Returns:
        bool: True if successful, False otherwise
    """
    if not ensure_table_exists():
        logger.error("Failed to ensure DynamoDB table exists")
        return False

    try:
        dynamodb = get_dynamodb_client()
        table = dynamodb.Table(DYNAMODB_TABLE)

        # Create the item to store
        timestamp = datetime.utcnow().isoformat()
        item = {
            "video_id": video_id,
            "channel_name": channel_name,
            "summary": summary,
            "processed_at": timestamp,
        }

        # Put the item in the table
        table.put_item(Item=item)

        logger.info(f"Marked video {video_id} as processed in DynamoDB")
        return True

    except ClientError as e:
        logger.error(f"DynamoDB error marking video as processed: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Error marking video as processed: {str(e)}")
        return False


def get_video_summary(video_id):
    """
    Get the summary for a processed video from DynamoDB.

    Args:
        video_id (str): The YouTube video ID

    Returns:
        dict: Video data including summary or None if not found
    """
    if not ensure_table_exists():
        logger.warning("DynamoDB table does not exist")
        return None

    try:
        dynamodb = get_dynamodb_client()
        table = dynamodb.Table(DYNAMODB_TABLE)

        # Get the item from the table
        response = table.get_item(Key={"video_id": video_id})

        # Check if the item exists
        if "Item" not in response:
            logger.warning(f"Video {video_id} not found in DynamoDB")
            return None

        return response["Item"]

    except ClientError as e:
        logger.error(f"DynamoDB error getting video summary: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Error getting video summary: {str(e)}")
        return None
