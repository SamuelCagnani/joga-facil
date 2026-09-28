# JogaFácil — Entrega 2 (Sistemas Distribuídos)

Implementação de dois serviços independentes que se comunicam via REST:

- **court-service** (porta 8001): cadastro e consulta de quadras.
- **match-service** (porta 8002): criação de partidas. Ao criar uma partida, consulta o
  `court-service` via HTTP para validar a quadra e copiar o nome dela.

Os serviços rodam em containers Docker e são iniciados juntos com Docker Compose.
Cada serviço tem documentação interativa (Swagger) em `/docs`.

Há também um **frontend** simples (nginx, porta 80) que serve uma página HTML e encaminha
as chamadas `/courts` e `/matches` para cada serviço — é uma demonstração visual da
comunicação entre eles.

A página permite:

- listar e **cadastrar quadras** (`POST /courts`);
- criar partidas escolhendo uma quadra ou **digitando um id inexistente** para ver o erro 400;
- **apagar reservas** (`DELETE /matches/{id}`);
- visualizar o **conflito de horário** (409) ao tentar reservar a mesma quadra no mesmo horário.

## Estrutura

```
.
├── court-service/
│   ├── app/main.py
│   ├── requirements.txt
│   └── Dockerfile
├── match-service/
│   ├── app/main.py
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── index.html
│   └── nginx.conf
├── docker-compose.yml
└── entrega2-comunicacao.md
```

## Como rodar local

```bash
docker compose up --build -d
```

Testar:

```bash
curl localhost:8001/courts
curl -X POST localhost:8002/matches -H 'Content-Type: application/json' \
  -d '{"court_id":"<id de uma quadra>","title":"Pelada Quinta","date":"2026-10-02","start_time":"20:00","end_time":"21:30"}'
```

Repetindo o mesmo `POST` (mesma quadra, data e horário) a resposta é
**409 `{"detail":"Ja existe uma reserva nesse horario para esta quadra"}`**.
Apagar uma reserva:

```bash
curl -X DELETE localhost:8002/matches/<id da partida>   # HTTP 204
```

Frontend (demonstração visual): http://localhost

Swagger: http://localhost:8001/docs e http://localhost:8002/docs

Detalhes da comunicação entre os serviços: [entrega2-comunicacao.md](entrega2-comunicacao.md)