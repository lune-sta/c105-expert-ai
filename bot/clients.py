import boto3
from botocore.config import Config


bedrock_runtime_config = Config(retries={"max_attempts": 10, "mode": "standard"})
bedrock_runtime_client = boto3.client("bedrock-runtime", config=bedrock_runtime_config)
bedrock_agent_client = boto3.client("bedrock-agent-runtime")
