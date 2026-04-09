import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from typing import Optional, Dict, Any
from pydantic import BaseModel
from incident_env import IncidentCommanderEnv, IncidentAction

app = FastAPI(
    title="Incident Commander Environment",
    description="OpenEnv-compatible RL environment for SRE incident response",
    version="1.0.0"
)

sessions: Dict[str, IncidentCommanderEnv] = {}


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
async def reset(request: Request):
    # Accept empty body OR json body
    try:
        body = await request.json()
    except Exception:
        body = {}

    task = body.get("task", "easy") if body else "easy"
    session_id = body.get("session_id", "default") if body else "default"

    env = IncidentCommanderEnv(task=task)
    obs = env.reset()
    sessions[session_id] = env
    return obs.dict()


@app.post("/step")
def step(request: StepRequest):
    env = sessions.get(request.session_id)
    if env is None:
        # Auto-create session if missing
        env = IncidentCommanderEnv(task="easy")
        env.reset()
        sessions[request.session_id] = env

    action = IncidentAction(
        action_type=request.action_type,
        parameters=request.parameters
    )
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
        env = IncidentCommanderEnv(task="easy")
        obs = env.reset()
        sessions[session_id] = env
    return env.state()


@app.post("/grade")
async def grade(request: Request):
    try:
        body = await request.json()
    except Exception:
        body = {}
    session_id = body.get("session_id", "default") if body else "default"
    env = sessions.get(session_id)
    if env is None:
        return {"score": 0.0}
    return {"score": env.grade()}


@app.get("/tasks")
def list_tasks():
    return {
        "tasks": [
            {"name": "easy", "description": "Payment Service High Latency", "difficulty": 1},
            {"name": "medium", "description": "Cascading Failures in Recommendation Engine", "difficulty": 2},
            {"name": "hard", "description": "Silent Data Corruption in Order Pipeline", "difficulty": 3}
        ]
    }


def main():
    import uvicorn
    uvicorn.run("server.app:app", host="0.0.0.0", port=7860)


if __name__ == "__main__":
    main()