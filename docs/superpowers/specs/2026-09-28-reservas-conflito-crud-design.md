# Design — Reservas: conflito de horário, CRUD e teste de erro

Data: 2026-09-28
Projeto: JogaFácil (Entrega 2 — Sistemas Distribuídos)

## Objetivo

Melhorar a lógica e a página de demonstração para:

1. Permitir tentar reservar uma quadra inexistente e visualizar o erro (400).
2. Bloquear reservas com sobreposição de horário na mesma quadra e data (409).
3. Permitir apagar reservas pela página.
4. Permitir cadastrar novas quadras pela página.

## Decisões

- **Onde bloquear o conflito:** no `match-service`, que é quem guarda todas as
  partidas. É a única fonte da verdade sobre reservas; o `court-service` não
  conhece partidas.
- **Regra de conflito:** sobreposição de horário (qualquer interseção) na mesma
  quadra e data. Intervalos meia-abertos: 20:00–21:30 e 21:30–22:00 **não**
  conflitam.
- **Persistência:** mantida em memória (dict). Reservas e quadras novas somem ao
  reiniciar/redeploy — aceitável para a demonstração.
- **Testes:** verificação manual (curl + navegador). Sem testes automatizados.

## Backend

### match-service (`match-service/app/main.py`)

- `POST /matches`:
  - valida a quadra via REST no `court-service` (comportamento atual mantido);
  - valida que o horário final é maior que o inicial;
  - verifica, entre as partidas existentes, se há alguma com o mesmo
    `court_id` + `date` e sobreposição de horário → **409**
    `"Ja existe uma reserva nesse horario para esta quadra"`;
  - a checagem + inserção ficam sob um `threading.Lock` para evitar corrida em
    cliques simultâneos.
- `DELETE /matches/{match_id}`:
  - **204** se removida;
  - **404** se não existir.
- Helpers: conversão `HH:MM` → minutos e teste de sobreposição.

### court-service (`court-service/app/main.py`)

- Sem mudanças: `POST /courts` já atende o cadastro de quadras.

### nginx (`frontend/nginx.conf`)

- Sem mudanças: as locations `/courts` e `/matches` já encaminham qualquer método
  HTTP (GET/POST/DELETE) para o serviço correspondente.

## Frontend (`frontend/index.html`)

- Campo de quadra passa de `<select>` para `<input list="quadras-lista">` +
  `<datalist>`, permitindo escolher uma quadra existente ou digitar um id
  inexistente para ver o erro.
- Nova seção **Cadastrar Quadra** (Nome, Endereço, Preço/hora) → `POST /courts`.
- Tabela de partidas ganha coluna **Ações** com botão **Apagar** →
  `DELETE /matches/{id}`.
- Erros (400/409/503) exibidos com o status HTTP e o campo `detail`.

## Documentação

- `README.md` e `entrega2-comunicacao.md`: incluir `DELETE /matches/{id}`, a
  regra de conflito/409, o cadastro de quadras e o teste de id inexistente.

## Implantação

- Redeploy na instância EC2: envio dos arquivos atualizados e
  `docker compose up -d --build`, seguido de validação pelo IP público.
