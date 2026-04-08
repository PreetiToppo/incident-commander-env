import os
import json
from typing import Optional
from openai import OpenAI
from incident_env import IncidentCommanderEnv, IncidentAction

API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")
HF_TOKEN = os.getenv("HF_TOKEN")

if not HF_TOKEN:
    raise ValueError("HF_TOKEN environment variable is required")

client = OpenAI(base_url=API_BASE_URL, api_key=HF_TOKEN)

TASKS = ["easy", "medium", "hard"]
MAX_STEPS = {"easy": 8, "medium": 12, "hard": 16}

SYSTEM_PROMPT = """You are an expert Site Reliability Engineer (SRE) responding to a production incident.
You must investigate the incident systematically and resolve it.

At each step, respond with a JSON object:
{
  "action_type": "<action_name>",
  "parameters": {"root_cause": "<if identifying root cause>", "notes": "<if resolving>"}
}

Available actions:
- check_logs: Read service logs
- check_metrics: View metrics dashboard
- check_traces: Check distributed traces (medium/hard)
- check_dependencies: Check service configs (hard only)
- run_query: Run diagnostic DB query (hard only)
- identify_root_cause: Identify root cause (include "root_cause" parameter)
- increase_connection_pool: Fix connection pool exhaustion
- restart_service: Restart crashed service
- rolling_restart: Rolling restart (preserves availability)
- fix_cache_config: Fix unbounded cache
- disable_auto_commit: Fix Kafka auto-commit
- fix_idempotency_read_source: Fix idempotency check reading from replica
- drain_kafka_backlog: Drain Kafka consumer lag
- reconcile_inventory: Fix inventory discrepancies
- identify_memory_leak: Diagnose memory leak
- resolve: Resolve the incident (include "notes" parameter)

Strategy:
1. Always check_logs and check_metrics first
2. For complex incidents, check_traces and check_dependencies
3. identify_root_cause with the exact root cause string
4. Apply the correct fix
5. Call resolve with notes

Root cause options:
- database_connection_pool_exhausted
- memory_leak_in_recommendation_service
- kafka_consumer_group_lag_with_duplicate_processing

Respond ONLY with valid JSON. No explanations."""


def log_start(task: str, env: str, model: str):
    print(f"[START] task={task} env={env} model={model}", flush=True)


def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]):
    error_val = error if error else "null"
    print(f"[STEP] step={step} action={action} reward={reward:.2f} done={str(done).lower()} error={error_val}", flush=True)


def log_end(success: bool, steps: int, score: float, rewards: list):
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(f"[END] success={str(success).lower()} steps={steps} score={score:.2f} rewards={rewards_str}", flush=True)


def get_action_from_llm(obs_dict: dict, conversation_history: list) -> dict:
    obs_text = f"""
INCIDENT: {obs_dict['title']} (Severity: {obs_dict['severity']})
Affected: {', '.join(obs_dict['affected_services'])}
Alerts: {chr(10).join(obs_dict['alert_messages'])}
Logs seen: {chr(10).join(obs_dict.get('logs', []))}
Metrics: {json.dumps(obs_dict.get('metrics', {}), indent=2)}
Diagnosis so far: {', '.join(obs_dict.get('diagnosis_so_far', []))}
Step: {obs_dict['current_step']}/{obs_dict['max_steps']}
Resolved: {obs_dict['resolved']}

What is your next action? Respond with JSON only.
"""
    conversation_history.append({"role": "user", "content": obs_text})

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "system", "content": SYSTEM_PROMPT}] + conversation_history,
            max_tokens=200,
            temperature=0.3
        )
        reply = response.choices[0].message.content.strip()
        conversation_history.append({"role": "assistant", "content": reply})
        # Clean JSON
        if "```" in reply:
            reply = reply.split("```")[1]
            if reply.startswith("json"):
                reply = reply[4:]
        return json.loads(reply.strip())
    except Exception as e:
        return {"action_type": "check_logs", "parameters": {}}


def run_task(task_name: str):
    env = IncidentCommanderEnv(task=task_name)
    obs = env.reset()
    log_start(task_name, "incident-commander", MODEL_NAME)

    rewards = []
    conversation_history = []
    done = False
    step = 0

    while not done:
        obs_dict = obs.model_dump()
        action_dict = get_action_from_llm(obs_dict, conversation_history)

        action = IncidentAction(
            action_type=action_dict.get("action_type", "check_logs"),
            parameters=action_dict.get("parameters", {})
        )

        obs, reward, done, info = env.step(action)
        step += 1
        rewards.append(reward)
        error = info.get("error") or info.get("hint")
        log_step(step, action.action_type, reward, done, str(error) if error else None)

    score = env.grade()
    success = score >= 0.5
    log_end(success, step, score, rewards)
    env.close()
    return score


if __name__ == "__main__":
    total_score = 0.0
    for task in TASKS:
        score = run_task(task)
        total_score += score
    avg = total_score / len(TASKS)
    print(f"\nAverage score across all tasks: {avg:.4f}", flush=True)