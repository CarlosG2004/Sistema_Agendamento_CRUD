# AgendaFácil — Sistema de Agendamento de Serviços

Plataforma de agendamentos para pequenos negócios: barbearias, clínicas de estética, petshops, personal trainers etc.

---

## Setup e Execução

### 1. Pré-requisitos

- Python 3.10+
- pip

### 2. Instalação

```bash
# Clone ou extraia o projeto
cd agendamento

# Crie e ative o ambiente virtual
python -m venv venv
source venv/bin/activate        # Linux/Mac
venv\Scripts\activate           # Windows

# Instale as dependências
pip install -r requirements.txt
```

### 3. Configurar variáveis de ambiente

```bash
cp .env.example .env
# Edite o .env com sua SECRET_KEY
```

### 4. Banco de dados

```bash
python manage.py migrate
```

### 5. (Opcional) Criar superusuário para o admin

```bash
python manage.py createsuperuser
```

### 6. Rodar o servidor

```bash
python manage.py runserver
```

Acesse: **http://127.0.0.1:8000**

---

##  Arquitetura

```
agendamento/
├── agendamento_project/   # Configurações do projeto Django
│   ├── settings.py
│   └── urls.py
├── core/                  # App principal
│   ├── models.py          # Usuario, Servico, Disponibilidade, Agendamento
│   ├── views.py           # Lógica de negócio + endpoints da API
│   ├── urls.py            # Roteamento
│   ├── admin.py           # Painel administrativo
│   └── templates/core/    # Templates HTML
├── manage.py
├── requirements.txt
└── .env.example
```

### Modelo de Dados

| Modelo | Descrição |
|--------|-----------|
| `Usuario` | Estende AbstractUser; campo `tipo` = `prestador` ou `cliente` |
| `Servico` | Pertence a um prestador; tem nome, duração, preço e flag `ativo` |
| `Disponibilidade` | Janela de horário por dia da semana de um prestador |
| `Agendamento` | Vincula cliente + serviço + data/hora; status: `pendente`, `confirmado`, `cancelado` |

---

##  Endpoints da API

A API responde sempre em **JSON**. A autenticação é via **sessão Django** (cookie `sessionid`).

###  Autenticação (RF-01)

#### Registrar usuário

**POST** `/api/auth/registro/`

Requisição:
```json
{
  "email": "prestador@teste.com",
  "password": "senha123",
  "tipo": "prestador",
  "first_name": "João",
  "last_name": "Silva",
  "telefone": "(51) 99999-0001",
  "bio": "Barbeiro especialista"
}
```

Resposta `201`:
```json
{
  "mensagem": "Usuário criado com sucesso.",
  "usuario": {
    "id": 1,
    "email": "prestador@teste.com",
    "nome": "João Silva",
    "tipo": "prestador"
  }
}
```

Erros possíveis:
- `400` — Campo obrigatório ausente ou e-mail já cadastrado
- `400` — `tipo` inválido (deve ser `"prestador"` ou `"cliente"`)

---

#### Login

**POST** `/api/auth/login/`

Requisição:
```json
{
  "email": "prestador@teste.com",
  "password": "senha123"
}
```

Resposta `200`:
```json
{
  "mensagem": "Login realizado com sucesso.",
  "usuario": {
    "id": 1,
    "email": "prestador@teste.com",
    "nome": "João Silva",
    "tipo": "prestador"
  }
}
```

Erros:
- `401` — Credenciais inválidas

---

#### Logout

**GET** `/api/auth/logout/`  *(requer autenticação)*

Resposta `200`:
```json
{ "mensagem": "Logout realizado com sucesso." }
```

---

###  Serviços (RF-02) — apenas Prestador

#### Listar serviços do prestador autenticado

**GET** `/api/servicos/`

Resposta `200`:
```json
[
  {
    "id": 1,
    "nome": "Corte masculino",
    "descricao": "Corte simples",
    "duracao_minutos": 30,
    "preco": "50.00",
    "ativo": true
  }
]
```

---

#### Criar serviço

**POST** `/api/servicos/criar/`

Requisição:
```json
{
  "nome": "Serviço A",
  "descricao": "Descrição opcional",
  "duracao_minutos": 30,
  "preco": "50.00",
  "ativo": true
}
```

Resposta `201`:
```json
{
  "mensagem": "Serviço criado.",
  "servico": { "id": 1, "nome": "Serviço A", "duracao_minutos": 30, "preco": "50.00", "ativo": true }
}
```

---

#### Editar serviço

**PUT** `/api/servicos/<id>/editar/`

Requisição (campos parciais aceitos):
```json
{
  "nome": "Serviço A atualizado",
  "ativo": false
}
```

Resposta `200`:
```json
{ "mensagem": "Serviço atualizado.", "id": 1 }
```

---

#### Deletar serviço

**DELETE** `/api/servicos/<id>/deletar/`

Resposta `200`:
```json
{ "mensagem": "Serviço removido." }
```

Erro `400` — se houver agendamentos futuros confirmados:
```json
{
  "erro": "Não é possível deletar: existem agendamentos futuros confirmados. Desative o serviço."
}
```

---

###  Disponibilidade (RF-03) — apenas Prestador

#### Listar disponibilidade

**GET** `/api/disponibilidade/`

Resposta `200`:
```json
[
  {
    "id": 1,
    "dia_semana": 0,
    "dia_semana_nome": "Segunda-feira",
    "hora_inicio": "09:00",
    "hora_fim": "18:00"
  }
]
```

Dias da semana: `0`=Segunda, `1`=Terça, `2`=Quarta, `3`=Quinta, `4`=Sexta, `5`=Sábado, `6`=Domingo

---

#### Cadastrar janela de horário

**POST** `/api/disponibilidade/criar/`

Requisição:
```json
{
  "dia_semana": 0,
  "hora_inicio": "09:00",
  "hora_fim": "18:00"
}
```

Resposta `201`:
```json
{
  "mensagem": "Disponibilidade cadastrada.",
  "disponibilidade": {
    "id": 1,
    "dia_semana": 0,
    "dia_semana_nome": "Segunda-feira",
    "hora_inicio": "09:00",
    "hora_fim": "18:00"
  }
}
```

Erro `400` — conflito de horário:
```json
{ "erro": "Conflito com janela existente: 09:00-18:00" }
```

---

#### Remover janela

**DELETE** `/api/disponibilidade/<id>/deletar/`

Resposta `200`:
```json
{ "mensagem": "Disponibilidade removida." }
```

---

###  Agendamentos (RF-04)

#### Listar agendamentos

**GET** `/api/agendamentos/`  *(requer autenticação)*

- Prestador vê os agendamentos dos seus serviços
- Cliente vê apenas os seus próprios agendamentos

Filtros opcionais via query string:
- `?status=pendente` | `confirmado` | `cancelado`
- `?data=2025-07-14`

Exemplo: `GET /api/agendamentos/?status=pendente&data=2025-07-14`

Resposta `200`:
```json
[
  {
    "id": 1,
    "servico": "Corte masculino",
    "servico_id": 1,
    "prestador": "João Silva",
    "cliente": "Maria Souza",
    "data_hora": "2025-07-14 10:00",
    "status": "pendente",
    "observacao": ""
  }
]
```

---

#### Criar agendamento *(apenas Cliente)*

**POST** `/api/agendamentos/criar/`

Requisição:
```json
{
  "servico_id": 1,
  "data_hora": "2025-07-14 10:00",
  "observacao": "Primeira vez"
}
```

Resposta `201`:
```json
{
  "mensagem": "Agendamento criado com sucesso.",
  "agendamento": {
    "id": 1,
    "servico": "Corte masculino",
    "data_hora": "2025-07-14 10:00",
    "status": "pendente"
  }
}
```

Erros `400`:
- Horário fora da disponibilidade do prestador
- Conflito com agendamento existente

---

#### Confirmar ou cancelar agendamento

**PATCH** `/api/agendamentos/<id>/acao/`

Requisição:
```json
{ "acao": "confirmar" }
```
ou
```json
{ "acao": "cancelar" }
```

- Prestador pode: `confirmar` ou `cancelar` qualquer agendamento
- Cliente pode: apenas `cancelar` agendamentos com status `pendente`
- Ninguém pode alterar agendamento `cancelado`

Resposta `200`:
```json
{ "mensagem": "Agendamento confirmado com sucesso.", "status": "confirmado" }
```

Erros:
- `400` — Agendamento cancelado não pode ser alterado
- `400` — Cliente tentando cancelar agendamento confirmado
- `403` — Cliente tentando confirmar agendamento

---

###  Endpoints Públicos (RF-05)

#### Listar prestadores *(sem autenticação)*

**GET** `/api/prestadores/`

Resposta `200`:
```json
[
  {
    "id": 1,
    "first_name": "João",
    "last_name": "Silva",
    "email": "joao@teste.com",
    "bio": "Barbeiro especialista",
    "nome_completo": "João Silva",
    "servicos_ativos": [
      { "id": 1, "nome": "Corte masculino", "duracao_minutos": 30, "preco": "50.00" }
    ]
  }
]
```

---

#### Serviços de um prestador específico *(sem autenticação)*

**GET** `/api/prestadores/<id>/servicos/`

Resposta `200`:
```json
{
  "prestador": { "id": 1, "nome": "João Silva", "bio": "Barbeiro especialista" },
  "servicos": [
    { "id": 1, "nome": "Corte masculino", "descricao": "", "duracao_minutos": 30, "preco": "50.00" }
  ]
}
```

---

##  Roteiro de Teste (Professor)

```bash
BASE=http://127.0.0.1:8000
# Use -c cookie.txt em todos os comandos para manter a sessão

# 1. Registrar prestador
curl -s -X POST $BASE/api/auth/registro/ -H "Content-Type: application/json" \
  -d '{"email":"prestador@teste.com","password":"senha1234","tipo":"prestador","first_name":"João","last_name":"Silva"}'

# 2. Registrar cliente
curl -s -X POST $BASE/api/auth/registro/ -H "Content-Type: application/json" \
  -d '{"email":"cliente@teste.com","password":"senha1234","tipo":"cliente","first_name":"Maria","last_name":"Souza"}'

# 3. Login como prestador
curl -s -c cookie.txt -X POST $BASE/api/auth/login/ -H "Content-Type: application/json" \
  -d '{"email":"prestador@teste.com","password":"senha1234"}'

# 4. Criar Serviço A
curl -s -b cookie.txt -X POST $BASE/api/servicos/criar/ -H "Content-Type: application/json" \
  -H "X-CSRFToken: $(grep csrftoken cookie.txt | awk '{print $7}')" \
  -d '{"nome":"Serviço A","duracao_minutos":30,"preco":"50.00"}'

# 5. Criar Serviço B
curl -s -b cookie.txt -X POST $BASE/api/servicos/criar/ -H "Content-Type: application/json" \
  -H "X-CSRFToken: $(grep csrftoken cookie.txt | awk '{print $7}')" \
  -d '{"nome":"Serviço B","duracao_minutos":60,"preco":"100.00"}'

# 6. Cadastrar disponibilidade (Segunda=0 a Sexta=4, 09:00-18:00)
for dia in 0 1 2 3 4; do
  curl -s -b cookie.txt -X POST $BASE/api/disponibilidade/criar/ \
    -H "Content-Type: application/json" \
    -H "X-CSRFToken: $(grep csrftoken cookie.txt | awk '{print $7}')" \
    -d "{\"dia_semana\":$dia,\"hora_inicio\":\"09:00\",\"hora_fim\":\"18:00\"}"
done

# 7. Login como cliente
curl -s -c cookie_cliente.txt -X POST $BASE/api/auth/login/ -H "Content-Type: application/json" \
  -d '{"email":"cliente@teste.com","password":"senha1234"}'

# 8. Criar agendamento válido (Serviço A, segunda às 10h)
# Altere a data para uma segunda-feira válida
curl -s -b cookie_cliente.txt -X POST $BASE/api/agendamentos/criar/ \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: $(grep csrftoken cookie_cliente.txt | awk '{print $7}')" \
  -d '{"servico_id":1,"data_hora":"2025-07-14 10:00"}'

# 9. Agendamento conflitante (deve falhar)
curl -s -b cookie_cliente.txt -X POST $BASE/api/agendamentos/criar/ \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: $(grep csrftoken cookie_cliente.txt | awk '{print $7}')" \
  -d '{"servico_id":2,"data_hora":"2025-07-14 10:15"}'

# 10. Agendamento válido (Serviço B, 10h30)
curl -s -b cookie_cliente.txt -X POST $BASE/api/agendamentos/criar/ \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: $(grep csrftoken cookie_cliente.txt | awk '{print $7}')" \
  -d '{"servico_id":2,"data_hora":"2025-07-14 10:30"}'

# 11. Prestador confirma agendamento 1
curl -s -b cookie.txt -X PATCH $BASE/api/agendamentos/1/acao/ \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: $(grep csrftoken cookie.txt | awk '{print $7}')" \
  -d '{"acao":"confirmar"}'

# 12. Cliente tenta cancelar confirmado (deve falhar)
curl -s -b cookie_cliente.txt -X PATCH $BASE/api/agendamentos/1/acao/ \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: $(grep csrftoken cookie_cliente.txt | awk '{print $7}')" \
  -d '{"acao":"cancelar"}'

# 13. Prestador cancela agendamento 2
curl -s -b cookie.txt -X PATCH $BASE/api/agendamentos/2/acao/ \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: $(grep csrftoken cookie.txt | awk '{print $7}')" \
  -d '{"acao":"cancelar"}'

# 14. Filtrar por status cancelado
curl -s -b cookie.txt $BASE/api/agendamentos/?status=cancelado

# 15. Cliente tenta endpoint de prestador (deve retornar 403)
curl -s -b cookie_cliente.txt $BASE/api/servicos/
```

---

##  Regras de Negócio

| Regra | Implementação |
|-------|---------------|
| E-mail único | `unique=True` no model + validação na view |
| Serviço inativo não aparece publicamente | `filter(ativo=True)` em endpoints públicos |
| Não deletar serviço com agendamentos futuros confirmados | `Servico.pode_ser_deletado()` |
| Sem sobreposição de disponibilidade | `Disponibilidade.clean()` |
| Horário deve cair em janela de disponibilidade | `Agendamento.clean()` |
| Sem conflito de agendamentos | `Agendamento.clean()` com verificação de sobreposição |
| Cliente só cancela pendentes | Verificação em `api_agendamentos_acao` |
| Agendamento cancelado é imutável | Verificação de status antes de qualquer ação |
| Separação de perfis | Decorators `requer_prestador` / `requer_cliente` + verificações nas views |

---

##  Tecnologias

- **Django 4.2** — Framework principal
- **SQLite** — Banco de dados (padrão, sem configuração extra)
- **ORM Django** — Todas as queries (sem SQL raw)
- **Sessões Django** — Autenticação stateful
- **HTML5 + CSS3 (puro)** — Interface sem frameworks externos
