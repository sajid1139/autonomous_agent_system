import json
import numpy as np
from sentence_transformers import SentenceTransformer
from tortoise import connections

model = SentenceTransformer("all-MiniLM-L6-v2")

async def _ensure_table():
    conn = connections.get("default")
    await conn.execute_script(
        "CREATE TABLE IF NOT EXISTS embeddings ("
        "id SERIAL PRIMARY KEY, "
        "goal_id TEXT, "
        "text TEXT, "
        "embedding TEXT"
        ");"
    )

def _cosine(a, b):
    a, b = np.array(a), np.array(b)
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    return float(np.dot(a, b) / denom) if denom else 0.0

async def store(text: str, goal_id: str):
    await _ensure_table()
    vec = model.encode(text).tolist()
    conn = connections.get("default")
    await conn.execute_query(
        "INSERT INTO embeddings (goal_id, text, embedding) VALUES ($1, $2, $3)",
        [goal_id, text, json.dumps(vec)]
    )

async def search(query: str, goal_id: str) -> list[str]:
    await _ensure_table()
    q_vec = model.encode(query).tolist()
    conn = connections.get("default")
    rows, _ = await conn.execute_query(
        "SELECT text, embedding FROM embeddings WHERE goal_id = $1",
        [goal_id]
    )
    scored = []
    for row in rows:
        vec = json.loads(row[1])
        score = _cosine(q_vec, vec)
        scored.append((score, row[0]))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [t for _, t in scored[:3]]
