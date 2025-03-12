# DailyYoutubeDigest

Automatically summarize new YouTube videos from specified channels and share the summaries on a blog or X (Twitter).

## Overview

DailyYoutubeDigest is a serverless application that:

1. Monitors specified YouTube channels for new videos
2. Retrieves video transcripts
3. Generates concise summaries using OpenAI's API
4. Posts these summaries to a blog or X (Twitter)

## Architecture

- **Trigger**: AWS Lambda function scheduled daily via Amazon EventBridge
- **Channels**: Configurable list of YouTube channels stored in JSON (S3 or DynamoDB)
- **Video Detection**: YouTube Data API to identify new videos
- **Transcript Fetching**: youtube-transcript-api library
- **Summarization**: OpenAI's API for generating concise summaries
- **Posting**: Integration with blog platforms and X API
- **State Tracking**: DynamoDB to record processed videos and prevent duplicates

## Setup

### Prerequisites

- Python 3.9+
- AWS Account
- YouTube Data API key
- OpenAI API key
- X (Twitter) API credentials (if posting to X)

### Installation

1. Clone the repository:

   ```
   git clone https://github.com/yourusername/DailyYoutubeDigest.git
   cd DailyYoutubeDigest
   ```

2. Create a virtual environment and install dependencies:

   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Configure environment variables:
   - Create a `.env` file based on `.env.example`
   - Add your API keys and configuration

### Deployment

1. Configure AWS credentials:

   ```
   aws configure
   ```

2. Deploy using the provided script:
   ```
   python deploy.py
   ```

## Configuration

Edit the `config.json` file to:

- Add/remove YouTube channels to monitor
- Customize summary length and style
- Configure posting preferences

## Local Development

Run the application locally:

```
python src/main.py
```

## License

MIT

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
