---
title: Incident Commander Environment
emoji: 🚨
colorFrom: red
colorTo: pink
sdk: docker
pinned: false
tags:
  - openenv
---

# Incident Commander Environment

An OpenEnv RL environment simulating real-world SRE production incident response.

## Tasks
| Task | Incident | Difficulty |
|------|----------|------------|
| easy | Payment Service High Latency (DB connection pool) | Easy |
| medium | Cascading Failures in Recommendation Engine (memory leak) | Medium |
| hard | Silent Data Corruption in Order Pipeline (Kafka duplicates) | Hard |

## Setup
```bash
pip install -r requirements.txt
python app.py
```

## Docker
```bash
docker build -t incident-commander-env .
docker run -p 7860:7860 incident-commander-env
```

## Baseline Scores
| Task | Score |
|------|-------|
| easy | 0.80 |
| medium | 0.65 |
| hard | 0.45 |
