# Enterprise Multi-Agent Clinical AI Assistant

> Enterprise-grade Healthcare AI platform built using LangGraph, Amazon Bedrock, Titan Embeddings, OpenSearch Serverless, and AWS cloud-native infrastructure.

MiKenko is a production-oriented Multi-Agent Clinical AI Assistant designed to demonstrate modern LLMOps architecture on AWS. The platform intelligently routes clinical queries to specialized AI agents, retrieves contextual medical information through semantic search, validates every request using AI guardrails, and streams real-time responses through WebSockets.

The system is built with scalability, security, observability, and production deployment best practices in mind.

---

## Enterprise Highlights

- Multi-Agent AI Architecture using LangGraph
- Intelligent Query Routing through Orchestrator Agent
- Amazon Bedrock Foundation Models
- Amazon Titan Text Embeddings V2
- Retrieval-Augmented Generation (RAG)
- Amazon OpenSearch Serverless Vector Database
- Real-time WebSocket Communication
- Semantic Search with Vector Embeddings
- Input Guardrails & Prompt Injection Protection
- Output Guardrails & Response Validation
- Clinical Response Safety Validation
- Production-ready Docker Containers
- Amazon ECS Fargate Deployment
- Amazon Elastic Container Registry (ECR)
- Application Load Balancer (ALB)
- Amazon CloudFront Distribution
- CloudWatch Logging & Monitoring
- Stateless Microservice Architecture

---

# System Architecture

```
                                React + Vite Frontend
                                         │
                                         │ HTTPS
                                         ▼
                               Amazon CloudFront CDN
                                         │
                                         ▼
                          Application Load Balancer (ALB)
                                         │
                                   WebSocket API
                                         │
                                         ▼
                          FastAPI WebSocket Server (ECS)
                                         │
                               Input Guardrails
                                         │
                                         ▼
                            LangGraph Orchestrator
                                         │
         ┌──────────────┬───────────────┬───────────────┬───────────────┐
         │              │               │               │
         ▼              ▼               ▼               ▼
 Patient History   Appointment      Pharmacy      Clinical Notes
      Agent            Agent          Agent            Agent
         │              │               │               │
         └──────────────┴───────────────┴───────────────┘
                                         │
                                         ▼
                             Titan Embeddings V2
                                         │
                                         ▼
                     Amazon OpenSearch Serverless
                                         │
                                         ▼
                         Amazon Bedrock Foundation Model
                                         │
                               Output Guardrails
                                         │
                                         ▼
                             Validated AI Response
                                         │
                                         ▼
                              React WebSocket Client
```

---

# Multi-Agent Workflow

1. User submits a clinical query.
2. Request reaches FastAPI through WebSocket.
3. Input Guardrails validate the request.
4. LangGraph Orchestrator determines the appropriate specialist agent.
5. Selected agent retrieves contextual healthcare information.
6. Titan Embeddings generate semantic vectors.
7. OpenSearch Serverless performs similarity search.
8. Amazon Bedrock generates the response.
9. Output Guardrails validate and sanitize the response.
10. Final response is streamed back to the client in real time.

---

# Specialized AI Agents

| Agent | Responsibility |
|--------|----------------|
| Orchestrator Agent | Intelligent routing of user requests |
| Patient History Agent | Medical history and chronic condition retrieval |
| Appointment Agent | Patient appointments and visit history |
| Pharmacy Agent | Medication and prescription management |
| Clinical Notes Agent | Clinical documentation and SOAP note summarization |

---

# LLMOps Pipeline

```
User Query
      │
      ▼
Input Validation
      │
      ▼
Prompt Injection Detection
      │
      ▼
LangGraph Orchestrator
      │
      ▼
Specialized Clinical Agent
      │
      ▼
Titan Embeddings
      │
      ▼
OpenSearch Vector Retrieval
      │
      ▼
Amazon Bedrock
      │
      ▼
Output Validation
      │
      ▼
Guardrails
      │
      ▼
Validated Clinical Response
```

---

# Technology Stack

## Frontend

- React
- Vite
- JavaScript
- HTML5
- CSS3
- WebSocket API

## Backend

- Python
- FastAPI
- LangGraph
- LangChain

## AI & LLM

- Amazon Bedrock
- Amazon Titan Embeddings V2
- Retrieval-Augmented Generation (RAG)

## Vector Search

- Amazon OpenSearch Serverless

## Cloud Infrastructure

- Amazon ECS Fargate
- Amazon Elastic Container Registry (ECR)
- Application Load Balancer
- Amazon CloudFront
- AWS IAM
- Amazon CloudWatch

## DevOps

- Docker
- Git
- GitHub

---

# Security & Guardrails

MiKenko follows production-grade AI safety practices through multiple validation layers.

### Input Protection

- Prompt Injection Detection
- Input Validation
- Malicious Request Filtering
- Request Sanitization

### Output Protection

- Response Validation
- AI Guardrails
- Safe Response Enforcement
- Structured Response Validation

---

# Production Deployment

The application follows an enterprise cloud-native deployment architecture.

```
Developer

↓

GitHub Repository

↓

Docker Build

↓

Amazon ECR

↓

Amazon ECS Fargate

↓

Application Load Balancer

↓

Amazon CloudFront

↓

Global End Users
```

---

# Project Structure

```
MiKenko/
│
├── frontend/
│   ├── src/
│   ├── public/
│   └── package.json
│
├── backend/
│   ├── agents/
│   ├── graph/
│   ├── api/
│   ├── tools/
│   ├── config/
│   ├── guardrails/
│   ├── evaluation/
│   └── websocket_server.py
│
├── deployment/
│
├── Dockerfile
│
├── docker-compose.yml
│
├── requirements.txt
│
└── README.md
```

---

# Key Capabilities

- Enterprise Multi-Agent AI Architecture
- Real-time Clinical AI Assistant
- Retrieval-Augmented Generation (RAG)
- Production LLMOps Pipeline
- Semantic Vector Search
- Secure AI Guardrails
- Cloud-native AWS Deployment
- Highly Scalable Microservice Architecture
- Real-time WebSocket Communication
- Production-ready Containerized Deployment

---

# Future Enhancements

- Electronic Health Record (EHR) Integration
- FHIR Compliance
- Voice-enabled Clinical Assistant
- Multi-language Medical Support
- AI-powered Clinical Decision Support
- Observability Dashboard & Analytics

---

