#!/usr/bin/env python3
"""
DailyYoutubeDigest - Deployment Script

This script handles the deployment of the DailyYoutubeDigest application to AWS Lambda.
"""

import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# AWS configuration
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
LAMBDA_FUNCTION_NAME = os.getenv("LAMBDA_FUNCTION_NAME", "daily-youtube-digest")
LAMBDA_ROLE_NAME = os.getenv("LAMBDA_ROLE_NAME", "daily-youtube-digest-role")
LAMBDA_TIMEOUT = int(os.getenv("LAMBDA_TIMEOUT", "300"))  # 5 minutes
LAMBDA_MEMORY_SIZE = int(os.getenv("LAMBDA_MEMORY_SIZE", "512"))  # 512 MB
SCHEDULE_EXPRESSION = os.getenv(
    "SCHEDULE_EXPRESSION", "cron(0 12 * * ? *)"
)  # Daily at 12:00 UTC


def create_lambda_role():
    """
    Create an IAM role for the Lambda function.

    Returns:
        str: The ARN of the created role or None if an error occurs
    """
    try:
        iam_client = boto3.client("iam", region_name=AWS_REGION)

        # Check if the role already exists
        try:
            response = iam_client.get_role(RoleName=LAMBDA_ROLE_NAME)
            logger.info(f"IAM role {LAMBDA_ROLE_NAME} already exists")
            return response["Role"]["Arn"]
        except iam_client.exceptions.NoSuchEntityException:
            pass

        # Create the role
        assume_role_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"Service": "lambda.amazonaws.com"},
                    "Action": "sts:AssumeRole",
                }
            ],
        }

        response = iam_client.create_role(
            RoleName=LAMBDA_ROLE_NAME,
            AssumeRolePolicyDocument=json.dumps(assume_role_policy),
            Description="Role for DailyYoutubeDigest Lambda function",
        )

        role_arn = response["Role"]["Arn"]
        logger.info(f"Created IAM role: {role_arn}")

        # Attach policies
        policies = [
            "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
            "arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess",
            "arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess",
        ]

        for policy_arn in policies:
            iam_client.attach_role_policy(
                RoleName=LAMBDA_ROLE_NAME, PolicyArn=policy_arn
            )
            logger.info(f"Attached policy {policy_arn} to role {LAMBDA_ROLE_NAME}")

        # Wait for the role to be available
        logger.info("Waiting for IAM role to be available...")
        waiter = iam_client.get_waiter("role_exists")
        waiter.wait(RoleName=LAMBDA_ROLE_NAME)

        # Additional delay to ensure the role is fully propagated
        import time

        time.sleep(10)

        return role_arn

    except ClientError as e:
        logger.error(f"Error creating IAM role: {str(e)}")
        return None


def create_deployment_package():
    """
    Create a deployment package (ZIP file) for the Lambda function.

    Returns:
        str: Path to the created ZIP file or None if an error occurs
    """
    try:
        # Create a temporary directory
        temp_dir = tempfile.mkdtemp()
        logger.info(f"Created temporary directory: {temp_dir}")

        # Copy the source code
        src_dir = Path("src")
        if not src_dir.exists():
            logger.error("Source directory not found")
            return None

        # Copy source files
        for item in src_dir.glob("**/*"):
            if item.is_file():
                # Create the destination directory if it doesn't exist
                dest_dir = Path(temp_dir) / item.relative_to(src_dir).parent
                dest_dir.mkdir(parents=True, exist_ok=True)

                # Copy the file
                shutil.copy2(item, dest_dir / item.name)

        # Install dependencies
        requirements_file = Path("requirements.txt")
        if requirements_file.exists():
            logger.info("Installing dependencies...")
            subprocess.check_call(
                [
                    sys.executable,
                    "-m",
                    "pip",
                    "install",
                    "-r",
                    str(requirements_file),
                    "-t",
                    temp_dir,
                ]
            )

        # Create the ZIP file
        zip_path = Path("deployment_package.zip")
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(temp_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, temp_dir)
                    zipf.write(file_path, arcname)

        logger.info(f"Created deployment package: {zip_path}")

        # Clean up the temporary directory
        shutil.rmtree(temp_dir)

        return str(zip_path)

    except Exception as e:
        logger.error(f"Error creating deployment package: {str(e)}")
        return None


def deploy_lambda_function(deployment_package, role_arn):
    """
    Deploy the Lambda function.

    Args:
        deployment_package (str): Path to the deployment package
        role_arn (str): ARN of the IAM role

    Returns:
        str: ARN of the Lambda function or None if an error occurs
    """
    try:
        lambda_client = boto3.client("lambda", region_name=AWS_REGION)

        # Check if the function already exists
        try:
            lambda_client.get_function(FunctionName=LAMBDA_FUNCTION_NAME)
            function_exists = True
        except lambda_client.exceptions.ResourceNotFoundException:
            function_exists = False

        # Read the deployment package
        with open(deployment_package, "rb") as f:
            zip_content = f.read()

        if function_exists:
            # Update the existing function
            logger.info(f"Updating Lambda function: {LAMBDA_FUNCTION_NAME}")
            response = lambda_client.update_function_code(
                FunctionName=LAMBDA_FUNCTION_NAME, ZipFile=zip_content
            )

            # Update the function configuration
            lambda_client.update_function_configuration(
                FunctionName=LAMBDA_FUNCTION_NAME,
                Timeout=LAMBDA_TIMEOUT,
                MemorySize=LAMBDA_MEMORY_SIZE,
                Environment={"Variables": {"PYTHONPATH": "/var/task"}},
            )
        else:
            # Create a new function
            logger.info(f"Creating Lambda function: {LAMBDA_FUNCTION_NAME}")
            response = lambda_client.create_function(
                FunctionName=LAMBDA_FUNCTION_NAME,
                Runtime="python3.9",
                Role=role_arn,
                Handler="main.lambda_handler",
                Code={"ZipFile": zip_content},
                Timeout=LAMBDA_TIMEOUT,
                MemorySize=LAMBDA_MEMORY_SIZE,
                Environment={"Variables": {"PYTHONPATH": "/var/task"}},
            )

        function_arn = response["FunctionArn"]
        logger.info(f"Lambda function deployed: {function_arn}")

        return function_arn

    except ClientError as e:
        logger.error(f"Error deploying Lambda function: {str(e)}")
        return None


def create_event_rule(function_arn):
    """
    Create an EventBridge rule to trigger the Lambda function on a schedule.

    Args:
        function_arn (str): ARN of the Lambda function

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        events_client = boto3.client("events", region_name=AWS_REGION)
        lambda_client = boto3.client("lambda", region_name=AWS_REGION)

        # Create the rule
        rule_name = f"{LAMBDA_FUNCTION_NAME}-schedule"
        logger.info(f"Creating EventBridge rule: {rule_name}")

        response = events_client.put_rule(
            Name=rule_name,
            ScheduleExpression=SCHEDULE_EXPRESSION,
            State="ENABLED",
            Description=f"Schedule for {LAMBDA_FUNCTION_NAME} Lambda function",
        )

        rule_arn = response["RuleArn"]

        # Add permission for EventBridge to invoke the Lambda function
        try:
            lambda_client.add_permission(
                FunctionName=LAMBDA_FUNCTION_NAME,
                StatementId=f"{LAMBDA_FUNCTION_NAME}-event-permission",
                Action="lambda:InvokeFunction",
                Principal="events.amazonaws.com",
                SourceArn=rule_arn,
            )
        except lambda_client.exceptions.ResourceConflictException:
            # Permission already exists
            pass

        # Create the target
        events_client.put_targets(
            Rule=rule_name, Targets=[{"Id": "1", "Arn": function_arn}]
        )

        logger.info(f"EventBridge rule created: {rule_arn}")
        return True

    except ClientError as e:
        logger.error(f"Error creating EventBridge rule: {str(e)}")
        return False


def main():
    """Main deployment function."""
    logger.info("Starting deployment of DailyYoutubeDigest")

    # Create IAM role
    role_arn = create_lambda_role()
    if not role_arn:
        logger.error("Failed to create IAM role")
        return False

    # Create deployment package
    deployment_package = create_deployment_package()
    if not deployment_package:
        logger.error("Failed to create deployment package")
        return False

    # Deploy Lambda function
    function_arn = deploy_lambda_function(deployment_package, role_arn)
    if not function_arn:
        logger.error("Failed to deploy Lambda function")
        return False

    # Create EventBridge rule
    if not create_event_rule(function_arn):
        logger.error("Failed to create EventBridge rule")
        return False

    logger.info("Deployment completed successfully")
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
