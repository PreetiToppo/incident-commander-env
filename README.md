python -c "
content = '''---
title: Incident Commander Env
emoji: 🚨
colorFrom: red
colorTo: orange
sdk: docker
app_file: app.py
pinned: false

---

# Incident Commander Environment 🚨

An OpenEnv RL environment simulating real-world SRE production incident response.

## Tasks

| Task   | Incident                                                    | Difficulty |
| ------ | ----------------------------------------------------------- | ---------- |
| easy   | Payment Service High Latency (DB connection pool)           | Easy       |
| medium | Cascading Failures in Recommendation Engine (memory leak)   | Medium     |
| hard   | Silent Data Corruption in Order Pipeline (Kafka duplicates) | Hard       |

## Setup

\`\`\`bash
pip install -r requirements.txt
python app.py
\`\`\`

## Inference

\`\`\`bash
export HF_TOKEN=your_token
python inference.py
\`\`\`

## Baseline Scores

| Task   | Score |
| ------ | ----- |
| easy   | 0.80  |
| medium | 0.65  |
| hard   | 0.45  |

'''
open('README.md','w').write(content)
print('done')
"
