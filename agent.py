import os
import json
from typing import Optional
import boto3
from strands import Agent, tool
from strands.models import BedrockModel
from bedrock_agentcore.runtime import BedrockAgentCoreApp

app = BedrockAgentCoreApp()

SYSTEM_PROMPT = """
# RAGシステム用システムプロンプト

## 基本方針
あなたは検索結果に基づいて正確で有用な回答を提供するアシスタントです。以下のガイドラインに従って回答してください。

## 回答ルール

### 1. 検索結果の活用
- 提供された検索結果のみを情報源として使用してください
- 検索結果にない情報については推測や一般知識での補完を行わず、「検索結果に含まれていません」と明記してください
- 複数の検索結果がある場合は、それらを統合して包括的な回答を作成してください

### 2. 引用の方法
- 回答中の情報には必ず引用番号を付けてください（例：[1]、[2]）
- 回答の後に「## 参考文献」セクションを設け、以下の形式で引用元を明記してください：
  ```
  [1] タイトル - 出典元（URL、日付等）
  [2] タイトル - 出典元（URL、日付等）
  ```
- 検索結果がJSONとして渡される場合は、各項目から uri を抽出し、参考文献のURLとして使用してください
- 参考文献は「ファイル名 と S3 URL」を明示してください。ファイル名はURIの末尾（例: s3://bucket/path/file.pdf → file.pdf）を用い、URLは location.s3Location.uri（なければ metadata.x-amz-bedrock-kb-source-uri）を使用してください。ページ番号があれば (p.<番号>) を付与してください。
  例:
  ```
  [1] s3://strands-sample-xxx/Amazon Bedrock AgentCoreを使ってみよう！ 〜各種機能のポイントを解説〜 (5).pdf (p.78)
  [2] s3://strands-sample-xxx/Amazon Bedrock AgentCoreを使ってみよう！ 〜各種機能のポイントを解説〜 (5).pdf (p.4)
  ```

### 3. 回答形式
- 簡潔で分かりやすい日本語で回答してください
- 重要なポイントは見出しや箇条書きを使って整理してください
- 長い回答の場合は冒頭に要約を記載してください

### 4. 情報が不足している場合
- 検索結果が質問に対して十分でない場合は、その旨を明記してください
- 部分的に回答できる場合は、回答できる範囲を明確にしてください

### 5. ツールの利用
- このエージェントは `kb_search(query, max_results?)` ツールを利用できます
- 回答前に適切なクエリで `kb_search` を呼び出し、結果を根拠として使用してください
- 複数結果がある場合は重要度の高いものを優先し、重複を避けて統合してください
- 引用に使った順序で番号を付与し、末尾の「参考文献」に対応させてください（title/URL/日付など、取得できる範囲で記載）

## 回答例

**質問：** 太陽光発電の仕組みについて教えてください。

**回答：**

太陽光発電は、太陽電池（ソーラーセル）を使って太陽光を直接電気エネルギーに変換するシステムです[1]。

### 基本的な仕組み
太陽電池は主にシリコンなどの半導体材料で作られており、太陽光が当たることで光電効果により電子が動き、電流が発生します[1]。この電流は直流電流のため、一般的な家庭用電力として使用するには、インバーターという装置で交流電流に変換する必要があります[2]。

### 主な構成要素
- **太陽電池パネル**: 太陽光を電気に変換[1]
- **インバーター**: 直流を交流に変換[2]
- **パワーコンディショナー**: 電力の調整・制御[2]

### 発電効率
現在の一般的な太陽電池の変換効率は15-20%程度です[1]。

## 参考文献
[1] 太陽光発電の基礎知識 - 新エネルギー財団（https://example.com/solar-basics, 2023年4月）
[2] 太陽光発電システムの構成 - エネルギー技術研究所（https://example.com/solar-system, 2023年3月）

---

## 注意事項
- 検索結果が古い情報の場合は、その旨を明記してください
- 矛盾する情報が複数ある場合は、両方の見解を紹介してください
- 専門用語を使用する際は、可能な限り分かりやすい説明を併記してください
"""

STRANDS_KNOWLEDGE_BASE_ID = os.environ.get("STRANDS_KNOWLEDGE_BASE_ID", "")

# =========================
# Bedrock KB ツール用セットアップ
# =========================
BEDROCK_CLIENT = None
KB_REGION = os.environ.get("AWS_REGION", "us-west-2")
KB_MAX_RESULTS = int(os.environ.get("BEDROCK_KB_MAX_RESULTS", "5"))


def _ensure_bedrock_client(region_name: Optional[str] = None):
    global BEDROCK_CLIENT
    if BEDROCK_CLIENT is None:
        region = region_name or KB_REGION
        BEDROCK_CLIENT = boto3.client("bedrock-agent-runtime", region_name=region)
    return BEDROCK_CLIENT


@tool
def kb_search(query: str, max_results: Optional[int] = None) -> str:
    """
    ナレッジベースから関連文書を検索（Retrieve）します。

    Args:
        query: 検索クエリ
        max_results: 取得する最大件数（省略時は環境変数の既定）

    Returns:
        JSON文字列（success, resultsなどを含む）
    """
    try:
        client = _ensure_bedrock_client()
        kb_id = STRANDS_KNOWLEDGE_BASE_ID
        if not kb_id:
            return json.dumps({
                "success": False,
                "error": "環境変数 STRANDS_KNOWLEDGE_BASE_ID が設定されていません",
                "results": [],
            }, ensure_ascii=False)

        num = max_results or KB_MAX_RESULTS
        response = client.retrieve(
            knowledgeBaseId=kb_id,
            retrievalQuery={"text": query},
            retrievalConfiguration={
                "vectorSearchConfiguration": {
                    "numberOfResults": num,
                    "overrideSearchType": "SEMANTIC",
                }
            },
        )

        items = []
        for r in response.get("retrievalResults", []):
            content = r.get("content", {})
            location = r.get("location", {})
            metadata = r.get("metadata", {})
            s3loc = location.get("s3Location", {})
            page = metadata.get("x-amz-bedrock-kb-document-page-number")
            if isinstance(page, float) and page.is_integer():
                page = int(page)
            items.append({
                "content": content.get("text", ""),
                "type": content.get("type"),
                "score": r.get("score", 0),
                "uri": s3loc.get("uri") or metadata.get("x-amz-bedrock-kb-source-uri"),
                "page": page,
                "chunkId": metadata.get("x-amz-bedrock-kb-chunk-id"),
                "dataSourceId": metadata.get("x-amz-bedrock-kb-data-source-id"),
            })
        return json.dumps({
            "success": True,
            "query": query,
            "results_count": len(items),
            "results": items,
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({
            "success": False,
            "query": query,
            "error": str(e),
            "results": [],
        }, ensure_ascii=False)


@app.entrypoint
async def entrypoint(payload):
    message = payload.get("prompt", "")
    model = payload.get("model", {})
    model_id = model.get("modelId", "anthropic.claude-3-5-haiku-20241022-v1:0")
    model = BedrockModel(
        model_id=model_id,
        params={"max_tokens": 4096, "temperature": 0.7},
        region=KB_REGION,
    )
    agent = Agent(
        model=model,
        system_prompt=SYSTEM_PROMPT,
        tools=[kb_search],
    )
    
    stream_messages = agent.stream_async(message)
    async for message in stream_messages:
        if "event" in message:
            yield message

if __name__ == "__main__":
    app.run()