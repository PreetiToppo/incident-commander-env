import random
import time
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel

# ─── Pydantic Models ─────────────────────────────────────────────────────────

class IncidentObservation(BaseModel):
    incident_id: str
    title: str
    severity: str
    affected_services: List[str]
    alert_messages: List[str]
    available_actions: List[str]
    current_step: int
    max_steps: int
    logs: Optional[List[str]] = []
    metrics: Optional[Dict[str, Any]] = {}
    runbook_hints: Optional[List[str]] = []
    diagnosis_so_far: Optional[List[str]] = []
    resolved: bool = False
    resolution_notes: Optional[str] = None

class IncidentAction(BaseModel):
    action_type: str
    parameters: Optional[Dict[str, Any]] = {}

class IncidentReward(BaseModel):
    value: float
    reason: str
    cumulative: float

# ─── Incident Scenarios ───────────────────────────────────────────────────────

EASY_SCENARIO = {
    "incident_id": "INC-001",
    "title": "Payment Service High Latency",
    "severity": "P2",
    "affected_services": ["payment-service"],
    "root_cause": "database_connection_pool_exhausted",
    "alert_messages": [
        "ALERT: payment-service p99 latency > 5000ms (threshold: 500ms)",
        "ALERT: payment-service error rate 12% (threshold: 1%)",
        "INFO: payment-service pod count: 3/3 running"
    ],
    "logs": {
        "check_logs": [
            "[ERROR] HikariPool-1 - Connection is not available, request timed out after 30000ms",
            "[ERROR] Unable to acquire JDBC Connection",
            "[WARN] HikariPool-1 - Thread starvation or clock leap detected",
            "[INFO] Active connections: 10/10, Idle: 0, Waiting: 47"
        ],
        "check_metrics": {
            "db_connection_pool_active": 10,
            "db_connection_pool_max": 10,
            "db_connection_pool_waiting": 47,
            "latency_p99_ms": 5200,
            "error_rate_percent": 12.3
        }
    },
    "resolution_steps": ["check_logs", "check_metrics", "increase_connection_pool", "restart_service"],
    "correct_root_cause": "database_connection_pool_exhausted",
    "correct_fix": "increase_connection_pool",
    "runbook_hints": [
        "Check DB connection pool metrics when latency spikes occur",
        "HikariPool exhaustion is a common cause of payment service degradation"
    ]
}

MEDIUM_SCENARIO = {
    "incident_id": "INC-002",
    "title": "Cascading Failures in Recommendation Engine",
    "severity": "P1",
    "affected_services": ["recommendation-service", "user-service", "api-gateway"],
    "root_cause": "memory_leak_in_recommendation_service",
    "alert_messages": [
        "ALERT: api-gateway 502 error rate 34% (threshold: 5%)",
        "ALERT: recommendation-service memory usage 98% (threshold: 80%)",
        "ALERT: user-service dependency timeout rate 45%",
        "ALERT: recommendation-service OOMKilled 3 times in last 10 minutes"
    ],
    "logs": {
        "check_logs": [
            "[ERROR] recommendation-service: java.lang.OutOfMemoryError: Java heap space",
            "[ERROR] api-gateway: upstream recommendation-service connection refused",
            "[WARN] user-service: recommendation endpoint timeout after 5000ms",
            "[INFO] recommendation-service restart #3 at 14:23:11 UTC"
        ],
        "check_metrics": {
            "recommendation_service_memory_mb": 7850,
            "recommendation_service_memory_limit_mb": 8000,
            "heap_used_percent": 98.1,
            "gc_pause_ms_avg": 4200,
            "api_gateway_502_rate": 34.2,
            "recommendation_service_restarts": 3
        },
        "check_traces": [
            "TraceID abc123: GET /recommendations -> OOM after processing 10k items",
            "TraceID def456: recommendation-service heap dump shows 2M cached objects",
            "TraceID ghi789: Cache not being evicted — LRU cache maxSize set to UNLIMITED"
        ]
    },
    "resolution_steps": ["check_logs", "check_metrics", "check_traces", "identify_memory_leak", "fix_cache_config", "rolling_restart"],
    "correct_root_cause": "memory_leak_in_recommendation_service",
    "correct_fix": "fix_cache_config",
    "runbook_hints": [
        "When OOMKilled events correlate with cascading failures, start with the crashing service",
        "Check cache configurations — unbounded caches are a common memory leak source",
        "Rolling restart preserves availability during fix deployment"
    ]
}

HARD_SCENARIO = {
    "incident_id": "INC-003",
    "title": "Silent Data Corruption in Order Processing Pipeline",
    "severity": "P0",
    "affected_services": ["order-service", "inventory-service", "fulfillment-service", "kafka-cluster", "postgres-primary"],
    "root_cause": "kafka_consumer_group_lag_with_duplicate_processing",
    "alert_messages": [
        "ALERT: order-service duplicate order creation rate 0.3% (threshold: 0%)",
        "ALERT: inventory-service stock count mismatch detected",
        "ALERT: fulfillment-service: 127 orders in UNKNOWN state",
        "ALERT: kafka consumer group lag: order-processor lag=145000 messages",
        "ALERT: postgres-primary replication lag: 45 seconds"
    ],
    "logs": {
        "check_logs": [
            "[ERROR] order-service: Idempotency key collision for order-789 — duplicate insert attempted",
            "[WARN] kafka-consumer: Rebalance triggered 14 times in last hour",
            "[ERROR] inventory-service: Negative stock count for SKU-4521: -3",
            "[INFO] fulfillment-service: Order state machine stuck in PROCESSING for >15min",
            "[ERROR] postgres-primary: WAL sender timeout — replica fell behind"
        ],
        "check_metrics": {
            "kafka_consumer_lag": 145000,
            "kafka_rebalance_count_1h": 14,
            "duplicate_orders_per_hour": 47,
            "postgres_replication_lag_sec": 45,
            "inventory_negative_count_skus": 3,
            "orders_in_unknown_state": 127
        },
        "check_traces": [
            "TraceID x1: order-789 processed twice — consumer rebalance mid-commit",
            "TraceID x2: inventory deduction ran twice for same order due to at-least-once delivery",
            "TraceID x3: idempotency check reads from replica (stale) — misses recent commit"
        ],
        "check_dependencies": {
            "kafka_version": "2.8.0",
            "consumer_group_config": "enable.auto.commit=true, auto.commit.interval.ms=1000",
            "order_service_config": "idempotency_check_reads_from=replica",
            "postgres_replica_lag_sec": 45
        },
        "run_query": "SELECT order_id, COUNT(*) FROM orders GROUP BY order_id HAVING COUNT(*) > 1 LIMIT 5; -- Returns 47 duplicate orders"
    },
    "resolution_steps": [
        "check_logs", "check_metrics", "check_traces", "check_dependencies",
        "run_query", "identify_root_cause", "disable_auto_commit",
        "fix_idempotency_read_source", "drain_kafka_backlog", "reconcile_inventory"
    ],
    "correct_root_cause": "kafka_consumer_group_lag_with_duplicate_processing",
    "correct_fix": "disable_auto_commit_and_fix_idempotency",
    "runbook_hints": [
        "When duplicates appear, check idempotency key implementation and read source",
        "Kafka rebalances with auto-commit can cause at-least-once redelivery",
        "Always read idempotency keys from primary, never replica with replication lag",
        "Reconciliation must happen after fixing the root cause, not before"
    ]
}

SCENARIOS = {
    "easy": EASY_SCENARIO,
    "medium": MEDIUM_SCENARIO,
    "hard": HARD_SCENARIO
}

# ─── Environment Class ────────────────────────────────────────────────────────

class IncidentCommanderEnv:
    """
    IncidentCommanderEnv: An RL environment simulating real-world SRE incident response.
    Agents must triage, diagnose, and resolve production incidents.
    """

    AVAILABLE_ACTIONS = [
        "check_logs",
        "check_metrics",
        "check_traces",
        "check_dependencies",
        "run_query",
        "identify_root_cause",
        "increase_connection_pool",
        "restart_service",
        "rolling_restart",
        "fix_cache_config",
        "disable_auto_commit",
        "fix_idempotency_read_source",
        "drain_kafka_backlog",
        "reconcile_inventory",
        "identify_memory_leak",
        "escalate",
        "resolve"
    ]

    def __init__(self, task: str = "easy"):
        assert task in SCENARIOS, f"Task must be one of {list(SCENARIOS.keys())}"
        self.task = task
        self.scenario = SCENARIOS[task]
        self.max_steps = {"easy": 8, "medium": 12, "hard": 16}[task]
        self._state = {}
        self._cumulative_reward = 0.0
        self._step_count = 0
        self._done = False
        self._actions_taken = []
        self._diagnosis = []

    def reset(self) -> IncidentObservation:
        self._state = {
            "incident_id": self.scenario["incident_id"],
            "title": self.scenario["title"],
            "severity": self.scenario["severity"],
            "affected_services": self.scenario["affected_services"],
            "alert_messages": self.scenario["alert_messages"],
            "logs_checked": False,
            "metrics_checked": False,
            "traces_checked": False,
            "root_cause_identified": False,
            "fix_applied": False,
            "resolved": False,
            "resolution_notes": None,
            "visible_logs": [],
            "visible_metrics": {},
            "diagnosis": [],
        }
        self._cumulative_reward = 0.0
        self._step_count = 0
        self._done = False
        self._actions_taken = []
        self._diagnosis = []
        return self._build_observation()

    def state(self) -> Dict[str, Any]:
        return {
            **self._state,
            "step_count": self._step_count,
            "cumulative_reward": self._cumulative_reward,
            "done": self._done,
            "actions_taken": self._actions_taken,
        }

    def step(self, action: IncidentAction) -> Tuple[IncidentObservation, float, bool, Dict]:
        if self._done:
            return self._build_observation(), 0.0, True, {"error": "Episode already done"}

        self._step_count += 1
        action_type = action.action_type
        params = action.parameters or {}
        reward = 0.0
        info = {}

        # Penalize repeated actions
        if action_type in self._actions_taken:
            reward -= 0.05
            info["warning"] = f"Action '{action_type}' already taken — penalizing loop"
        else:
            self._actions_taken.append(action_type)

        # Process actions
        if action_type == "check_logs":
            reward += 0.15
            self._state["logs_checked"] = True
            self._state["visible_logs"] = self.scenario["logs"].get("check_logs", [])
            self._diagnosis.append("Checked service logs")

        elif action_type == "check_metrics":
            reward += 0.15
            self._state["metrics_checked"] = True
            self._state["visible_metrics"] = self.scenario["logs"].get("check_metrics", {})
            self._diagnosis.append("Checked metrics dashboard")

        elif action_type == "check_traces":
            if self.task in ["medium", "hard"]:
                reward += 0.15
                self._state["visible_logs"] += self.scenario["logs"].get("check_traces", [])
                self._diagnosis.append("Checked distributed traces")
            else:
                reward -= 0.02
                info["hint"] = "Traces not needed for this incident"

        elif action_type == "check_dependencies":
            if self.task == "hard":
                reward += 0.15
                dep_info = self.scenario["logs"].get("check_dependencies", {})
                self._state["visible_metrics"].update(dep_info)
                self._diagnosis.append("Checked service dependency configs")
            else:
                reward -= 0.02

        elif action_type == "run_query":
            if self.task == "hard":
                reward += 0.10
                self._state["visible_logs"].append(self.scenario["logs"].get("run_query", "No query result"))
                self._diagnosis.append("Ran diagnostic database query")
            else:
                reward -= 0.02

        elif action_type == "identify_root_cause":
            root_cause_guess = params.get("root_cause", "")
            if root_cause_guess == self.scenario["correct_root_cause"]:
                reward += 0.25
                self._state["root_cause_identified"] = True
                self._diagnosis.append(f"Correctly identified root cause: {root_cause_guess}")
            else:
                reward -= 0.10
                self._diagnosis.append(f"Incorrect root cause guess: {root_cause_guess}")
                info["hint"] = "Wrong root cause — investigate further"

        elif action_type == self.scenario["correct_fix"]:
            if self._state["root_cause_identified"]:
                reward += 0.20
                self._state["fix_applied"] = True
                self._diagnosis.append(f"Applied correct fix: {action_type}")
            else:
                reward += 0.05
                self._diagnosis.append(f"Applied fix {action_type} without identifying root cause")

        elif action_type == "resolve":
            if self._state["fix_applied"] and self._state["root_cause_identified"]:
                reward += 0.30
                self._state["resolved"] = True
                self._state["resolution_notes"] = params.get("notes", "Incident resolved")
                self._done = True
                info["success"] = True
            elif self._state["logs_checked"] and self._state["metrics_checked"]:
                reward -= 0.05
                info["hint"] = "Cannot resolve — fix not yet applied"
            else:
                reward -= 0.15
                info["hint"] = "Cannot resolve — insufficient investigation"

        elif action_type == "escalate":
            reward -= 0.05
            self._diagnosis.append("Escalated incident (penalized — try to resolve yourself)")

        else:
            # Generic fix actions
            if action_type in self.AVAILABLE_ACTIONS:
                reward += 0.02
            else:
                reward -= 0.05
                info["error"] = f"Unknown action: {action_type}"

        # Step limit penalty
        if self._step_count >= self.max_steps and not self._done:
            reward -= 0.10
            self._done = True
            info["timeout"] = True

        self._cumulative_reward = round(self._cumulative_reward + reward, 4)
        self._state["diagnosis"] = self._diagnosis

        obs = self._build_observation()
        return obs, round(reward, 4), self._done, info

    def _build_observation(self) -> IncidentObservation:
        return IncidentObservation(
            incident_id=self._state.get("incident_id", ""),
            title=self._state.get("title", ""),
            severity=self._state.get("severity", ""),
            affected_services=self._state.get("affected_services", []),
            alert_messages=self._state.get("alert_messages", []),
            available_actions=self.AVAILABLE_ACTIONS,
            current_step=self._step_count,
            max_steps=self.max_steps,
            logs=self._state.get("visible_logs", []),
            metrics=self._state.get("visible_metrics", {}),
            runbook_hints=self.scenario.get("runbook_hints", []),
            diagnosis_so_far=self._state.get("diagnosis", []),
            resolved=self._state.get("resolved", False),
            resolution_notes=self._state.get("resolution_notes")
        )

    def grade(self) -> float:
        """Returns a score between 0.0 and 1.0 for the episode."""
        score = 0.0
        if self._state.get("logs_checked"):
            score += 0.10
        if self._state.get("metrics_checked"):
            score += 0.10
        if self._state.get("root_cause_identified"):
            score += 0.35
        if self._state.get("fix_applied"):
            score += 0.25
        if self._state.get("resolved"):
            score += 0.20
        # Speed bonus
        if self._state.get("resolved") and self._step_count <= self.max_steps // 2:
            score = min(1.0, score + 0.10)
        return round(score, 4)

    def close(self):
        pass