from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from uuid import uuid4

app = FastAPI(title="JogaFacil - Court Service")

courts = {}


class CourtIn(BaseModel):
    name: str
    address: str
    price_per_hour: float


@app.get("/health")
def health():
    return {"status": "ok", "service": "court-service"}


@app.post("/courts", status_code=201)
def create_court(body: CourtIn):
    court_id = f"court_{uuid4().hex[:8]}"
    courts[court_id] = {
        "id": court_id,
        "name": body.name,
        "address": body.address,
        "price_per_hour": body.price_per_hour,
    }
    return courts[court_id]


@app.get("/courts")
def list_courts():
    return list(courts.values())


@app.get("/courts/{court_id}")
def get_court(court_id: str):
    if court_id not in courts:
        raise HTTPException(status_code=404, detail="Quadra nao encontrada")
    return courts[court_id]


for nome, endereco, preco in [
    ("Arena Central", "Rua A, 100", 120.0),
    ("Society do Ze", "Av. B, 200", 90.0),
]:
    cid = f"court_{uuid4().hex[:8]}"
    courts[cid] = {
        "id": cid,
        "name": nome,
        "address": endereco,
        "price_per_hour": preco,
    }