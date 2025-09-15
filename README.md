# RAG Strands Sample

Amazon Bedrock Knowledge Bases と Strands Agents を使った簡易的なRAGのサンプルコードです。

## 概要

S3 Vectors + Knowledge Base + Strands Agents を使用してRAGを実装しています。

## 前提条件

- Python 3.12.6
- AWS CLI 2.28.8
- AWS アカウント（us-west-2リージョン）
- Amazon Bedrock Knowledge Base（事前作成済み）
- IAMロール（下記ポリシーをアタッチ）

### 必要なIAMポリシー

AgentCoreエージェント用のIAMロールに以下のポリシーが必要です：

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "ECRImageAccess",
            "Effect": "Allow",
            "Action": [
                "ecr:BatchGetImage",
                "ecr:GetDownloadUrlForLayer"
            ],
            "Resource": [
                "arn:aws:ecr:us-west-2:123456789012:repository/*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "logs:DescribeLogStreams",
                "logs:CreateLogGroup"
            ],
            "Resource": [
                "arn:aws:logs:us-west-2:123456789012:log-group:/aws/bedrock-agentcore/runtimes/*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "logs:DescribeLogGroups"
            ],
            "Resource": [
                "arn:aws:logs:us-west-2:123456789012:log-group:*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ],
            "Resource": [
                "arn:aws:logs:us-west-2:123456789012:log-group:/aws/bedrock-agentcore/runtimes/*:log-stream:*"
            ]
        },
        {
            "Sid": "ECRTokenAccess",
            "Effect": "Allow",
            "Action": [
                "ecr:GetAuthorizationToken"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "xray:PutTraceSegments",
                "xray:PutTelemetryRecords",
                "xray:GetSamplingRules",
                "xray:GetSamplingTargets"
            ],
            "Resource": [
                "*"
            ]
        },
        {
            "Effect": "Allow",
            "Resource": "*",
            "Action": "cloudwatch:PutMetricData",
            "Condition": {
                "StringEquals": {
                    "cloudwatch:namespace": "bedrock-agentcore"
                }
            }
        },
        {
            "Sid": "GetAgentAccessToken",
            "Effect": "Allow",
            "Action": [
                "bedrock-agentcore:GetWorkloadAccessToken",
                "bedrock-agentcore:GetWorkloadAccessTokenForJWT",
                "bedrock-agentcore:GetWorkloadAccessTokenForUserId"
            ],
            "Resource": [
                "arn:aws:bedrock-agentcore:us-west-2:123456789012:workload-identity-directory/default",
                "arn:aws:bedrock-agentcore:us-west-2:123456789012:workload-identity-directory/default/workload-identity/agent-*"
            ]
        },
        {
            "Sid": "BedrockModelInvocation",
            "Effect": "Allow",
            "Action": [
                "bedrock:InvokeModel",
                "bedrock:InvokeModelWithResponseStream",
                "bedrock:ApplyGuardrail"
            ],
            "Resource": [
                "arn:aws:bedrock:*::foundation-model/*",
                "arn:aws:bedrock:us-west-2:123456789012:*"
            ]
        },
        {
            "Sid": "KBManagement",
            "Effect": "Allow",
            "Action": [
                "bedrock:CreateKnowledgeBase",
                "bedrock:GetKnowledgeBase",
                "bedrock:UpdateKnowledgeBase",
                "bedrock:DeleteKnowledgeBase",
                "bedrock:ListKnowledgeBases",
                "bedrock:TagResource",
                "bedrock:UntagResource"
            ],
            "Resource": "*"
        },
        {
            "Sid": "KBDataSourceManagement",
            "Effect": "Allow",
            "Action": [
                "bedrock:CreateDataSource",
                "bedrock:GetDataSource",
                "bedrock:UpdateDataSource",
                "bedrock:DeleteDataSource",
                "bedrock:ListDataSources",
                "bedrock:StartIngestionJob",
                "bedrock:GetIngestionJob",
                "bedrock:ListIngestionJobs",
                "bedrock:Retrieve"
            ],
            "Resource": "*"
        }
    ]
}
```

**注意**: アカウントID（`123456789012`）は実際のAWSアカウントIDに置き換えてください。

## セットアップ

1. 依存パッケージのインストール
```bash
pip install -r requirements.txt
```

2. AgentCore の設定
IAMロールは自分で作成したロールを指定しましょう。
```bash
agentcore configure
```

3. デプロイ
Knowledge Base IDを環境変数として指定してデプロイします。
```bash
agentcore launch --env STRANDS_KNOWLEDGE_BASE_ID=your-knowledge-base-id
```

## 使い方

エージェントは Bedrock Knowledge Base に対して検索を実行し、取得した情報を基に回答を生成します。

## ファイル構成

- `agent.py` - カスタムツール（kb_search）を使用したRAG実装
- `requirements.txt` - 依存パッケージ一覧