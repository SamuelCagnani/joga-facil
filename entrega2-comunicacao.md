# Entrega 2 — Comunicação entre os Serviços

## 1. Visão geral

A Entrega 2 pede dois serviços se comunicando via RPC/REST. Foram implementados:

| Serviço         | Porta | Responsabilidade                                  |
| --------------- | ----- | ------------------------------------------------- |
| court-service   | 8001  | Cadastro e consulta de quadras                    |
| match-service   | 8002  | Criação e listagem de partidas; valida a quadra   |
| frontend (nginx)| 80    | Página HTML de demonstração + gateway para as APIs|

Cada serviço é um processo independente (container Docker próprio), com sua própria API
REST. A comunicação entre eles acontece quando o `match-service` precisa validar uma quadra.

## 2. Fluxo de comunicação

```
Cliente
  │
  │  POST /matches {"court_id": "court_4e6924a1", ...}
  ▼
match-service (8002)
  │
  │  GET http://court-service:8001/courts/court_4e6924a1   (REST/HTTP)
  ▼
court-service (8001)
  │
  │  200 {"id": "...", "name": "Arena Central", ...}
  ▼
match-service
  │
  │  201 {"id": "match_...", "court_name": "Arena Central", ...}
  ▼
Cliente
```

- Se a quadra não existe, o `court-service` responde 404 e o `match-service` devolve
  **400 "Quadra nao encontrada no court-service"** para o cliente.
- Se o `court-service` estiver fora do ar, o `match-service` devolve **503**.
- Se já existir uma reserva para a **mesma quadra e data com sobreposição de horário**, o
  `match-service` devolve **409 "Ja existe uma reserva nesse horario para esta quadra"**.
  A checagem é feita no próprio `match-service` (dono das partidas) e fica sob um lock,
  evitando duas reservas simultâneas no mesmo horário.
- Isso comprova que a resposta do `match-service` depende de uma chamada real ao
  `court-service` (o campo `court_name` nem é enviado pelo cliente; ele vem da outra API).

## 3. Como a comunicação foi implementada

- No `match-service`, a URL do outro serviço vem da variável de ambiente
  `COURT_SERVICE_URL` (em `match-service/app/main.py`):

```python
COURT_SERVICE_URL = os.getenv("COURT_SERVICE_URL", "http://localhost:8001")
```

- A chamada é feita com a biblioteca `requests` dentro do endpoint `POST /matches`:

```python
resposta = requests.get(f"{COURT_SERVICE_URL}/courts/{body.court_id}", timeout=5)
```

- No `docker-compose.yml`, o endereço usa o **nome do serviço no Compose**, que o Docker
  resolve por DNS interno da rede dos containers:

```yaml
environment:
  COURT_SERVICE_URL: http://court-service:8001
```

- **Middlewares usados:** Docker Compose (execução dos containers/processos), HTTP/REST
  (comunicação) e nginx (gateway/reverse proxy e servidor da página de demonstração).
  Os dados ficam em memória (dicionários Python), reiniciando a cada start.

## 4. Endpoints

### court-service (8001)

| Método | Rota                 | Descrição                                                 |
| ------ | -------------------- | --------------------------------------------------------- |
| GET    | `/health`            | Status do serviço                                         |
| POST   | `/courts`            | Cadastra uma quadra (409 se nome+endereço já existirem)   |
| GET    | `/courts`            | Lista todas as quadras                                    |
| GET    | `/courts/{court_id}` | Consulta uma quadra pelo id                               |
| DELETE | `/courts/{court_id}` | Apaga uma quadra (204; 404 se não existir)                |

### match-service (8002)

| Método | Rota                  | Descrição                                             |
| ------ | --------------------- | ----------------------------------------------------- |
| GET    | `/health`             | Status do serviço                                     |
| POST   | `/matches`            | Cria partida (consulta o court-service via REST)      |
| GET    | `/matches`            | Lista as partidas criadas                             |
| DELETE | `/matches/{match_id}` | Apaga uma reserva (204; 404 se não existir)           |

## 5. Como reproduzir (local)

```bash
docker compose up --build -d
```

1) Ver os serviços no ar:

```bash
curl localhost:8001/health
# {"status":"ok","service":"court-service"}
curl localhost:8002/health
# {"status":"ok","service":"match-service"}
```

2) Listar as quadras de exemplo (já cadastradas na subida do serviço):

```bash
curl localhost:8001/courts
# [{"id":"court_4e6924a1","name":"Arena Central","address":"Rua A, 100","price_per_hour":120.0},
#  {"id":"court_89c1dfe1","name":"Society do Ze","address":"Av. B, 200","price_per_hour":90.0}]
```

3) Criar uma partida usando o id de uma quadra (aqui a comunicação REST acontece):

```bash
curl -w "\nHTTP %{http_code}\n" -X POST localhost:8002/matches -H 'Content-Type: application/json' \
  -d '{"court_id":"court_4e6924a1","title":"Pelada Quinta","date":"2026-10-02","start_time":"20:00","end_time":"21:30","max_players":12,"price_per_player":20}'
```

Saída obtida:

```
{"id":"match_89b06b72","court_id":"court_4e6924a1","court_name":"Arena Central","title":"Pelada Quinta","date":"2026-10-02","start_time":"20:00","end_time":"21:30","max_players":12,"price_per_player":20.0}
HTTP 201
```

Obs.: `court_name` não foi enviado pelo cliente — veio da resposta do `court-service`.

4) Provar que o match-service consulta o court-service (quadra inexistente):

```bash
curl -w "\nHTTP %{http_code}\n" -X POST localhost:8002/matches -H 'Content-Type: application/json' \
  -d '{"court_id":"court_naoexiste","title":"Teste","date":"2026-10-02","start_time":"20:00","end_time":"21:30"}'
```

Saída obtida:

```
{"detail":"Quadra nao encontrada no court-service"}
HTTP 400
```

## 6. Frontend de demonstração

Para facilitar a demonstração foi adicionada uma página HTML simples em
`frontend/index.html`, servida por um container **nginx** (`frontend/nginx.conf`) na porta 80.

- O nginx serve a página e também atua como **gateway/reverse proxy**: as chamadas
  `/courts` são encaminhadas para `court-service:8001` e `/matches` para `match-service:8002`.
- Como a página e as APIs ficam na mesma origem, não é necessário configurar CORS.
- A página lista as quadras, lista as partidas e permite criar partidas. Ao criar uma
  partida, a resposta exibida mostra o campo `court_name`, que veio do `court-service`,
  tornando a comunicação entre os serviços visível na tela.
- Ela também permite **cadastrar quadras** (`POST /courts`), **apagar quadras**
  (`DELETE /courts/{id}`), **apagar reservas** (`DELETE /matches/{id}`) e digitar um
  **id de quadra inexistente** no campo de quadra (input com sugestões) para ver o erro 400.
  Ao tentar reservar um horário já ocupado da mesma quadra, a página exibe o 409; ao
  cadastrar uma quadra com **nome e endereço já existentes**, exibe o 409 de duplicidade.

Acesso local: http://localhost
Acesso na AWS: http://<ip-publico> (ex.: http://44.192.85.121)

## 7. Evidências para o relatório

- Prints desta página executada no terminal (itens 5.1 a 5.4).
- Print do `docker ps` mostrando os containers rodando (court, match e frontend).
- Print do Swagger (`/docs`) de cada serviço.
- Print do frontend (`http://<ip-publico>`) criando uma partida na AWS.
- Print do mesmo teste feito na AWS (seção 8).

## 8. Implantação na AWS (Fase 2)

O sistema foi implantado em uma instância **Amazon EC2** (`t3.micro`, Ubuntu 24.04) na região
`us-east-1`. Os três containers (court-service, match-service e frontend/nginx) rodam na mesma
instância, orquestrados pelo Docker Compose. O security group libera as portas 22 (SSH,
restrita ao IP do desenvolvedor), 80 (frontend) e 8001/8002 (APIs).

Passos executados:

1. Instalação do Docker e do Docker Compose na instância (Ubuntu 24.04).
2. Envio dos serviços para a instância (sem uso do GitHub, apenas cópia dos arquivos):

```bash
scp -i chave.pem -r court-service match-service frontend docker-compose.yml ubuntu@<ip>:/home/ubuntu/jogafacil/
```

3. Subida dos containers na nuvem:

```bash
cd /home/ubuntu/jogafacil
sudo docker compose up -d --build
```

4. Testes feitos de fora da instância (da máquina do desenvolvedor, via IP público):

```bash
curl http://<ip-publico>:8001/courts
# [{"id":"court_81d7a310","name":"Arena Central",...},{"id":"court_30a8bd6e","name":"Society do Ze",...}]

curl -X POST http://<ip-publico>:8002/matches -H 'Content-Type: application/json' \
  -d '{"court_id":"court_81d7a310","title":"Pelada Quinta",...}'
# HTTP 201 -> {"id":"match_7ffa9eeb","court_name":"Arena Central",...}

curl -X POST http://<ip-publico>:8002/matches -H 'Content-Type: application/json' \
  -d '{"court_id":"court_naoexiste",...}'
# HTTP 400 -> {"detail":"Quadra nao encontrada no court-service"}
```

Isso comprova que, na nuvem, o `match-service` também consulta o `court-service` via REST
(nos containers, pelo nome `http://court-service:8001`).

Com o frontend publicado, a demonstração pode ser feita direto no navegador:
**http://44.192.85.121** (criando uma partida e vendo o `court_name` vindo do outro serviço).

> Observação: a instância EC2 deve ser **parada/terminada após a demonstração** para evitar
> cobrança. O ambiente é de demonstração e os dados são apenas em memória.