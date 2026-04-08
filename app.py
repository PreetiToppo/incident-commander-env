import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from typing import Optional, Dict, Any
from pydantic import BaseModel
from incident_env import IncidentCommanderEnv, IncidentAction

app = FastAPI(
    title="Incident Commander Environment",
    description="OpenEnv-compatible RL environment for SRE incident response",
    version="1.0.0"
)

# In-memory session store
sessions: Dict[str, IncidentCommanderEnv] = {}


class ResetRequest(BaseModel):
    task: Optional[str] = "easy"
    session_id: Optional[str] = "default"


class StepRequest(BaseModel):
    session_id: Optional[str] = "default"
    action_type: str
    parameters: Optional[Dict[str, Any]] = {}


@app.get("/")
def root():
    return {
        "name": "Incident Commander Environment",
        "version": "1.0.0",
        "tasks": ["easy", "medium", "hard"],
        "description": "SRE incident response RL environment"
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/reset")
def reset(request: ResetRequest):
    env = IncidentCommanderEnv(task=request.task)
    obs = env.reset()
    sessions[request.session_id] = env
    return obs.dict()


@app.post("/step")
def step(request: StepRequest):
    env = sessions.get(request.session_id)
    if env is None:
        raise HTTPException(status_code=404, detail="Session not found. Call /reset first.")
    action = IncidentAction(action_type=request.action_type, parameters=request.parameters)
    obs, reward, done, info = env.step(action)
    return {
        "observation": obs.dict(),
        "reward": reward,
        "done": done,
        "info": info
    }


@app.get("/state")
def state(session_id: str = "default"):
    env = sessions.get(session_id)
    if env is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    return env.state()


@app.post("/grade")
def grade(session_id: str = "default"):
    env = sessions.get(session_id)
    if env is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    return {"score": env.grade()}


@app.get("/tasks")
def list_tasks():
    return {
        "tasks": [
            {"name": "easy", "description": "Payment Service High Latency — DB connection pool exhaustion", "difficulty": 1},
            {"name": "medium", "description": "Cascading Failures in Recommendation Engine — memory leak", "difficulty": 2},
            {"name": "hard", "description": "Silent Data Corruption in Order Pipeline — Kafka duplicate processing", "difficulty": 3}
        ]
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7860)