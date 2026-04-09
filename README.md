---
title: Incident Commander Env
emoji: 🚨
colorFrom: red
colorTo: yellow
sdk: docker
sdk_version: "1.0"
app_file: app.py
pinned: false
tags:
  - openenv
---

# Incident Commander Environment 🚨

> **An OpenEnv RL environment where AI agents act as on-call SRE engineers — triaging, diagnosing, and resolving real production incidents.**

Inspired by real runbooks at MAANG companies. Not a toy. Not a game. This is the kind of agentic reasoning task that Meta, Google, and Amazon actually need agents to be good at.

---

## What Makes This Different

Most RL environments test _what_ an agent does. This one also tests _why_.

**Two novel capabilities not found in any existing OpenEnv benchmark:**

### 🧠 Reasoning Trace Evaluator

Every action includes an optional `reasoning` field. The environment scores the agent's explanation against a keyword rubric derived from real SRE runbooks — rewarding agents that can articulate _why_ they're investigating a particular signal, not just agents that stumble onto the right action sequence.

```json
{
  "action_type": "check_metrics",
  "reasoning": "HikariPool exhaustion seen in logs — need metrics to confirm pool saturation and waiting thread count",
  "parameters": {}
}
```

### 💾 Cross-Incident Memory

Resolved incidents are stored in a persistent `IncidentMemoryStore`. On each new episode, the environment injects relevant past incidents into the observation. Agents that reuse prior knowledge — identifying root cause faster because they've seen a similar pattern before — earn a memory bonus reward. This tests **in-context meta-learning across episodes**, directly analogous to how senior SREs operate.

```json
"past_similar_incidents": [
  {
    "incident_id": "INC-001",
    "root_cause": "database_connection_pool_exhausted",
    "fix": "increase_connection_pool",
    "tags": ["database", "latency", "java"]
  }
]
```

---

## Tasks

| Task     | Incident                                                                                      | Severity | Max Steps | Difficulty |
| -------- | --------------------------------------------------------------------------------------------- | -------- | --------- | ---------- |
| `easy`   | Payment Service High Latency — HikariPool DB connection pool exhaustion                       | P2       | 8         | Easy       |
| `medium` | Cascading Failures in Recommendation Engine — unbounded LRU cache memory leak                 | P1       | 12        | Medium     |
| `hard`   | Silent Data Corruption in Order Pipeline — Kafka consumer rebalance with duplicate processing | P0       | 16        | Hard       |

The hard task involves correlating Kafka consumer lag, Postgres replication delay, idempotency key reads from a stale replica, and `enable.auto.commit=true` — a class of bug that genuinely challenges frontier models.

---

## Reward Function

| Signal                                        | Reward        |
| --------------------------------------------- | ------------- |
| Investigation step (logs / metrics / traces)  | `+0.15`       |
| Reasoning quality bonus (per step, scaled)    | `up to +0.05` |
| Correct root cause identified                 | `+0.25`       |
| Memory bonus (reused past incident knowledge) | `+0.10`       |
| Correct fix applied                           | `+0.20`       |
| Successful resolution                         | `+0.30`       |
| Speed bonus (resolved in half max steps)      | `+0.10`       |
| Repeated action (loop penalty)                | `-0.10`       |
| Wrong root cause guess                        | `-0.10`       |
| Premature resolution attempt                  | `-0.15`       |

Rewards fire throughout the trajectory — not just at episode end.

---

## Observation Space

```python
class IncidentObservation(BaseModel):
    incident_id: str
    title: str
    severity: str
    affected_services: List[str]
    alert_messages: List[str]
    logs: List[str]
    metrics: Dict[str, Any]
    available_actions: List[str]
    runbook_hints: List[str]
    diagnosis_so_far: List[str]
    current_step: int
    max_steps: int
    resolved: bool
    reasoning_score: Optional[float]        # avg reasoning quality so far
    reasoning_feedback: List[str]           # per-step rubric feedback
    past_similar_incidents: List[Dict]      # cross-incident memory injection
```

## Action Space

```python
class IncidentAction(BaseModel):
    action_type: str          # one of the actions listed below
    parameters: Dict          # e.g. {"root_cause": "..."} for identify_root_cause
    reasoning: Optional[str]  # explanation scored by Reasoning Trace Evaluator
```

**Available actions:** `check_logs` · `check_metrics` · `check_traces` · `check_dependencies` · `run_query` · `identify_root_cause` · `identify_memory_leak` · `increase_connection_pool` · `restart_service` · `rolling_restart` · `fix_cache_config` · `disable_auto_commit` · `fix_idempotency_read_source` · `drain_kafka_backlog` · `reconcile_inventory` · `escalate` · `resolve`

---

## API Endpoints

| Method | Endpoint  | Description                                        |
| ------ | --------- | -------------------------------------------------- |
| `POST` | `/reset`  | Start a new episode `{"task": "easy/medium/hard"}` |
| `POST` | `/step`   | Take an action                                     |
| `GET`  | `/state`  | Current episode state                              |
| `POST` | `/grade`  | Get episode score (0.0–1.0)                        |
| `GET`  | `/tasks`  | List available tasks                               |
| `GET`  | `/health` | Health check                                       |

---

## Setup

```bash
pip install -r requirements.txt
python app.py
```

## Docker

```bash
docker build -t incident-commander-env .
docker run -p 7860:7860 -e HF_TOKEN=your_token incident-commander-env
```

## Inference

```bash
# Local development (Groq)
export GROQ_API_KEY=your_key
python inference.py

# Production (HuggingFace)
export HF_TOKEN=your_token
export API_BASE_URL=https://router.huggingface.co/v1
export MODEL_NAME=Qwen/Qwen2.5-72B-Instruct
python inference.py
```

---

## Baseline Scores

Verified end-to-end with `Qwen/Qwen2.5-72B-Instruct` via HuggingFace router:

| Task        | Score    | Steps | Avg Reasoning | Memory Bonus |
| ----------- | -------- | ----- | ------------- | ------------ |
| easy        | 1.00     | 5     | 0.68          | —            |
| medium      | 1.00     | 7     | 0.65          | yes          |
| hard        | 1.00     | 9     | 0.50          | —            |
| **average** | **1.00** | —     | **0.61**      | —            |

---

## Project Structure

```
incident-commander-env/
├── incident_env.py      # Core RL environment + Reasoning Evaluator + Memory Store
├── app.py               # FastAPI server (OpenEnv-compatible endpoints)
├── inference.py         # Baseline inference script (OpenAI client)
├── test_incident_env.py # Unit tests (33/33 passing)
├── openenv.yaml         # OpenEnv spec metadata
├── requirements.txt
└── Dockerfile
```

---
