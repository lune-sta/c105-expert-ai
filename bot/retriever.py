import json
from typing import TypedDict

from history import Message
from clients import bedrock_runtime_client, bedrock_agent_client
import config


_tool_name = "search_vector_store"
_tool_definition = {
    "toolSpec": {
        "name": _tool_name,
        "description": "Search from vector store based on user input",
        "inputSchema": {
            "json": {
                "type": "object",
                "properties": {
                    "queries": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of search query texts",
                    },
                    "summary": {
                        "type": "string",
                        "description": "Summary of the search query",
                    },
                },
                "required": ["queries", "summary"],
            }
        },
    }
}

_prompt = """Your task is to be a technical supporter of users.
Search the necessary information from the vector database.
Conversations with user are given as <messages> in order of oldest to newest.
Use only the $tool_name$ tool, and write the text in English.
You can write up to 4 objects in the conditions argument.

<messages>$messages$</messages>
"""


class SearchCondition(TypedDict):
    queries: list[str]
    summary: str


def generate_search_condition(messages: list[Message]) -> SearchCondition:
    prompt = _prompt.replace("$tool_name$", _tool_name).replace(
        "$messages$", json.dumps(messages, indent=2, ensure_ascii=False)
    )

    response = bedrock_runtime_client.converse(
        modelId=config.CHEAP_MODEL_ID,
        messages=[{"role": "user", "content": [{"text": prompt}]}],
        toolConfig={
            "tools": [_tool_definition],
            "toolChoice": {
                "tool": {
                    "name": _tool_name,
                },
            },
        },
    )
    return response["output"]["message"]["content"][0]["toolUse"]["input"]


class Metadata(TypedDict):
    languages: list[str]
    projects: list[str]
    url: str
    s3_uri: str


class Document(TypedDict):
    text: str
    metadata: Metadata


def _retrieve(query: str) -> list[Document]:
    result: list[Document] = []
    response = bedrock_agent_client.retrieve(
        knowledgeBaseId=config.KNOWLEDGE_BASE_ID,
        retrievalConfiguration={
            "vectorSearchConfiguration": {
                "implicitFilterConfiguration": {
                    "metadataAttributes": [
                        {
                            "description": f'Programming languages. Choose at most one: {", ".join(config.LANGUAGES)}',
                            "key": "languages",
                            "type": "STRING_LIST",
                        },
                        {
                            "description": f'Project name. Choose at most one: {", ".join(config.PROJECTS)}',
                            "key": "projects",
                            "type": "STRING_LIST",
                        },
                    ],
                    "modelArn": f"arn:aws:bedrock:{config.REGION_NAME}"
                    f"::foundation-model/{config.CHEAP_MODEL_ID.replace('us.', '')}",
                },
                "numberOfResults": config.RETRIEVE_DOCUMENTS_PER_QUERY,
                "overrideSearchType": "HYBRID",
            }
        },
        retrievalQuery={"text": query},
    )

    for res in response["retrievalResults"]:
        result.append(
            Document(
                text=res["content"]["text"],
                metadata=Metadata(
                    languages=res["metadata"]["languages"],
                    projects=res["metadata"]["projects"],
                    url=res["metadata"]["url"],
                    s3_uri=res["metadata"]["x-amz-bedrock-kb-source-uri"],
                ),
            )
        )
    return result


def _rerank(query: str, documents: list[Document]) -> list[Document]:
    result = []
    response = bedrock_agent_client.rerank(
        queries=[
            {"textQuery": {"text": query}, "type": "TEXT"},
        ],
        rerankingConfiguration={
            "bedrockRerankingConfiguration": {
                "modelConfiguration": {
                    "modelArn": f"arn:aws:bedrock:{config.REGION_NAME}::foundation-model/{config.RERANK_MODEL_ID}"
                },
                "numberOfResults": min(
                    config.RETRIEVE_DOCUMENTS_PER_QUERY, len(documents)
                ),
            },
            "type": "BEDROCK_RERANKING_MODEL",
        },
        sources=[
            {
                "inlineDocumentSource": {
                    "jsonDocument": {
                        "text": document["text"],
                        "url": document["metadata"]["url"],
                        # 'languages': document['metadata']['languages'],
                        # 'projects': document['metadata']['projects'],
                    },
                    "type": "JSON",
                },
                "type": "INLINE",
            }
            for document in documents
        ],
    )
    for res in response["results"]:
        result.append(documents[res["index"]])
    return result


def retrieve_and_rerank(
    messages: list[Message], use_rerank: bool = True
) -> (SearchCondition, list[Document]):
    result = []
    search_condition = generate_search_condition(messages)

    for query in search_condition["queries"]:
        documents = _retrieve(query)
        result.extend(documents)

    if use_rerank and result:
        result = _rerank(search_condition["summary"], result)

    return search_condition, result
