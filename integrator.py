import sys
import requests
import json
from PyQt5.QtCore import Qt, QDateTime
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QLabel, QFormLayout, QLineEdit,
    QComboBox, QMessageBox, QDateTimeEdit, QCheckBox, QListWidget, QAbstractItemView, QTableWidget,
    QTableWidgetItem, QHeaderView, QHBoxLayout
)


# Configurações de múltiplas instâncias do Zabbix
ZABBIX_INSTANCES = {
    "Zabbix Principal": {
        "url": "http://192.168.0.31/zabbix/api_jsonrpc.php",
        "username": "Admin",
        "password": "zabbix"
    },
    "Zabbix de Teste": {
        "url": "http://192.168.0.35/zabbix/api_jsonrpc.php",
        "username": "Admin",
        "password": "zabbix"
    },
    "Zabbix Trucks - Homologação": {
        "url": "http://192.168.0.35/zabbix/api_jsonrpc.php",
        "username": "Admin",
        "password": "zabbix"
    }
}

headers = {'Content-Type': 'application/json'}

# Função de autenticação
def zabbix_authenticate(url, username, password):
    """Autentica no Zabbix e retorna o token."""
    payload = {
        "jsonrpc": "2.0",
        "method": "user.login",
        "params": {
            "username": username,
            "password": password
        },
        "id": 1
    }
    response = requests.post(url, headers=headers, data=json.dumps(payload))
    result = response.json()
    if 'result' in result:
        return result['result']
    else:
        raise Exception(f"Erro ao autenticar no Zabbix: {result.get('error')}")

# Função de requisição genérica
def zabbix_request(url, token, method, params):
    """Faz uma requisição à API do Zabbix."""
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
        raise Exception(f"Erro na API do Zabbix: {result.get('error')}" )
    
class ZabbixApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gerenciador de Blackout Zabbix")
        self.setGeometry(100, 100, 600, 500)

        # Layout principal
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)

        # Seleção da instância do Zabbix
        self.instance_selector = QComboBox()
        self.instance_selector.addItems(ZABBIX_INSTANCES.keys())
        self.layout.addWidget(QLabel("Selecione o Zabbix:"))
        self.layout.addWidget(self.instance_selector)

        # Botão para autenticar na instância selecionada
        self.auth_button = QPushButton("Autenticar")
        self.auth_button.clicked.connect(self.authenticate_instance)
        self.layout.addWidget(self.auth_button)

        # Status de autenticação
        self.auth_status = QLabel("")
        self.auth_status.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.auth_status)

        # Botões para configurações
        self.btn_configurar_blackout = QPushButton("Configurar Blackout")
        self.btn_configurar_blackout.clicked.connect(self.configurar_blackout)
        self.btn_configurar_blackout.setEnabled(False)
        self.layout.addWidget(self.btn_configurar_blackout)

        self.btn_administrar_blackouts = QPushButton("Administrar Blackouts")
        self.btn_administrar_blackouts.clicked.connect(self.administrar_blackouts)
        self.btn_administrar_blackouts.setEnabled(False)
        self.layout.addWidget(self.btn_administrar_blackouts)

    def authenticate_instance(self):
        instance_name = self.instance_selector.currentText()
        instance = ZABBIX_INSTANCES[instance_name]

        try:
            self.token = zabbix_authenticate(instance["url"], instance["username"], instance["password"])
            self.auth_status.setText(f"Autenticado em: {instance_name}")
            self.auth_status.setStyleSheet("color: green;")
            self.current_instance = instance
            self.btn_configurar_blackout.setEnabled(True)
            self.btn_administrar_blackouts.setEnabled(True)
        except Exception as e:
            self.auth_status.setText(f"Erro: {str(e)}")
            self.auth_status.setStyleSheet("color: red;")

    def configurar_blackout(self):
        self.blackout_window = QWidget()
        self.blackout_window.setWindowTitle("Configurar Blackout")
        self.blackout_window.setGeometry(150, 150, 400, 500)

        layout = QVBoxLayout(self.blackout_window)
        form_layout = QFormLayout()

        # Campo para nome da manutenção
        self.input_maintenance_name = QLineEdit()
        self.input_maintenance_name.setPlaceholderText("Digite o nome do blackout")

        # Campo para descrição do blackout
        self.input_maintenance_description = QLineEdit()
        self.input_maintenance_description.setPlaceholderText("Adicione uma descrição (opcional)")

        # Campo de busca
        self.input_search_host = QLineEdit()
        self.input_search_host.setPlaceholderText("Digite para buscar hosts...")
        self.input_search_host.textChanged.connect(self.filter_hosts)

        # Lista de hosts com seleção múltipla
        self.input_host_list = QListWidget()
        self.input_host_list.setSelectionMode(QAbstractItemView.MultiSelection)
        hosts = self.get_hosts()
        self.host_map = {host["name"]: host["hostid"] for host in hosts}
        self.input_host_list.addItems(self.host_map.keys())

        # Campo de texto para hostname manual (vários)
        self.input_manual_hostnames = QLineEdit()
        self.input_manual_hostnames.setPlaceholderText("Digite os hostnames separados por vírgula (opcional)")

        # Seletores de data/hora
        self.input_time_from = QDateTimeEdit()
        self.input_time_from.setCalendarPopup(True)
        self.input_time_from.setDateTime(QDateTime.currentDateTime())

        self.input_time_till = QDateTimeEdit()
        self.input_time_till.setCalendarPopup(True)
        self.input_time_till.setDateTime(QDateTime.currentDateTime().addSecs(3600))

        # Checkbox para coleta de dados
        self.checkbox_collect_data = QCheckBox("Manter coleta de dados durante o blackout")
        self.checkbox_collect_data.setChecked(True)

        # Adicionar os campos ao layout
        form_layout.addRow("Nome do Blackout:", self.input_maintenance_name)
        form_layout.addRow("Descrição do Blackout:", self.input_maintenance_description)
        form_layout.addRow("Buscar Hostnames:", self.input_search_host)
        form_layout.addRow("Selecionar Hostnames:", self.input_host_list)
        form_layout.addRow("Ou Digitar Hostnames:", self.input_manual_hostnames)
        form_layout.addRow("Início (Data/Hora):", self.input_time_from)
        form_layout.addRow("Término (Data/Hora):", self.input_time_till)
        form_layout.addRow(self.checkbox_collect_data)

        # Botão para adicionar blackout
        self.btn_add_blackout = QPushButton("Adicionar Blackout")
        self.btn_add_blackout.clicked.connect(self.adicionar_blackout)

        layout.addLayout(form_layout)
        layout.addWidget(self.btn_add_blackout)

        self.blackout_window.setLayout(layout)
        self.blackout_window.show()

    def get_hosts(self):
        try:
            params = {"output": ["hostid", "name"]}
            return zabbix_request(self.current_instance["url"], self.token, "host.get", params)
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Falha ao buscar hosts: {str(e)}")
            return []

    def filter_hosts(self):
        search_text = self.input_search_host.text().lower()
        for index in range(self.input_host_list.count()):
            item = self.input_host_list.item(index)
            item.setHidden(search_text not in item.text().lower())

    def adicionar_blackout(self):
        try:
            maintenance_name = self.input_maintenance_name.text().strip()
            description = self.input_maintenance_description.text().strip()
            if not maintenance_name:
                raise Exception("O nome do blackout é obrigatório.")

            selected_hosts = [item.text() for item in self.input_host_list.selectedItems()]
            selected_host_ids = [self.host_map[host] for host in selected_hosts]

            manual_hostnames = self.input_manual_hostnames.text().strip()
            if manual_hostnames:
                manual_host_ids = []
                for hostname in manual_hostnames.split(","):
                    hostname = hostname.strip()
                    if hostname in self.host_map:
                        manual_host_ids.append(self.host_map[hostname])
                    else:
                        raise Exception(f"Hostname '{hostname}' não encontrado.")
                selected_host_ids.extend(manual_host_ids)

            if not selected_host_ids:
                raise Exception("É necessário selecionar ou digitar pelo menos um hostname.")

            time_from = int(self.input_time_from.dateTime().toSecsSinceEpoch())
            time_till = int(self.input_time_till.dateTime().toSecsSinceEpoch())

            maintenance_type = 0 if self.checkbox_collect_data.isChecked() else 1

            params = {
                "name": maintenance_name,
                "description": description,
                "active_since": time_from,
                "active_till": time_till,
                "hostids": selected_host_ids,
                "maintenance_type": maintenance_type,
                "timeperiods": [{"timeperiod_type": 0, "period": time_till - time_from}]
            }
            zabbix_request(self.current_instance["url"], self.token, "maintenance.create", params)
            QMessageBox.information(self, "Sucesso", f"Blackout '{maintenance_name}' configurado com sucesso!")
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Falha ao configurar blackout: {str(e)}")

    def administrar_blackouts(self):
        self.admin_window = QWidget()
        self.admin_window.setWindowTitle("Administrar Blackouts")
        self.admin_window.setGeometry(150, 150, 600, 400)

        layout = QVBoxLayout(self.admin_window)
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["ID", "Nome", "Início/Término", "Status"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        btn_layout = QHBoxLayout()
        self.btn_remove_blackout = QPushButton("Remover")
        self.btn_remove_blackout.clicked.connect(self.remover_blackout)
        btn_layout.addWidget(self.btn_remove_blackout)

        self.btn_editar_blackout = QPushButton("Editar")
        self.btn_editar_blackout.clicked.connect(self.editar_blackout)
        btn_layout.addWidget(self.btn_editar_blackout)

        layout.addWidget(self.table)
        layout.addLayout(btn_layout)

        self.carregar_blackouts()

        self.admin_window.setLayout(layout)
        self.admin_window.show()

    def carregar_blackouts(self):
        try:
            params = {"output": ["maintenanceid", "name", "active_since", "active_till"]}
            blackouts = zabbix_request(self.current_instance["url"], self.token, "maintenance.get", params)
            self.table.setRowCount(len(blackouts))

            current_time = QDateTime.currentSecsSinceEpoch()
            for row, blackout in enumerate(blackouts):
                self.table.setItem(row, 0, QTableWidgetItem(blackout["maintenanceid"]))
                self.table.setItem(row, 1, QTableWidgetItem(blackout["name"]))
                period = f"{QDateTime.fromSecsSinceEpoch(int(blackout['active_since'])).toString()} - " \
                         f"{QDateTime.fromSecsSinceEpoch(int(blackout['active_till'])).toString()}"
                self.table.setItem(row, 2, QTableWidgetItem(period))

                # Determinar o status
                if current_time < int(blackout['active_since']):
                    status = "Futuro"
                elif current_time > int(blackout['active_till']):
                    status = "Encerrado"
                else:
                    status = "Ativo"
                self.table.setItem(row, 3, QTableWidgetItem(status))
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Falha ao carregar blackouts: {str(e)}")

    def remover_blackout(self):
        selected_row = self.table.currentRow()
        if selected_row == -1:
            QMessageBox.warning(self, "Atenção", "Selecione um blackout para remover.")
            return

        maintenance_id = self.table.item(selected_row, 0).text()
        try:
            params = [maintenance_id]  # A API espera um array de IDs
            zabbix_request(self.current_instance["url"], self.token, "maintenance.delete", params)
            QMessageBox.information(self, "Sucesso", "Blackout removido com sucesso.")
            self.carregar_blackouts()
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Falha ao remover blackout: {str(e)}")

    def editar_blackout(self):
        selected_row = self.table.currentRow()
        if selected_row == -1:
            QMessageBox.warning(self, "Atenção", "Selecione um blackout para editar.")
            return

        maintenance_id = self.table.item(selected_row, 0).text()
        blackout_name = self.table.item(selected_row, 1).text()

        self.edit_window = QWidget()
        self.edit_window.setWindowTitle(f"Editar Blackout: {blackout_name}")
        self.edit_window.setGeometry(200, 200, 400, 300)

        layout = QVBoxLayout(self.edit_window)
        form_layout = QFormLayout()

        self.edit_name = QLineEdit()
        self.edit_name.setText(blackout_name)
        self.edit_name.setPlaceholderText("Digite o novo nome")

        self.edit_time_from = QDateTimeEdit()
        self.edit_time_from.setCalendarPopup(True)

        self.edit_time_till = QDateTimeEdit()
        self.edit_time_till.setCalendarPopup(True)

        form_layout.addRow("Nome do Blackout:", self.edit_name)
        form_layout.addRow("Início (Data/Hora):", self.edit_time_from)
        form_layout.addRow("Término (Data/Hora):", self.edit_time_till)

        btn_save = QPushButton("Salvar Alterações")
        btn_save.clicked.connect(lambda: self.salvar_edicao_blackout(maintenance_id))

        layout.addLayout(form_layout)
        layout.addWidget(btn_save)

        self.edit_window.setLayout(layout)
        self.edit_window.show()

    def salvar_edicao_blackout(self, maintenance_id):
        try:
            new_name = self.edit_name.text().strip()
            new_time_from = int(self.edit_time_from.dateTime().toSecsSinceEpoch())
            new_time_till = int(self.edit_time_till.dateTime().toSecsSinceEpoch())

            params = {
                "maintenanceid": maintenance_id,
                "name": new_name,
                "active_since": new_time_from,
                "active_till": new_time_till
            }
            zabbix_request(self.current_instance["url"], self.token, "maintenance.update", params)
            QMessageBox.information(self, "Sucesso", "Blackout atualizado com sucesso.")
            self.edit_window.close()
            self.carregar_blackouts()
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Falha ao atualizar blackout: {str(e)}")

# Executar a aplicação
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ZabbixApp()
    window.show()
    sys.exit(app.exec_())
