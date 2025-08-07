# Criação do serviço no linux para rodar o Portal de Blackouts 



## PRÉ-REQUISITOS
* Sistema operacional: Linux (Ubuntu, Debian, CentOS, etc.)
* Python 3.8+ instalado
* Todos os pacotes necessários instalados:
```bash
pip install gradio requests pandas
```

* Arquivo do projeto salvo, por exemplo como:
```bash
/opt/portal_blackouts/portal_blackout.py 
```

##  ESTRUTURA DO PROJETO (recomendada)

```bash
/opt/portal_blackouts/
├── portal_blackout.py
├── portal/           # ambiente virtual Python (opcional mas recomendado)
├── requirements.txt
```

* Para gerar requirements.txt:
```bash
pip freeze > requirements.txt
```

## ETAPA 1: Criar script de execução

Crie o script start.sh

```bash
sudo nano /opt/portal_blackouts/start.sh
```
conteúdo: 

```sh
#!/bin/bash
cd /opt/portal_blackouts/
source /opt/portal_blackouts/portal/bin/activate
python portal_blackout.py
```
Dê permissão de execução:

```bash
chmod +x /opt/portal_blackouts/start.sh
````

## ETAPA 2: Criar o serviço systemd

```init
sudo nano /etc/systemd/system/zabbix-portal.service
```
Conteúdo:

```bash
[Unit]
Description=Portal Gradio de Blackout Zabbix
After=network.target

[Service]
Type=simple
User=root
ExecStart=/opt/portal_blackouts/start.sh
WorkingDirectory=/opt/portal_blackouts/
Restart=on-failure
Environment="PYTHONUNBUFFERED=1"

[Install]
WantedBy=multi-user.target
```

## ETAPA 3: Ativar e iniciar o serviço
