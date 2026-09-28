import os

import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from uuid import uuid4

COURT_SERVICE_URL = os.getenv("COURT_SERVICE_URL", "http://localhost:8001")

app = FastAPI(title="JogaFacil - Match Service")

matches = {}


class MatchIn(BaseModel):
    court_id: str
    title: str
    date: str
    start_time: str
    end_time: str
    max_players: int = 12
    price_per_player: float = 0


@app.get("/health")
def health():
    return {"status": "ok", "service": "match-service"}


@app.post("/matches", status_code=201)
def create_match(body: MatchIn):
    try:
        resposta = requests.get(
            f"{COURT_SERVICE_URL}/courts/{body.court_id}", timeout=5
        )
    except requests.exceptions.RequestException:
        raise HTTPException(status_code=503, detail="court-service indisponivel")

    if resposta.status_code == 404:
        raise HTTPException(
            status_code=400, detail="Quadra nao encontrada no court-service"
        )

    quadra = resposta.json()
    match_id = f"match_{uuid4().hex[:8]}"
    matches[match_id] = {
        "id": match_id,
        "court_id": quadra["id"],
        "court_name": quadra["name"],
        "title": body.title,
        "date": body.date,
        "start_time": body.start_time,
        "end_time": body.end_time,
        "max_players": body.max_players,
        "price_per_player": body.price_per_player,
    }
    return matches[match_id]


@app.get("/matches")
def list_matches():
    return list(matches.values())