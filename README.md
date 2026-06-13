
# 🤖 Code Reviewer Agent

> An AI system that reviews GitHub Pull Requests using LLMs, static analysis tools, and agentic workflows built with LangGraph.

This system acts as an **intelligent CI reviewer**, capable of analyzing code quality, detecting security vulnerabilities, and generating actionable PR feedback in real time.

It is designed with **scalability, observability, fault tolerance, and streaming-first architecture**.

---

# 🚀 Tech Stack

### 🧠 AI / Agent Layer

* **LangGraph** – stateful agent orchestration (fan-out/fan-in, checkpoints, retries)
* **LangChain** – LLM integration, tool calling, structured outputs
* **OpenAI / Hugging Face**

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
│   ├── prompts/             # Prompt templates
│   ├── observability/       # LangSmith + logging config
│   ├── main.py              # FastAPI application entry point
│   ├── config.py            # App config and environment variable loading
│
├── tests/
├── docker-compose.yml
├── Dockerfile
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
OPENAI_API_KEY=your_key # Required for Model calls
HF_TOKEN="your_key" # Required for embedding calls if using HuggingFace models
QDRANT_STORAGE_PATH="/app/qdrant_code_reviewer_db" # can use this path for dockerized deployment
LOG_FILE_PATH="/app/code_reviewer.log"  # can use this path for dockerized deployment
LANGSMITH_TRACING=true #optional for monitoring
LANGSMITH_ENDPOINT=https://eu.api.smith.langchain.com    #optional for monitoring
LANGSMITH_API_KEY=api_key   #optional for monitoring
LANGSMITH_PROJECT="Langgraph" #optional for monitoring
REDIS_CACHE_URL="redis://@redis:6379/0" #optional for enabling cache
POSTGRES_URL="postgresql://postgres:postgres@postgres:5432/langgraph" #optional for storing state data
MLFLOW_TRACKING_URI="http://mlflow:5000/"  # optional
MLFLOW_EXPERIMENT="langgraph"   # optional
```

---

## 5. Run locally

```bash
uvicorn app.main:app --reload
```

---

# 🐳 Deployment (Production Ready)

## Docker 

### Build image and deploy

```bash
docker-compose up
```

---


# 🧠 How to Use

After deployment, The Agent is accessible in `http://localhost:8000`.

Sample curl request to trigger a review:

```bash
curl --no-buffer -X POST "http://localhost:8000/review" \
-H "Content-Type: application/json" \
-d '{  "user_name": "github_user", "repository": "github_repository", "pull_number": 2}'
```

For providing repository source code as RAG context data for better code review, call following api

```bash
curl -X POST 'http://localhost:8000/embed' \
-H 'Content-Type: application/json' \
-d '{  "user_name": "github_user",  "github_repository": "ebf-employee-management",   "token":"access token" }'
```


## What happens internally

1. FastAPI receives code review request (async, non-blocking)
2. PR diff is fetched from GitHub API
3. LangGraph orchestrates analysis pipeline
4. Files processed in parallel (fan-out)
5. LLM + static tools analyze code
6. Streaming aggregation builds final report
7. LangSmith logs full execution trace
8. API returns response with code review result

---

## 5. API Endpoints

### pr code review call

```http
POST /review
```

### embedding source code

```http
POST /embed
```

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
* Connect to Github Webhooks
* Send notification email to the user
