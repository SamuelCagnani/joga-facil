import os

import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from uuid import uuid4
import threading

COURT_SERVICE_URL = os.getenv("COURT_SERVICE_URL", "http://localhost:8001")

app = FastAPI(title="JogaFacil - Match Service")

matches = {}
_lock = threading.Lock()


def _to_minutes(hhmm: str) -> int:
    horas, minutos = hhmm.split(":")
    return int(horas) * 60 + int(minutos)


def _overlaps(start_a: int, end_a: int, start_b: int, end_b: int) -> bool:
    return start_a < end_b and start_b < end_a


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

    try:
        inicio = _to_minutes(body.start_time)
        fim = _to_minutes(body.end_time)
    except ValueError:
        raise HTTPException(status_code=400, detail="Horario invalido (use HH:MM)")

    if fim <= inicio:
        raise HTTPException(
            status_code=400, detail="Horario final deve ser maior que o inicial"
        )

    with _lock:
        for partida in matches.values():
            if partida["court_id"] != quadra["id"] or partida["date"] != body.date:
                continue
            if _overlaps(
                inicio,
                fim,
                _to_minutes(partida["start_time"]),
                _to_minutes(partida["end_time"]),
            ):
                raise HTTPException(
                    status_code=409,
                    detail="Ja existe uma reserva nesse horario para esta quadra",
                )

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


@app.delete("/matches/{match_id}", status_code=204)
def delete_match(match_id: str):
    with _lock:
        if match_id not in matches:
            raise HTTPException(status_code=404, detail="Partida nao encontrada")
        del matches[match_id]
