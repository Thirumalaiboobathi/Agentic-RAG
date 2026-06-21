# Multi-Agent LangGraph System

> Orchestrator + 4 agents (Knowledge Brain, SQL, Research, Author) over FastAPI WebSocket, deployed on ECS Fargate.

LangGraph 1.2.4 · Bedrock Claude 3.5 Sonnet · OpenSearch · RDS PostgreSQL · Google CSE

---

## Architecture

```
Angular client (WebSocket)
        ↓
   ws://.../ws/agent
        ↓
  [Guardrail input]  ──blocked──→ [Blocked response] ─┐
        ↓ clean                                        │
  [Orchestrator] decides route                         │
        ├── org mentioned    → [Knowledge Brain] ──┐   │
        ├── data keywords    → [SQL Agent] ────────┤   │
        └── everything else  → [Research Agent] ───┤   │
                                                    ↓   │
                                            [Author Agent] (PII mask)
                                                    ↓   │
                                            [Evaluator] ←┘
                                                    ↓
                                          PostgreSQL + CloudWatch
```

Every response flows through the Author Agent (single output point, PII masking).
Every run is captured by the Evaluator to RDS + CloudWatch.

---

## File Structure

```
multi_agent/
├── config/
│   ├── agents.yaml          # orgs, model, guardrails, routing — EDIT THIS
│   └── settings.py          # loads yaml + resolves ${ENV_VARS}
├── graph/
│   ├── state.py             # shared AgentState (TypedDict)
│   └── workflow.py          # LangGraph StateGraph — wires all nodes
├── agents/
│   ├── orchestrator.py      # routing decision
│   ├── knowledge_agent.py   # OpenSearch retrieval
│   ├── sql_agent.py         # frame → verify → execute
│   ├── research_agent.py    # google search → read URLs → synthesise
│   └── author_agent.py      # final formatter + PII mask
├── tools/
│   ├── llm.py               # shared ChatBedrock factory
│   ├── opensearch_tool.py   # vector retrieval
│   ├── sql_tools.py         # 3 SQL tools
│   └── search_tools.py      # Google CSE + URL reader
├── guardrails/guardrail.py  # SQL injection + PII masking
├── evaluation/evaluator.py  # trace capture → PostgreSQL + CloudWatch
├── api/websocket_server.py  # FastAPI WebSocket entry point
├── sql/seed.sql             # local test data
├── tests/
│   ├── test_client.py       # local WebSocket tester
│   └── test_google_search.py
├── Dockerfile
├── docker-compose.yml
├── task-definition.json     # ECS Fargate
└── requirements.txt
```

---

## Version Safety (the mismatch problem)

The single most important rule: **upgrade `langgraph`, `langchain-core`, and `langchain-aws` together, never in isolation.** The pinned, verified-compatible set (June 2026):

| Package | Version | Notes |
|---------|---------|-------|
| langgraph | 1.2.4 | pulls checkpoint/prebuilt/sdk automatically |
| langchain-core | 1.4.3 | major-aligned with langgraph 1.x |
| langchain-aws | 1.5.0 | provides ChatBedrock |

We deliberately do **not** pin `langgraph-checkpoint`, `langgraph-prebuilt`, or `langgraph-sdk` — letting `langgraph` resolve its own sub-dependencies is what prevents mismatch errors. Verified with `pip check`: zero conflicts.

---

## Phase 1 — Local Setup & Test (do this first)

### 1A. Prerequisites
- The RAG pipeline OpenSearch domain already running (we reuse its index)
- AWS credentials configured locally (`aws configure`)
- Bedrock model access enabled for Claude 3.5 Sonnet + Titan V2
- A Google Custom Search API key + CSE ID ([get one here](https://developers.google.com/custom-search/v1/overview))

### 1A-i. Google Custom Search Setup

**Step 1 — Create a Google API Key**

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or select an existing one).
3. Navigate to **APIs & Services → Library**.
4. Search for and enable **Custom Search API**.
5. Go to **APIs & Services → Credentials**.
6. Click **Create Credentials → API Key**.
7. Copy the generated API key.

```
GOOGLE_API_KEY=AIzaSyxxxxxxxxxxxxxxxxxxxx
```

**Step 2 — Create a Custom Search Engine (CSE ID)**

1. Open [Programmable Search Engine](https://programmablesearchengine.google.com/)
2. Click **Add**.
3. Enter a website (e.g. `google.com`) temporarily as the site to search.
4. Click **Create**.
5. Open the search engine settings.
6. Under **Search the entire web**, enable the option.
7. Copy the **Search Engine ID** (also called `CX`).

```
GOOGLE_CSE_ID=1234567890abcdefg
```

Add both values to your `.env` file before running the server.

---

### 1B. Install
```bash
cd multi_agent
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 1C. Configure
```bash
cp .env.example .env
# Edit .env — fill in OPENSEARCH_HOST, Google keys.
# For local Postgres, the docker-compose overrides POSTGRES_* automatically.
```

### 1D. Edit your organizations
Open `config/agents.yaml` and add the org names the Knowledge Brain agent should recognise:
```yaml
organizations:
  - name: "OTB"
    aliases: ["otb", "on the beach"]
```

### 1E. Run locally with Docker Compose (recommended)
This spins up a local PostgreSQL (seeded with test data) + the API:
```bash
docker-compose up --build
```

### 1F. Test with the WebSocket client
In another terminal:
```bash
# SQL Agent (data question)
python tests/test_client.py "How many orders were placed yesterday?"

# Knowledge Brain (org mention)
python tests/test_client.py "What does OTB's runbook say about incident response?"

# Research Agent (general knowledge)
python tests/test_client.py "What are the latest AI agent frameworks in 2026?"

# Guardrail test (should be blocked)
python tests/test_client.py "DROP TABLE orders;"
```

You'll see streamed progress events for each, ending in a final response.

### 1G. Run without Docker (pure Python)
```bash
# Point POSTGRES_HOST at your RDS in .env first
uvicorn api.websocket_server:app --host 0.0.0.0 --port 8000 --reload
```

---

## Phase 2 — Push to ECR

```bash
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export AWS_REGION=us-east-1

# Create ECR repo (once)
aws ecr create-repository --repository-name multi-agent-api --region $AWS_REGION

# Login, build, push
aws ecr get-login-password --region $AWS_REGION \
  | docker login --username AWS --password-stdin \
    $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

docker build --platform linux/amd64 -t multi-agent-api .
docker tag multi-agent-api:latest \
  $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/multi-agent-api:latest
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/multi-agent-api:latest
```

---

## Phase 3 — Store Secrets

The task definition pulls secrets from AWS Secrets Manager (never hardcode them):
```bash
aws secretsmanager create-secret --name multi-agent/postgres-password \
  --secret-string "your-rds-password"
aws secretsmanager create-secret --name multi-agent/google-api-key \
  --secret-string "your-google-api-key"
aws secretsmanager create-secret --name multi-agent/google-cse-id \
  --secret-string "your-cse-id"
```

---

## Phase 4 — IAM Task Role

The container needs permissions for Bedrock, OpenSearch, RDS, and Secrets Manager:
```bash
aws iam create-role --role-name multi-agent-task-role \
  --assume-role-policy-document '{
    "Version":"2012-10-17",
    "Statement":[{"Effect":"Allow","Principal":{"Service":"ecs-tasks.amazonaws.com"},"Action":"sts:AssumeRole"}]
  }'

aws iam put-role-policy --role-name multi-agent-task-role \
  --policy-name multi-agent-policy \
  --policy-document '{
    "Version":"2012-10-17",
    "Statement":[
      {"Effect":"Allow","Action":["bedrock:InvokeModel"],"Resource":"*"},
      {"Effect":"Allow","Action":["es:ESHttpGet","es:ESHttpPost"],"Resource":"arn:aws:es:us-east-1:ACCOUNT_ID:domain/rag-vector-domain/*"},
      {"Effect":"Allow","Action":["secretsmanager:GetSecretValue"],"Resource":"arn:aws:secretsmanager:us-east-1:ACCOUNT_ID:secret:multi-agent/*"},
      {"Effect":"Allow","Action":["logs:CreateLogGroup","logs:CreateLogStream","logs:PutLogEvents"],"Resource":"*"}
    ]
  }'
```

The execution role also needs Secrets Manager access to inject the secrets:
```bash
aws iam attach-role-policy --role-name ecsTaskExecutionRole \
  --policy-arn arn:aws:iam::aws:policy/SecretsManagerReadWrite
```

---

## Phase 5 — Deploy to ECS

```bash
# Register task definition (edit ACCOUNT_ID + endpoints in task-definition.json first)
aws ecs register-task-definition --cli-input-json file://task-definition.json

# Create cluster (if not reusing the RAG pipeline cluster)
aws ecs create-cluster --cluster-name multi-agent-cluster
```

### WebSocket needs an Application Load Balancer
WebSocket connections are long-lived, so you need an ALB with the target group configured for it:
```bash
# The ALB target group health check path:
#   /health   (the FastAPI health endpoint)
#
# Key ALB settings for WebSocket:
#   - Protocol: HTTP (ALB upgrades to ws automatically)
#   - Idle timeout: raise to 300s+ (default 60s drops long connections)
#   - Stickiness: enable (keeps a client on the same task)
```

Create the service behind the ALB:
```bash
aws ecs create-service \
  --cluster multi-agent-cluster \
  --service-name multi-agent-service \
  --task-definition multi-agent-task \
  --desired-count 2 \
  --launch-type FARGATE \
  --load-balancers "targetGroupArn=arn:aws:elasticloadbalancing:...:targetgroup/multi-agent-tg/xxx,containerName=multi-agent-api,containerPort=8000" \
  --network-configuration "awsvpcConfiguration={
    subnets=[subnet-xxx,subnet-yyy],
    securityGroups=[sg-xxx],
    assignPublicIp=ENABLED
  }"
```

Angular connects to: `wss://your-alb-dns-name/ws/agent`

---

## Phase 6 — Verify

```bash
aws logs tail /ecs/multi-agent-api --follow
```

Filter evaluation traces in CloudWatch Logs Insights:
```
fields @timestamp, @message
| filter @message like /EVAL_TRACE/
| sort @timestamp desc
```

---

## Evaluation Data

Every request writes a row to the `agent_traces` table in RDS:

| Column | Description |
|--------|-------------|
| trace_id | UUID |
| session_id | client session |
| user_query | original question |
| selected_agent | which agent ran |
| routing_reason | why the orchestrator chose it |
| agent_content | raw agent output |
| final_response | post-PII-mask response |
| guardrail_flags | array, e.g. {pii_masked:email} |
| latency_ms | JSONB per-stage timing |
| created_at | timestamp |

Query for evaluation:
```sql
SELECT selected_agent, COUNT(*), AVG((latency_ms->>'author')::int) AS avg_author_ms
FROM agent_traces
GROUP BY selected_agent;
```

The same data lands in CloudWatch as `EVAL_TRACE` JSON lines, so you can evaluate from either sink.

---

## Angular Client Contract

Connect and send:
```typescript
const ws = new WebSocket('wss://your-alb/ws/agent');
ws.onopen = () => ws.send(JSON.stringify({
  session_id: 'user-123',
  query: 'How many orders yesterday?'
}));
ws.onmessage = (e) => {
  const msg = JSON.parse(e.data);
  switch (msg.event) {
    case 'agent_selected':  // show which agent
    case 'agent_progress':  // show progress spinner text
    case 'agent_complete':  // render msg.data.response
    case 'turn_complete':   // re-enable input
  }
};
```
