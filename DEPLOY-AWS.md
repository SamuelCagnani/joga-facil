# Deploy na AWS EC2

Guia do deploy já executado do JogaFácil em uma instância Amazon EC2.

## Dados da instância (preenchidos no deploy)

| Item             | Valor                                            |
| ---------------- | ------------------------------------------------ |
| Instance ID      | `i-04e80b438a1ba9efa`                            |
| Nome (tag)       | `jogafacil`                                      |
| Tipo             | `t3.micro`                                       |
| Região           | `us-east-1` (AZ `us-east-1a`)                    |
| AMI              | Ubuntu 24.04 (`ami-0045d7fc2ad003464`)           |
| IP público       | `18.235.0.42`                                    |
| Key pair         | `jogafacil` (chave local `~/.ssh/jogafacil.pem`) |
| Security Group   | `sg-0f7890dcdf1f9388b` (`jogafacil-sg`)          |
| Subnet / VPC     | `subnet-0588f6223891b02e0` / `vpc-019c88cfbb8223edd` |
| Conta AWS        | `473009223019`                                   |

> Atenção: o IP público pode mudar se a instância for parada e iniciada de novo.
> Consulte sempre o IP atual com o comando em "Consultar IP atual".

## URLs de acesso

| Serviço        | URL                              |
| -------------- | -------------------------------- |
| Frontend       | http://18.235.0.42               |
| court-service  | http://18.235.0.42:8001          |
| court-service Swagger | http://18.235.0.42:8001/docs |
| match-service  | http://18.235.0.42:8002          |
| match-service Swagger | http://18.235.0.42:8002/docs |
| SSH            | `ssh -i ~/.ssh/jogafacil.pem ubuntu@18.235.0.42` |

## Passos já executados (deploy)

1. **Instância criada** via AWS CLI na default VPC `us-east-1`, com `user-data` que
   instala Docker, Docker Compose e git:

   ```bash
   aws ec2 run-instances \
     --region us-east-1 \
     --image-id ami-0045d7fc2ad003464 \
     --instance-type t3.micro \
     --key-name jogafacil \
     --security-group-ids sg-0f7890dcdf1f9388b \
     --subnet-id subnet-0588f6223891b02e0 \
     --associate-public-ip-address \
     --user-data file:///tmp/opencode/jogafacil-userdata.sh \
     --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=jogafacil}]'
   ```

2. **Código enviado** por `git clone` do repositório público do GitHub na instância:

   ```bash
   ssh -i ~/.ssh/jogafacil.pem ubuntu@18.235.0.42
   git clone https://github.com/SamuelCagnani/joga-facil.git /home/ubuntu/jogafacil
   ```

3. **Containers subidos** com Docker Compose:

   ```bash
   cd /home/ubuntu/jogafacil
   sudo docker compose up -d --build
   ```

4. **Verificação** feita de fora (da máquina local, via IP público) — todos OK:
   - `GET :8001/health` e `GET :8002/health` → `{"status":"ok",...}`
   - `GET :8001/courts` → 2 quadras de exemplo
   - `POST :8002/matches` com quadra válida → **201** com `court_name` (prova a comunicação REST)
   - `POST :8002/matches` com `court_naoexiste` → **400**
   - `POST :8002/matches` repetindo o horário → **409**
   - Frontend `http://18.235.0.42` → **200**

## Comandos úteis (dentro da instância)

```bash
cd /home/ubuntu/jogafacil

sudo docker ps                 # ver os 3 containers
sudo docker compose logs -f    # acompanhar logs
sudo docker compose restart    # reiniciar
sudo docker compose down       # derrubar os containers
sudo docker compose up -d --build  # atualizar e subir de novo
```

Atualizar o código a partir do GitHub:

```bash
cd /home/ubuntu/jogafacil
git pull
sudo docker compose up -d --build
```

## Consultar IP atual

```bash
aws ec2 describe-instances --region us-east-1 \
  --instance-ids i-04e80b438a1ba9efa \
  --query 'Reservations[0].Instances[0].{State:State.Name,IP:PublicIpAddress}' --output table
```

## Encerramento (faça após a demonstração)

Os dados são apenas em memória e se perdem de qualquer forma, então o recomendado é
**terminar** a instância para não gerar cobrança.

### Opção A — Terminar (recomendado, para de cobrar)

```bash
aws ec2 terminate-instances --region us-east-1 --instance-ids i-04e80b438a1ba9efa
```

Aguarde o estado `terminated`:

```bash
aws ec2 wait instance-terminated --region us-east-1 --instance-ids i-04e80b438a1ba9efa
```

### Opção B — Parar (mantém a instância, mas o volume EBS continua com custo pequeno)

```bash
aws ec2 stop-instances --region us-east-1 --instance-ids i-04e80b438a1ba9efa
```

> Ao reiniciar (opção B), o IP público pode mudar se não houver Elastic IP. Consulte o
> novo IP com o comando "Consultar IP atual" acima.

### Não esqueça de conferir

```bash
aws ec2 describe-instances --region us-east-1 \
  --filters Name=instance-state-name,Values=running \
  --query 'Reservations[].Instances[].{ID:InstanceId,IP:PublicIpAddress}' --output table
```

Se não aparecer nada, não há instância rodando/cobrando.

## Observações de segurança / rede

- O Security Group `jogafacil-sg` libera: `22` (SSH, restrita ao IP do desenvolvedor — muda com
  frequência, veja a seção "Se o SSH parar de funcionar" abaixo),
  `80`, `8001` e `8002` (0.0.0.0/0).
- Os serviços rodam na mesma rede do Docker Compose; o `match-service` fala com o
  `court-service` por `http://court-service:8001` (DNS interno do Compose).

### Se o SSH parar de funcionar (Connection timed out)

Normalmente é porque o **seu IP público mudou** e o SG só libera o IP antigo. Confirme:

```bash
curl -s https://api.ipify.org; echo
aws ec2 describe-security-groups --region us-east-1 --group-ids sg-0f7890dcdf1f9388b \
  --query 'SecurityGroups[0].IpPermissions[?FromPort==`22`].IpRanges[].CidrIp' --output json
```

Se o IP não estiver na lista, libere o IP atual e, em seguida, remova a regra antiga:

```bash
NOVO_IP=$(curl -s https://api.ipify.org)

aws ec2 authorize-security-group-ingress --region us-east-1 \
  --group-id sg-0f7890dcdf1f9388b --protocol tcp --port 22 \
  --cidr "$NOVO_IP/32"

# opcional: remover a regra antiga (troque pelo IP que apareceu como desatualizado)
aws ec2 revoke-security-group-ingress --region us-east-1 \
  --group-id sg-0f7890dcdf1f9388b --protocol tcp --port 22 \
  --cidr "IP_ANTIGO/32"
```

Teste novamente:

```bash
ssh -i ~/.ssh/jogafacil.pem ubuntu@18.235.0.42
```
