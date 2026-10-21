# CoreAxis Deploy

**Plataforma de provisionamento de infraestrutura via terminal.**  
Instala e configura serviços como Grafana e Zabbix automaticamente — sem precisar saber Docker ou comandos Linux avançados.

---

## O que este projeto faz?

Você responde algumas perguntas simples no terminal (nome, porta, senha) e o sistema:

- Gera os arquivos de configuração automaticamente
- Sobe os containers Docker
- Registra o serviço no banco de dados
- Exibe a URL de acesso pronta para usar

---

## Requisitos

- Ubuntu Server 22.04 ou 24.04 (ou Debian 12)
- Acesso root (`sudo`)
- Conexão com a internet (para baixar as imagens Docker)

> O script de instalação cuida de instalar Python, Docker, MariaDB e tudo mais automaticamente.

---

## Instalação — passo a passo

### Modo rápido (recomendado para VM nova)

Em uma VM Ubuntu Server limpa, execute **apenas este comando**:

```bash
curl -fsSL https://raw.githubusercontent.com/georgeangra/coreaxis-deploy/main/bootstrap.sh | sudo bash
```

Ele faz tudo automaticamente:
- Atualiza o sistema operacional
- Instala Git, Python, Docker, MariaDB
- Baixa o projeto do GitHub
- Configura o banco de dados
- Deixa tudo pronto para usar

### Modo manual (passo a passo)

```bash
# 1. Conecte-se ao servidor
ssh usuario@IP_DO_SERVIDOR

# 2. Instale o Git
sudo apt install -y git

# 3. Baixe o projeto
git clone https://github.com/georgeangra/coreaxis-deploy.git
cd coreaxis-deploy

# 4. Execute o instalador
sudo bash install.sh
```

O script vai instalar e configurar automaticamente:

| Componente     | O que faz                              |
|----------------|----------------------------------------|
| Python 3       | Linguagem do sistema                   |
| Docker Engine  | Executa os containers dos serviços     |
| Docker Compose | Orquestra múltiplos containers         |
| MariaDB        | Banco de dados do CoreAxis Deploy      |

Ao final da instalação você verá:

```
╔══════════════════════════════════════════════╗
║         INSTALAÇÃO CONCLUÍDA COM SUCESSO     ║
╚══════════════════════════════════════════════╝

  Para iniciar o sistema:
    bash run.sh
```

---

## Como usar

### Iniciar o sistema

```bash
bash run.sh
```

O menu principal será exibido:

```
╭──────────────────────────────────╮
│       COREAXIS DEPLOY v1.0.0     │
╰──────────────────────────────────╯
  [1]  Implantar Grafana
  [2]  Implantar Zabbix
  [3]  Listar Serviços
  [4]  Ver Status dos Containers
  [5]  Ver Logs
  [6]  Remover Serviço
  [7]  Sair
```

### Implantar o Grafana

1. Digite `1` e pressione Enter
2. Preencha os campos:

```
Nome da Instância [Grafana-Lab]: Grafana-Lab   ← aperte Enter para aceitar o padrão
Porta [3000]: 3000
Usuário Administrador [admin]: admin
Senha Administrador: sua_senha_aqui
```

3. Aguarde a instalação e acesse no navegador:

```
http://IP_DO_SERVIDOR:3000
```

### Implantar o Zabbix

1. Digite `2` e pressione Enter
2. Preencha os campos:

```
Nome da Instância [Zabbix-Lab]: Zabbix-Lab
Porta Frontend [8080]: 8080
Porta MariaDB [3307]: 3307
Senha do Banco: sua_senha_aqui
Usuário Administrador [Admin]: Admin
```

3. Aguarde e acesse no navegador:

```
http://IP_DO_SERVIDOR:8080
```

Login padrão do Zabbix: usuário `Admin`, senha `zabbix`

> O Zabbix leva alguns minutos para inicializar o banco na primeira vez. Se aparecer erro de banco, aguarde 2 minutos e recarregue a página.

---

## Comandos úteis

### Ver serviços implantados

No menu, escolha a opção `3`.

### Ver containers em execução

```bash
sudo docker ps
```

### Ver logs de um container

No menu, escolha a opção `5`, depois informe o ID do serviço.

### Remover um serviço

No menu, escolha a opção `6`, informe o ID e confirme se deseja remover os volumes (dados).

---

## Estrutura do projeto

```
coreaxis-deploy/
├── install.sh          ← Instalador automático (execute primeiro)
├── run.sh              ← Inicia o sistema no dia a dia
├── main.py             ← Menu principal
├── requirements.txt    ← Dependências Python
├── .env.example        ← Modelo de configuração
│
├── config/             ← Configurações centralizadas
├── database/           ← Banco de dados (ORM + modelos)
├── deployers/          ← Módulos de cada serviço
│   ├── grafana.py
│   └── zabbix.py
├── docker/             ← Arquivos docker-compose gerados
├── utils/              ← Utilitários (Docker, logs, validações)
└── logs/               ← Logs da aplicação
```

---

## Adicionar novos serviços

O sistema usa arquitetura de plugins. Para adicionar um serviço:

1. Crie `deployers/nome_servico.py` herdando `BaseDeployer`
2. Implemente os métodos: `service_name`, `display_name`, `collect_config`, `deploy`, `remove`
3. Registre em `DEPLOYERS` no `main.py`

Serviços planejados para próximas versões:

- Portainer
- Uptime Kuma
- GLPI
- Wazuh
- Prometheus + Alertmanager
- Nginx Proxy Manager
- SonarQube
- GitLab

---

## Solução de problemas

### "Permission denied" no Docker

```bash
sudo usermod -aG docker $USER
newgrp docker
```

### Docker não está ativo

```bash
sudo systemctl start docker
```

### MariaDB não conecta

```bash
sudo systemctl start mariadb
```

Verifique as credenciais no arquivo `.env`.

### Porta já está em uso

Escolha uma porta diferente quando o sistema solicitar (ex: `3001` em vez de `3000`).

---

## Tecnologias utilizadas

| Tecnologia     | Versão   | Uso                          |
|----------------|----------|------------------------------|
| Python         | 3.12+    | Linguagem principal          |
| Rich           | 13+      | Interface colorida no terminal|
| SQLAlchemy     | 2.0+     | ORM para o banco de dados    |
| MariaDB        | 10.6+    | Banco de dados               |
| Docker         | 24+      | Execução dos serviços        |
| Docker Compose | v2       | Orquestração dos containers  |
| PyYAML         | 6+       | Geração dos docker-compose   |

---

## Roadmap

- **v1.0** — MVP terminal: Grafana + Zabbix ✅
- **v1.1** — Portainer, Uptime Kuma, GLPI
- **v1.2** — Wazuh, Prometheus, Nginx Proxy Manager
- **v2.0** — Interface web (FastAPI + React)

---

## Licença

Desenvolvido por [CoreAxis Tech](https://github.com/georgeangra)
