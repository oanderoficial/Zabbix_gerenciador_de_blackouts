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

```bash
# Recarrega os serviços
sudo systemctl daemon-reexec
sudo systemctl daemon-reload

# Habilita para iniciar no boot
sudo systemctl enable zabbix-portal.service

# Inicia o serviço manualmente
sudo systemctl start zabbix-portal.service
```

## ETAPA 4: Verificar status e logs

```bash
# Verifica se está rodando
sudo systemctl status zabbix-portal.service

# Ver logs ao vivo
journalctl -u zabbix-portal.service -f
```

## Acessar o portal

* Se estiver rodando com server_name="0.0.0.0" e server_port=8080
* Acesse de outro dispositivo da rede:

```bash
http://<ip_do_servidor>:8080
```
