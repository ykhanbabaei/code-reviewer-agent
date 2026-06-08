# code-reviewer-agent

A lightweight, stream-first code-review assistant service built with FastAPI. This project is designed for high-throughput, low-latency workloads and production-readiness: async stream-based processing, Dockerized deployment, integrated monitoring via LangSmith, robust logging, and fault-tolerant patterns.

Key features
- Stream-based async processing (asyncio + FastAPI streaming endpoints)
- Dockerized with Dockerfile and docker-compose for local and containerized deployments
- FastAPI-powered HTTP API (async endpoints, streaming responses)
- LangSmith integration for monitoring, metrics, and run logging
- Structured logging (console + file, configurable level)
- Fault-tolerance: retries, backoff, graceful shutdown, and idempotency patterns

Quick start (local)
1. Create a virtual environment and install dependencies:
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
2. Run the API server:
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
3. Open http://localhost:8000/docs for the OpenAPI UI.

Docker
- Build and run with docker-compose:
  docker-compose up --build
- The Dockerfile produces a lightweight container running uvicorn. Use environment variables (see Configuration) to provide secrets and runtime options.

Stream-based async design
- The service uses asyncio for concurrency and prefers streaming when handling large inputs or long-running operations.
- FastAPI streaming endpoints return async generators so clients can start receiving partial results immediately.
- Internal processing is implemented with async queues and background tasks so work is processed continuously without blocking request handlers.
- Benefits: lower memory footprint, improved latency for long-running operations, backpressure-friendly.

FastAPI details
- Endpoints are declared async and use pydantic models for validation.
- Streaming endpoints use StreamingResponse with async generators to yield chunks as soon as they are available.
- Health, metrics, and readiness endpoints are exposed for orchestration and monitoring.

LangSmith monitoring and metrics
- LangSmith is used to collect run-level telemetry and structured traces for important operations.
- To enable LangSmith, set the LANGSMITH_API_KEY environment variable. Optionally configure LANGSMITH_PROJECT or LANGSMITH_ENV.
- The integration logs events such as: request start/stop, stream events, errors, processing latency, and custom metrics.
- Example environment variables:
  - LANGSMITH_API_KEY=your_key_here
  - LANGSMITH_PROJECT=code-reviewer-agent

Logging
- The app uses structured logging (JSON-capable format optional) with configurable level via LOG_LEVEL environment variable (default: INFO).
- Logs include request IDs and trace IDs when LangSmith/OpenTelemetry is enabled to correlate logs with traces and runs.
- Configure handlers for console output and optional file rotation for persistent logs.

Fault tolerance and resilience
- Retries: Use exponential backoff (e.g., tenacity) for transient external calls (network, models, APIs).
- Circuit breakers: Protect downstream dependencies by failing fast when a dependency is unhealthy.
- Graceful shutdown: Signal handlers ensure background tasks complete or checkpoint progress before exiting.
- Idempotency and deduplication: Requests that can be retried are handled idempotently or deduplicated by idempotency keys.
- Backpressure: Async queues and bounded worker pools provide natural backpressure to prevent resource exhaustion.

Observability and metrics
- Instrument latency, throughput, success/error counts, and queue depth as metrics.
- LangSmith captures run artifacts and structured events; add Prometheus or OpenTelemetry for additional metric sinks.

Configuration
- Environment variables configure runtime behavior:
  - LOG_LEVEL (default: INFO)
  - LANGSMITH_API_KEY (optional)
  - HOST, PORT
  - WORKER_COUNT, QUEUE_SIZE
- Secrets should be provided via environment variables or secret stores; never commit them to source.

Recommended production practices
- Run behind a process manager or container orchestrator (Docker Compose, Kubernetes).
- Use HTTPS, a reverse proxy (NGINX), and configure resource limits for containers.
- Centralize logs and telemetry in an observability backend (LangSmith + Prometheus/Grafana or vendor of choice).
- Configure liveness/readiness probes for container orchestration.

Folder layout (example)
- app/ - application package (FastAPI app, endpoints, background workers)
- Dockerfile - container image definition
- docker-compose.yml - local orchestration
- requirements.txt - Python dependencies
- tests/ - unit and integration tests

Extending monitoring
- Add custom LangSmith events for important domain actions (e.g., review.completed, review.error).
- Record contextual metadata: request id, user id, repo, file path, and metrics such as token usage or processing time.

Contributing
- Fork, create a branch, add tests for new behavior, and open a pull request.
- Keep changes small and include tests for any bugfix or feature.

License
- See LICENSE file for license details (if present).

Support
- For questions or contributions, open an issue in this repository.

