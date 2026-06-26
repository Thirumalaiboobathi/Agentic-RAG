## 📦 Project Repositories

| Repository | Description |
|------------|-------------|
| **Backend** | Multi-Agent AI backend, LangGraph orchestration, Agentic RAG, FastAPI, AWS deployment |
| **Frontend** | React + Vite user interface deployed on Netlify |

# 🏥 Enterprise Multi-Agent Clinical AI Assistant

<p align="center">

Enterprise-grade Healthcare AI platform built with <b>LangGraph</b>, <b>Amazon Bedrock</b>, <b>Amazon Titan Embeddings</b>, <b>Amazon OpenSearch Serverless</b>, and a cloud-native AWS architecture following modern <b>LLMOps</b> practices.

</p>

<p align="center">

![Python](https://img.shields.io/badge/Python-3.12-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-WebSockets-green)
![React](https://img.shields.io/badge/React-18-blue)
![LangGraph](https://img.shields.io/badge/LangGraph-Multi--Agent-orange)
![Amazon Bedrock](https://img.shields.io/badge/Amazon-Bedrock-FF9900)
![OpenSearch](https://img.shields.io/badge/OpenSearch-Serverless-blue)
![Docker](https://img.shields.io/badge/Docker-Containerized-blue)
![AWS ECS](https://img.shields.io/badge/Amazon-ECS%20Fargate-orange)

</p>

---

# 📖 Overview

This project demonstrates how to build a **production-oriented Enterprise Healthcare AI Platform** using a **Multi-Agent Architecture**, **Agentic Retrieval-Augmented Generation (RAG)**, and **AWS cloud-native services**.

Unlike traditional chatbot implementations where every request is processed through a single prompt, this platform intelligently routes user queries to specialized AI agents responsible for different clinical domains. Each agent performs semantic retrieval using **Amazon Titan Embeddings** and **Amazon OpenSearch Serverless** before invoking **Amazon Bedrock** to generate grounded, context-aware responses.

The platform is designed around **LLMOps principles**, incorporating secure request validation, AI guardrails, observability, containerized deployment, and scalable AWS infrastructure suitable for enterprise workloads.

---

# ✨ Key Features

- 🤖 Multi-Agent AI Architecture using LangGraph
- 🧠 Intelligent Query Routing
- 🔍 Agentic Retrieval-Augmented Generation (RAG)
- 📚 Amazon Titan Embeddings V2
- ⚡ Amazon OpenSearch Serverless Vector Search
- 🏥 Specialized Clinical AI Agents
- 💬 Real-time WebSocket Streaming
- 🛡️ Input & Output Guardrails
- 🚫 Prompt Injection Detection
- 📦 Docker Containerization
- ☁️ Amazon ECS Fargate Deployment
- 🌍 Amazon CloudFront Distribution
- ⚖️ Application Load Balancer
- 📈 Amazon CloudWatch Observability
- 📝 PostgreSQL Trace Logging
- 🚀 Cloud-native Enterprise LLMOps Pipeline

---

# 🏗️ High-Level Architecture

> Replace the image below with your generated architecture diagram.

<p align="center">

![Architecture](images/system-architecture.png)

</p>

---

# 🔄 End-to-End LLMOps Pipeline

> Replace the image below with your generated LLMOps pipeline diagram.

<p align="center">

![LLMOps Pipeline](images/llmops-pipeline.png)

</p>

---

# ⚙️ System Workflow

```text
User Query
     │
     ▼
React Frontend
     │
     ▼
Amazon CloudFront
     │
     ▼
Application Load Balancer
     │
     ▼
FastAPI WebSocket Server
     │
     ▼
Input Guardrails
     │
     ▼
LangGraph Orchestrator
     │
     ▼
Specialized Clinical Agent
     │
     ▼
Amazon Titan Embeddings
     │
     ▼
Amazon OpenSearch Serverless
     │
     ▼
Amazon Bedrock
     │
     ▼
Output Guardrails
     │
     ▼
Validated AI Response
```

---

# 🤖 Multi-Agent Architecture

The platform follows a **specialized agent architecture**, where each AI agent is responsible for a specific clinical domain instead of relying on a single monolithic prompt.

This approach provides:

- Better reasoning accuracy
- Reduced hallucinations
- Cleaner prompt engineering
- Independent scalability
- Easier maintenance
- Modular AI workflows
- Domain-specific retrieval strategies

The **LangGraph Orchestrator** acts as the central decision-making layer, routing requests to the most appropriate specialist agent based on user intent.

# 🧠 Specialized AI Agents

Rather than relying on a single prompt to handle every healthcare request, the platform follows a **Multi-Agent Architecture**, where each AI agent specializes in a particular clinical domain. The **LangGraph Orchestrator** analyzes user intent and delegates each request to the most appropriate specialist agent.

| AI Agent | Responsibility |
|-----------|----------------|
| 🧠 Orchestrator Agent | Intent classification, workflow routing, and state management |
| 🩺 Patient History Agent | Medical history, chronic conditions, diagnoses, allergies |
| 📅 Appointment Agent | Appointment scheduling, visit history, physician availability |
| 💊 Pharmacy Agent | Medication history, prescriptions, dosage information |
| 📋 Clinical Notes Agent | SOAP notes, consultation summaries, physician documentation |

### Why Multi-Agent?

Unlike a monolithic chatbot, specialized agents provide:

- Better domain-specific reasoning
- Smaller and more focused prompts
- Reduced hallucinations
- Improved maintainability
- Independent scalability
- Easier feature expansion

---

# 🔍 Agentic Retrieval-Augmented Generation (RAG)

The platform uses **Agentic RAG**, where each specialist agent retrieves contextual healthcare information before invoking the foundation model.

Instead of relying solely on the model's pre-trained knowledge, every response is grounded using enterprise data retrieved through semantic search.

## Retrieval Pipeline

```text
User Query
      │
      ▼
Titan Embeddings
      │
      ▼
Vector Generation
      │
      ▼
Amazon OpenSearch Serverless
      │
      ▼
Top-K Similar Clinical Documents
      │
      ▼
Amazon Bedrock
      │
      ▼
Grounded Clinical Response
```

> Replace this section with your generated RAG architecture image.

<p align="center">

![Agentic RAG](images/rag-pipeline.png)

</p>

### Why Agentic RAG?

Unlike traditional chatbots that rely solely on foundation models, Agentic RAG ensures that every response is generated using the most relevant enterprise knowledge.

Benefits include:

- Semantic document retrieval
- Context-aware reasoning
- Reduced hallucinations
- Improved factual accuracy
- Better explainability
- Enterprise knowledge grounding

---

# 🚀 Enterprise LLMOps Pipeline

Building enterprise AI applications requires significantly more than prompting a language model.

This project follows a complete **LLMOps pipeline** that validates requests, orchestrates AI workflows, retrieves contextual information, performs inference, validates outputs, and streams responses in real time.

```text
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
Amazon OpenSearch Serverless
      │
      ▼
Context Retrieval
      │
      ▼
Amazon Bedrock
      │
      ▼
Response Generation
      │
      ▼
Output Guardrails
      │
      ▼
Validated AI Response
      │
      ▼
WebSocket Streaming
      │
      ▼
React Frontend
```

> Replace this section with your generated LLMOps pipeline image.

<p align="center">

![LLMOps](images/llmops.png)

</p>

---

# ☁️ AWS Cloud-Native Deployment

The platform follows a fully containerized deployment architecture using AWS managed services.

```text
Developer

      │

      ▼

GitHub Repository

      │

      ▼

Docker Build

      │

      ▼

Amazon Elastic Container Registry

      │

      ▼

Amazon ECS Fargate

      │

      ▼

Application Load Balancer

      │

      ▼

Amazon CloudFront

      │

      ▼

Global Users
```

### AWS Services

| Service | Purpose |
|----------|---------|
| Amazon Bedrock | Foundation Model Inference |
| Amazon Titan Embeddings | Semantic Embeddings |
| Amazon OpenSearch Serverless | Vector Database |
| Amazon ECS Fargate | Container Orchestration |
| Amazon Elastic Container Registry | Docker Image Storage |
| Application Load Balancer | Traffic Distribution & WebSocket Support |
| Amazon CloudFront | HTTPS, CDN & Global Delivery |
| Amazon CloudWatch | Logging & Monitoring |
| AWS IAM | Identity & Access Management |

---

# 🛡️ Security & AI Guardrails

Enterprise AI systems require multiple validation layers before and after model inference.

This platform incorporates both **Input Guardrails** and **Output Guardrails** to improve response quality and security.

## Input Validation

- Prompt Injection Detection
- Input Sanitization
- Request Validation
- Malicious Prompt Filtering
- Invalid Character Detection

## Output Validation

- Safe Response Validation
- Response Completeness
- Structured Output Validation
- Response Sanitization
- Clinical Safety Enforcement

This layered approach significantly improves the reliability and trustworthiness of AI-generated responses.

---

# 📊 Observability & Monitoring

Production AI systems require continuous monitoring and traceability.

The platform integrates with **Amazon CloudWatch** and structured trace logging to capture operational metrics throughout the inference lifecycle.

### Captured Metrics

- Agent Selection
- Routing Decisions
- Request Latency
- Retrieval Duration
- Model Inference Time
- WebSocket Events
- Runtime Exceptions
- Container Health
- CloudWatch Logs
- PostgreSQL Trace Logging

The architecture is also designed to support future integration with automated evaluation frameworks for continuous assessment of retrieval quality and response effectiveness.

---

# 📂 Project Structure

This repository contains the **backend services**, AI orchestration, and AWS deployment components for the Enterprise Multi-Agent Clinical AI Assistant.

```text
backend/

│

├── agents/
├── api/
├── config/
├── evaluation/
├── graph/
├── guardrails/
├── models/
├── tools/
├── utils/
├── websocket/
│
├── websocket_server.py
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── README.md
```

> **Note:** The React frontend is maintained in a separate repository and deployed independently on Netlify. Communication between the frontend and backend is performed through secure WebSocket connections.

---

# 🚀 Getting Started

## Clone Repository

```bash
git clone https://github.com/Thirumalaiboobathi/<backend-repository>.git

cd <backend-repository>
```

---

## Create Virtual Environment

```bash
python -m venv .venv
```

Activate

Linux / macOS

```bash
source .venv/bin/activate
```

Windows

```bash
.venv\Scripts\activate
```

---

## Install Dependencies

```bash
pip install -r requirements.txt
```

---

## Configure Environment Variables

Create a `.env` file and configure the required AWS resources.

Example:

```env
AWS_REGION=us-east-1

BEDROCK_MODEL_ID=...

OPENSEARCH_ENDPOINT=...

AWS_ACCESS_KEY_ID=...

AWS_SECRET_ACCESS_KEY=...
```

---

## Start the Backend

```bash
python websocket_server.py
```

The backend starts a FastAPI WebSocket server that communicates with the independently deployed React frontend.

---

# 🐳 Docker Deployment

Build the Docker image

```bash
docker build -t enterprise-clinical-ai .
```

Run the container

```bash
docker run -p 8000:8000 enterprise-clinical-ai
```

---

# ☁️ Production Deployment

The backend is deployed using a cloud-native AWS architecture.

```text
Developer

↓

GitHub

↓

Docker Build

↓

Amazon Elastic Container Registry (ECR)

↓

Amazon ECS Fargate

↓

Application Load Balancer

↓

Amazon CloudFront

↓

Secure WebSocket Endpoint (WSS)

↓

React Frontend (Netlify)

↓

End Users
```

---

# 📈 Future Roadmap

- AI-powered Clinical Decision Support
- Electronic Health Record (EHR) Integration
- HL7 FHIR Support
- Voice-enabled Clinical Assistant
- Multi-language Support
- Automated RAG Evaluation
- LLMOps Dashboard
- AI Feedback Loop
- Multi-region AWS Deployment

---

# 🤝 Contributing

Contributions are welcome.

Feel free to fork this repository, submit issues, or create pull requests that improve the architecture, deployment, or AI capabilities.

---

# ⭐ Support

If you found this project useful, consider giving it a ⭐ on GitHub.

Your support helps the project reach more developers and encourages future improvements.

---
