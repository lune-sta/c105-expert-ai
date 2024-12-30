import os

# リージョン、オレゴンが無難
REGION_NAME = os.environ.get("AWS_REGION", "us-west-2")

# 単純なタスクに使用するモデル
CHEAP_MODEL_ID = "us.anthropic.claude-3-5-sonnet-20241022-v2:0"

# 文章を生成したり高度なタスクに使用するモデル
EXPENSIVE_MODEL_ID = "us.anthropic.claude-3-5-sonnet-20241022-v2:0"

# リランクに使用するモデル
RERANK_MODEL_ID = "amazon.rerank-v1:0"

# Knowledge BaseのID
KNOWLEDGE_BASE_ID = os.environ.get("KNOWLEDGE_BASE_ID", "R4XR9BKK70")

# クエリごとにこの件数のドキュメントを取得する
RETRIEVE_DOCUMENTS_PER_QUERY = 20

# リランキングして最終的にこの件数を残す
MAX_DOCUMENTS_PER_PROMPT = 5

LANGUAGES = ["TypeScript", "JavaScript", "Python", "Shell"]
PROJECTS = [
    "AWS CLI",
    "AWS SDK for JavaScript",
    "AWS CDK",
    "Boto3",
    "React",
    "Hono",
    "SWR",
    "Prisma",
    "peewee",
    "PynamoDB",
    "Playwright",
    "Tailwind CSS",
    "Zustand",
]
