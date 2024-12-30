import json
from typing import TypedDict

from history import Message
from clients import bedrock_runtime_client
import config

_tool_name = "respond_to_user"
_tool_definition = {
    "toolSpec": {
        "name": _tool_name,
        "description": "Respond to the user and provides information about the referenced documents",
        "inputSchema": {
            "json": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "The response text in Japanese to the user",
                    },
                    "references": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "An array of URLs of the referenced documents",
                    },
                },
                "required": ["text", "references"],
            }
        },
    }
}

_prompt = """あなたはAWSやプログラミングに精通したスペシャリストで、ユーザーからの技術的な質問に正確に答えます。
ユーザーとのやりとりは<messages>タグで古い順に与えられるため一番最後のメッセージに返信する形で答えて下さい。
また回答に必要なドキュメントは事前にデータベースから検索され、<documents>タグで与えられます。
回答には $tool_name$ ツールのみを使用し、テキストは日本語で応答して下さい。

<messages>
$messages$
</messages>

<documents>
$documents$
</documents>
"""


class Answer(TypedDict):
    text: str
    references: list[str]


def generate_answer(messages: list[Message], documents: dict) -> Answer:
    prompt = (
        _prompt.replace("tool_name", _tool_name)
        .replace("$messages$", json.dumps(messages, indent=2, ensure_ascii=False))
        .replace("$documents$", json.dumps(documents, indent=2, ensure_ascii=False))
    )

    response = bedrock_runtime_client.converse(
        modelId=config.EXPENSIVE_MODEL_ID,
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
    answer = response["output"]["message"]["content"][0]["toolUse"]["input"]
    return answer
