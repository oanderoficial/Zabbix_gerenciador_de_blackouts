import gradio as gr
import requests
import json
from datetime import datetime
import pandas as pd

# Configurações de instâncias Zabbix
ZABBIX_INSTANCES = {
    "Zabbix Produção": {
        "url": "http://192.168.0.31/zabbix/api_jsonrpc.php",
        "user": "Admin",
        "password": "zabbix",
        "usar_username": False  # Zabbix 5
    },
    "Zabbix Homologação": {
        "url": "http://192.168.0.31/zabbix/api_jsonrpc.php",
        "user": "Admin",
        "password": "zabbix",
        "usar_username": False  # Zabbix 5
    },
    "Zabbix Desenvolvimento": {
        "url": "http://192.168.0.31/zabbix/api_jsonrpc.php",
        "user": "Admin",
        "password": "zabbix",
        "usar_username": True  # Zabbix 7
    }
}
headers = {'Content-Type': 'application/json'}

# Variáveis globais
zabbix_token = None
zabbix_instance = None
host_map = {}

# Funções de API

def zabbix_authenticate(url, user, password, usar_username=False):
    field_name = "username" if usar_username else "user"
    payload = {
        "jsonrpc": "2.0",
        "method": "user.login",
        "params": {
            field_name: user,
            "password": password
        },
        "id": 1
    }
    response = requests.post(url, headers=headers, data=json.dumps(payload))
    result = response.json()
    if 'result' in result:
        return result['result']
    else:
        raise Exception(result.get('error'))
    
def zabbix_request(url, token, method, params):
    payload = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params,
        "auth": token,
        "id": 1
    }
    response = requests.post(url, headers=headers, data=json.dumps(payload))
    result = response.json()
    if 'result' in result:
        return result['result']
    else:
        raise Exception(result.get('error'))

# Funções de interface

def autenticar(instancia):
    global zabbix_token, zabbix_instance
    try:
        config = ZABBIX_INSTANCES[instancia]
        token = zabbix_authenticate(
            config["url"],
            config["user"],
            config["password"],
            config.get("usar_username", False) 
        )
        zabbix_token = token
        zabbix_instance = config
        carregar_hosts()  # atualiza host_map ao trocar de instância
        return f"Autenticado em {instancia}"
    except Exception as e:
        return f"Erro na autenticação: {str(e)}"


def carregar_hosts():
    global host_map
    hosts = zabbix_request(zabbix_instance["url"], zabbix_token, "host.get", {"output": ["hostid", "name"]})
    host_map = {h["name"]: h["hostid"] for h in hosts}
    return list(host_map.keys())

def filtrar_hosts(filtro):
    if not filtro:
        return gr.update(choices=list(host_map.keys()))
    return gr.update(choices=[host for host in host_map if filtro.lower() in host.lower()])

def criar_blackout(nome, descricao, hosts_selecionados, hostnames_texto, inicio, fim, manter_dados):
    try:
        host_ids = [host_map[h] for h in hosts_selecionados if h in host_map]

        if hostnames_texto:
            for h in hostnames_texto.split(","):
                h = h.strip()
                if h in host_map:
                    host_ids.append(host_map[h])
                else:
                    raise Exception(f"Hostname '{h}' não encontrado.")

        if not host_ids:
            raise Exception("Nenhum host válido selecionado.")

        time_from = int(inicio)
        time_till = int(fim)

        tipo = 0 if manter_dados else 1
        params = {
            "name": nome,
            "description": descricao,
            "active_since": time_from,
            "active_till": time_till,
            "hostids": host_ids,
            "maintenance_type": tipo,
            "timeperiods": [{"timeperiod_type": 0, "period": time_till - time_from}]
        }

        zabbix_request(zabbix_instance["url"], zabbix_token, "maintenance.create", params)
        return f"Blackout '{nome}' criado com sucesso."
    except Exception as e:
        return f"Erro: {str(e)}"

def listar_blackouts():
    try:
        blackouts = zabbix_request(zabbix_instance["url"], zabbix_token, "maintenance.get", {
            "output": ["maintenanceid", "name", "active_since", "active_till"]
        })
        now = int(datetime.now().timestamp())
        tabela = [
            {
                "ID": b["maintenanceid"],
                "Nome": b["name"],
                "Início": datetime.fromtimestamp(int(b["active_since"])).strftime("%Y-%m-%d %H:%M"),
                "Fim": datetime.fromtimestamp(int(b["active_till"])).strftime("%Y-%m-%d %H:%M"),
                "Status": "Ativo" if int(b["active_since"]) <= now <= int(b["active_till"]) else ("Futuro" if now < int(b["active_since"]) else "Encerrado")
            } for b in blackouts
        ]
        return pd.DataFrame(tabela)
    except Exception as e:
        return pd.DataFrame([{"Erro": str(e)}])


#frontend
estilo_css = """
footer {display: none !important;}

.gradio-container {
    padding-bottom: 60px; /* espaço reservado pro footer */
}

/* Rodapé fixo personalizado */
.custom-footer {
    position: fixed;
    bottom: 0;
    left: 0;
    width: 100%;
    background-color: #222;
    color: white;
    text-align: center;
    padding: 10px 0;
    font-size: 14px;
    font-family: Arial, sans-serif;
    z-index: 9999;
}

/* Estiliza o link do GitHub */
.custom-footer a {
    color: #007bff;
    text-decoration: none;
    font-weight: bold;
}
.custom-footer a:hover {
    text-decoration: underline;
}
"""

custom_footer = """
<div class="custom-footer">
    Desenvolvido por Anderson Bezerra Silva |
    <a href="https://github.com/oanderoficial" target="_blank">GitHub</a>
</div>
"""

# HTML do footer personalizado
custom_footer = """
<div class="custom-footer">
    Desenvolvido por Anderson Bezerra Silva | 
    <a href="https://github.com/oanderoficial" target="_blank">GitHub</a>
</div>
"""

with gr.Blocks(css=estilo_css) as demo:
    instancia = gr.Dropdown(label="Instância Zabbix", choices=list(ZABBIX_INSTANCES.keys()))
    status = gr.Textbox(label="Status de Autenticação", interactive=False)
    btn_auth = gr.Button("Autenticar")

    btn_auth.click(autenticar, inputs=instancia, outputs=status)

    with gr.Tabs():
        with gr.TabItem("Criar Blackout"):
            nome = gr.Textbox(label="Nome do Blackout")
            descricao = gr.Textbox(label="Descrição")
            search_host = gr.Textbox(label="Buscar Hosts")
            hosts = gr.CheckboxGroup(choices=[], label="Hosts Disponíveis")
            search_host.change(filtrar_hosts, inputs=search_host, outputs=hosts)
            btn_carregar = gr.Button("Carregar Hosts")
            hostnames_manual = gr.Textbox(label="Hostnames (manual, separados por vírgula)")
            data_ini = gr.DateTime(label="Início")
            data_fim = gr.DateTime(label="Fim")
            manter = gr.Checkbox(label="Manter coleta de dados", value=True)
            resultado = gr.Textbox(label="Resultado", interactive=False)
            btn_criar = gr.Button("Criar Blackout")

            btn_carregar.click(lambda: gr.update(choices=carregar_hosts()), outputs=hosts)
            btn_criar.click(criar_blackout, inputs=[nome, descricao, hosts, hostnames_manual, data_ini, data_fim, manter], outputs=resultado)

        with gr.TabItem("Visualizar Blackouts"):
            btn_listar = gr.Button("Atualizar Lista")
            tabela_blackouts = gr.Dataframe(headers=["ID", "Nome", "Início", "Fim", "Status"], interactive=False)
            btn_listar.click(fn=listar_blackouts, outputs=tabela_blackouts)

            # Adiciona o Footer na Interface
        gr.Markdown(custom_footer)

demo.launch(share=False, show_api=False, server_name="0.0.0.0", server_port=8080)
