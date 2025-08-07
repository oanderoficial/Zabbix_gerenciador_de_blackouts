import gradio as gr
import requests
import json
from datetime import datetime
import pandas as pd

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

def login_action(usuario, senha, instancia, state):
    try:
        config = ZABBIX_INSTANCES[instancia]
        token = zabbix_authenticate(config["url"], usuario, senha, usar_username=config.get("usar_username", False))
        host_map = {
            h["name"]: h["hostid"]
            for h in zabbix_request(config["url"], token, "host.get", {"output": ["hostid", "name"]})
        }

        state["token"] = token
        state["config"] = config
        state["host_map"] = host_map
        state["usuario"] = usuario

        return gr.update(visible=False), gr.update(visible=True), "", True
    except Exception as e:
        return gr.update(visible=True), gr.update(visible=False), f"Erro de login: {str(e)}", False

def carregar_hosts(state):
    return list(state.get("host_map", {}).keys())

def filtrar_hosts(filtro, state):
    host_map = state.get("host_map", {})
    if not filtro:
        return gr.update(choices=list(host_map.keys()))
    return gr.update(choices=[host for host in host_map if filtro.lower() in host.lower()])

def criar_blackout(change_id, descricao, hosts_selecionados, hostnames_texto, inicio, fim, manter_dados, state):
    try:
        usuario = state.get("usuario", "desconhecido")

        if not change_id.strip():
            raise Exception("Número da Change é obrigatório.")

        nome = f"ID: {usuario} Change: {change_id.strip()} - {descricao.strip()}"
        descricao_final = f"Criado por ID: {usuario} referente à change {change_id.strip()}."

        host_map = state["host_map"]
        zabbix_token = state["token"]
        zabbix_instance = state["config"]

        host_ids = [host_map[h] for h in hosts_selecionados if h in host_map]

        if hostnames_texto:
            for h in hostnames_texto.split(","):
                h = h.strip()
                if h in host_map:
                    host_ids.append(host_map[h])
                else:
                    raise Exception(f"Hostname '{h}' não encontrado.")

        host_ids = list(set(host_ids))
        if not host_ids:
            raise Exception("Nenhum host válido selecionado.")

        time_from = int(inicio)
        time_till = int(fim)

        if time_from >= time_till:
            raise Exception("A data de início deve ser anterior à data de fim.")

        tipo = 0 if manter_dados else 1
        params = {
            "name": nome,
            "description": descricao_final,
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

def listar_blackouts(state):
    try:
        token = state["token"]
        config = state["config"]
        blackouts = zabbix_request(config["url"], token, "maintenance.get", {
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

# Estilo e footer
estilo_css = """
footer {display: none !important;}
.gradio-container { padding-bottom: 60px; }
.custom-footer {
    position: fixed;
    bottom: 0;
    left: 0;
    width: 100%;
    background-color: #222;
    color: white;
    text-align: center;
    padding: 7px 0;
    font-size: 14px;
    font-family: Arial, sans-serif;
    z-index: 9999;
}
.custom-footer a {
    color: #007bff;
    text-decoration: none;
    font-weight: bold;
}
.custom-footer a:hover { text-decoration: underline; }
"""

custom_footer = """
<div class=\"custom-footer\">
    Desenvolvido por T-systems @oanderoficial |
    <a href=\"https://github.com/oanderoficial\" target=\"_blank\">GitHub</a>
</div>
"""

# Interface Gradio
with gr.Blocks(css=estilo_css) as demo:
    state = gr.State({})
    autenticado = gr.State(False)

    with gr.Column(visible=True) as login_area:
        instancia = gr.Dropdown(label="Instância Zabbix", choices=list(ZABBIX_INSTANCES.keys()))
        usuario = gr.Textbox(label="Usuário Zabbix")
        senha = gr.Textbox(label="Senha", type="password")
        msg_login = gr.Textbox(interactive=False)
        btn_login = gr.Button("Entrar")

    with gr.Column(visible=False) as main_area:
        with gr.Tabs():
            with gr.TabItem("Criar Blackout"):
                change_id = gr.Textbox(label="Número da mudança (obrigatório, ex: 1571256789)")
                descricao = gr.Textbox(label="Descrição")
                search_host = gr.Textbox(label="Buscar Hosts")
                hosts = gr.CheckboxGroup(choices=[], label="Hosts Disponíveis")
                search_host.change(filtrar_hosts, inputs=[search_host, state], outputs=hosts)
                btn_carregar = gr.Button("Carregar Hosts")
                hostnames_manual = gr.Textbox(label="Hostnames (manual, separados por vírgula)")
                data_ini = gr.DateTime(label="Início")
                data_fim = gr.DateTime(label="Fim")
                manter = gr.Checkbox(label="Manter coleta de dados", value=True)
                resultado = gr.Textbox(label="Resultado", interactive=False)
                btn_criar = gr.Button("Criar Blackout")

                btn_carregar.click(lambda state: gr.update(choices=carregar_hosts(state)), inputs=state, outputs=hosts)
                btn_criar.click(
                    criar_blackout,
                    inputs=[change_id, descricao, hosts, hostnames_manual, data_ini, data_fim, manter, state],
                    outputs=resultado
                )

            with gr.TabItem("Visualizar Blackouts"):
                btn_listar = gr.Button("Atualizar Lista")
                tabela_blackouts = gr.Dataframe(headers=["ID", "Nome", "Início", "Fim", "Status"], interactive=False)
                btn_listar.click(fn=listar_blackouts, inputs=state, outputs=tabela_blackouts)

        gr.Markdown(custom_footer)

    btn_login.click(
        login_action,
        inputs=[usuario, senha, instancia, state],
        outputs=[login_area, main_area, msg_login, autenticado]
    )

demo.launch(share=False, show_api=False, server_name="0.0.0.0", server_port=8080)
