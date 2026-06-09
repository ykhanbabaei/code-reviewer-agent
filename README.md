
# 🤖 Code Reviewer Agent

> A production-grade AI system that automatically reviews GitHub Pull Requests using LLMs, static analysis tools, and agentic workflows built with LangGraph.

This system acts as an **intelligent CI reviewer**, capable of analyzing code quality, detecting security vulnerabilities, and generating actionable PR feedback in real time.

It is designed with **scalability, observability, fault tolerance, and streaming-first architecture**.

---

# 🚀 Tech Stack

### 🧠 AI / Agent Layer

* **LangGraph** – stateful agent orchestration (fan-out/fan-in, checkpoints, retries)
* **LangChain** – LLM integration, tool calling, structured outputs
* **OpenAI / Claude / Local LLMs (Ollama, vLLM)**

---

### ⚡ Backend

* **FastAPI** – async API gateway + GitHub webhook receiver
* **Uvicorn** – ASGI server for high-performance async execution

---

### 🔄 Streaming & Async Architecture

* **Async Python (asyncio)**
* **Streaming LLM responses (token-level / chunk-level)**
* **Background task execution (non-blocking webhook handling)**
* Optional:

  * Celery / Redis Queue for distributed workloads

---

### 🧪 Code Analysis Tools

* Bandit (security scanning)
* Semgrep (rule-based static analysis)
* Ruff / Pylint (linting & quality checks)

---

### 📊 Observability & Monitoring

* **LangSmith**

  * Trace LLM calls
  * Track latency per node
  * Monitor token usage & cost
  * Debug agent execution graphs
* Structured logging (JSON logs)
* Metrics-ready architecture (Prometheus-compatible design)

---

### 🧱 Infrastructure

* Docker (containerized deployment)
* PostgreSQL (state + checkpoint persistence)
* Redis (queueing + caching)
* GitHub API integration

---

# 🏗️ System Architecture

```text
GitHub PR Event
        ↓
FastAPI Webhook (async, non-blocking)
        ↓
LangGraph Orchestrator (state machine agent)
        ↓
Fan-out File Analysis (parallel execution)
        ↓
LLM + Static Analysis Tools
        ↓
Streaming Aggregation Layer
        ↓
LangSmith Observability Trace
        ↓
GitHub PR Comment + Status Update
```

---

# ⚙️ Key Features

## ⚡ Streaming-Based Async Processing

* Non-blocking PR ingestion via FastAPI
* Async file-level analysis
* Streaming LLM responses for incremental processing
* Real-time partial result aggregation

---

## 🧠 Agentic Multi-Step Reasoning

* File-level + repo-level reasoning
* Tool-augmented LLM execution
* Reflection loop (self-review of findings)
* Context-aware issue prioritization

---

## 🔁 Fault Tolerant Design

* LangGraph checkpointing (resume execution after failure)
* Retry-safe node execution
* Idempotent GitHub webhook processing
* Graceful degradation (Workflow fallbacks, reduced analysis on failure)

---

## 📊 Observability with LangSmith

* Full traceability of:

  * Each LangGraph node
  * LLM prompts and outputs
  * Tool calls (Bandit/Semgrep/etc.)
* Performance metrics:

  * Latency per PR
  * Token usage per file
  * Cost estimation per run
* Debuggable execution graph per PR

---

## 🐳 Fully Dockerized

* Production-ready container setup
* Multi-service support (API + worker + DB + Redis)
* Environment-based configuration

---

# 📦 Project Structure

```text
code-reviewer-agent/
│
├── app/
│   ├── api/                  # FastAPI routes (webhooks, status API)
│   ├── agent/                # LangGraph workflow definition
│   │   ├── graph.py
│   │   ├── nodes.py
│   │   ├── state.py
│   │   └── tools.py
│   │
│   ├── services/            # GitHub + LLM + orchestration services
│   ├── analyzers/           # Bandit, Semgrep, Ruff integrations
│   ├── prompts/             # Prompt templates
│   ├── observability/       # LangSmith + logging config
│   └── utils/
│
├── tests/
├── docker-compose.yml
├── Dockerfile
├── main.py
├── requirements.txt
└── README.md
```

---

# ⚙️ Setup and Installation

## 1. Clone repository

```bash
git clone https://github.com/your-org/code-reviewer-agent.git
cd code-reviewer-agent
```

---

## 2. Create virtual environment

```bash
python -m venv .venv
source .venv/bin/activate   # Linux / Mac
.venv\Scripts\activate      # Windows
```

---

## 3. Install dependencies

```bash
pip install -r requirements.txt
```

---

## 4. Environment configuration

Create `.env`:

```env
OPENAI_API_KEY=your_key

DATABASE_URL=postgresql://user:password@localhost:5432/reviewer
REDIS_URL=redis://localhost:6379

LANGSMITH_API_KEY=your_langsmith_key
LANGSMITH_PROJECT=code-reviewer-agent
```

---

## 5. Run locally

```bash
uvicorn app.main:app --reload
```

---

# 🐳 Deployment (Production Ready)

## Option 1: Docker (Recommended)

### Build image

```bash
docker build -t code-reviewer-agent .
```

---

### Run container

```bash
docker run -p 8000:8000 --env-file .env code-reviewer-agent
```

---

## Option 2: Docker Compose (Full Stack)

```yaml
version: "3.9"

services:
  api:
    build: .
    ports:
      - "8000:8000"
    env_file:
      - .env
    depends_on:
      - redis
      - postgres

  worker:
    build: .
    command: python worker.py
    env_file:
      - .env
    depends_on:
      - redis
      - postgres

  redis:
    image: redis:7

  postgres:
    image: postgres:15
```

---

## Option 3: Cloud Deployment

Recommended:

* AWS ECS / Fargate
* Google Cloud Run
* Azure Container Apps
* Fly.io (lightweight deployments)

---

### Production Best Practices

* Use worker-based architecture for LangGraph execution
* Enable PostgreSQL checkpointing
* Use Redis for queueing + deduplication
* Enable HTTPS for GitHub webhooks
* Configure autoscaling for worker nodes

---

# 🧠 How to Use

## 1. Configure GitHub Webhook

Go to:

```
GitHub → Settings → Webhooks → Add webhook
```

### Configuration:

| Field        | Value                                    |
| ------------ | ---------------------------------------- |
| Payload URL  | `https://your-domain.com/webhook/github` |
| Content type | `application/json`                       |
| Events       | Pull Requests                            |

---

## 2. Trigger a PR Review

Simply open or update a pull request:

```text
GitHub automatically sends webhook → system starts analysis
```

---

## 3. What happens internally

1. FastAPI receives webhook (async, non-blocking)
2. PR diff is fetched from GitHub API
3. LangGraph orchestrates analysis pipeline
4. Files processed in parallel (fan-out)
5. LLM + static tools analyze code
6. Streaming aggregation builds final report
7. LangSmith logs full execution trace
8. GitHub PR comment is posted

---

## 4. View results

### In GitHub PR:

* Automated review comment
* Severity-ranked issues
* Suggested fixes

### In CI status:

* Pass / Fail / Warning

---

## 5. API Endpoints

### Triggered internally (webhook)

```http
POST /webhook/github
```

---

### Check status

```http
GET /review/{review_id}/status
```

---

### Cancel review

```http
POST /review/{review_id}/cancel
```

---

# 🔐 Security

* GitHub webhook signature validation (HMAC SHA-256)
* Prompt injection mitigation via diff-only context isolation
* No execution of user-provided code
* Secrets stored in environment variables / vault
* Optional self-hosted LLM support for air-gapped environments

---

# 📊 Observability

Powered by **LangSmith**

You can monitor:

* Full LangGraph execution traces
* Node-level latency
* LLM cost & token usage
* Tool execution logs
* Failure points in workflows

---

# 🔁 Fault Tolerance Strategy

* LangGraph checkpointing (resume interrupted workflows)
* Retry policies per node
* Idempotent webhook handling
* Graceful fallback to lightweight analysis models
* Dead-letter queue for failed PRs

---

# 📌 Future Enhancements

* Auto-fix PR generation (AI patch suggestions)
* Multi-agent reviewer system (security / performance / style agents)
* Slack + Teams integration
* PR risk scoring dashboard
* Continuous learning from developer feedback

---


# How to use
After deployment, The Agent is accessible in `http://localhost:8000`.
Sample curl request to trigger a review:

```bash
curl --no-buffer -X POST "http://localhost:8000/review" \
-H "Content-Type: application/json" \
-d '{  "user_name": "github_user",  "repository": "github_repository",        "pull_number": 2}'
```

# Environment Variables

   ```bash
   OPENAI_API_KEY="your openai api key"
   ```
  Optionally if you want to enable langsmith tracing, add the following environment variable:
   ```bash
   LANGSMITH_TRACING="langsmith is enabled or not"
   LANGSMITH_ENDPOINT=https://eu.api.smith.langchain.com
   LANGSMITH_API_KEY="api key for langsmith"
   LANGSMITH_PROJECT="Langgraph"
   ```
