import os
import time
import re # <--- IMPORTANTE: Necessário para identificar botões dinâmicos
from flask import Flask, request, jsonify, render_template, redirect, url_for
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler
from jira import JIRA
from app.infra.adapters import get_queue_provider
from app.core.metrics import log_metric, init_log
from app.infra.config_db import save_config, get_channel_config, load_configs

# --- CONFIGURAÇÃO ---
load_dotenv()
init_log()

app = Flask(__name__)
queue = get_queue_provider()
PROVIDER = os.getenv("CLOUD_PROVIDER", "LOCAL")

bolt_app = App(
    token=os.environ["SLACK_BOT_TOKEN"], 
    signing_secret=os.environ["SLACK_SIGNING_SECRET"],
    process_before_response=True
)
handler = SlackRequestHandler(bolt_app)

# Jira (Apenas para Diagnósticos)
try:
    jira_api = JIRA(
        server=os.environ["JIRA_SERVER"],
        basic_auth=(os.environ["JIRA_EMAIL"], os.environ["JIRA_API_TOKEN"])
    )
except: jira_api = None

# --- ROTAS CONFIG ---
def get_jira_diagnostics(debug_project_key=None):
    """
    Busca metadados do Jira para identificar BLOQUEIOS (Campos Obrigatórios).
    """
    diag = {
        "boards": [], 
        "required_fields": [], 
        "debug_project": debug_project_key,
        "error": None
    }
    
    if not jira_api:
        diag["error"] = "Jira desconectado. Verifique o .env"
        return diag

    try:
        # 1. Lista Boards (Apenas informativo)
        try:
            boards = jira_api.boards(startAt=0, maxResults=20)
            for b in boards:
                diag["boards"].append(f"{b.name} (ID: {b.id})")
        except Exception as e:
            print(f"Erro ao listar boards: {e}")

        # 2. VERIFICA CAMPOS OBRIGATÓRIOS (O Detetive)
        if debug_project_key:
            try:
                # Pergunta ao Jira: "O que é obrigatório para criar uma Task aqui?"
                meta = jira_api.createmeta(
                    projectKeys=debug_project_key, 
                    issuetypeNames=['Task'], 
                    expand='projects.issuetypes.fields'
                )
                
                if meta['projects']:
                    # Pega os campos da 'Task'
                    fields = meta['projects'][0]['issuetypes'][0]['fields']
                    
                    for field_key, field_val in fields.items():
                        # Se o campo for obrigatório (required=True)
                        if field_val.get('required'):
                            # Ignoramos os campos que o Bot JÁ preenche automaticamente
                            ignored = ['project', 'summary', 'description', 'issuetype', 'reporter', 'priority', 'assignee']
                            
                            if field_key not in ignored:
                                diag["required_fields"].append({
                                    "id": field_key,
                                    "name": field_val['name'],
                                    "type": field_val['schema']['type']
                                })
            except Exception as e:
                diag["required_fields_error"] = f"Erro ao analisar projeto {debug_project_key}: {e}"

    except Exception as e:
        diag["error"] = str(e)

    return diag

# --- ROTA DE CONFIGURAÇÃO ---
@app.route('/api/config', methods=['GET'])
@app.route("/config", methods=["GET"])
def config_page():
    # Pega o projeto que o usuário digitou na caixa de busca do Detetive
    debug_project = request.args.get("debug_project")
    
    # Roda o diagnóstico
    diagnostics = get_jira_diagnostics(debug_project)
    
    return render_template("manager.html", configs=load_configs(), diag=diagnostics)

@app.route('/api/config/save', methods=['POST'])
@app.route("/config/save", methods=["POST"])
def config_save():
    save_config(request.form["channel_id"], request.form["project_key"], "0", {})
    return redirect(url_for('config_page'))

# --- FLUXO SLACK ---

def build_ticket_modal_fast(channel_id):
    return {
        "type": "modal",
        "callback_id": "view_create_ticket",
        "private_metadata": channel_id,
        "title": {"type": "plain_text", "text": "Novo Chamado"},
        "submit": {"type": "plain_text", "text": "Criar"},
        "blocks": [
            {"type": "input", "block_id": "blk_title", "element": {"type": "plain_text_input", "action_id": "inp_title"}, "label": {"type": "plain_text", "text": "Título"}},
            {"type": "input", "block_id": "blk_desc", "element": {"type": "plain_text_input", "action_id": "inp_desc", "multiline": True}, "label": {"type": "plain_text", "text": "Descrição"}}
        ]
    }

@app.route('/api/slack/events', methods=['POST'])
@app.route("/slack/events", methods=["POST"])
def slack_events():
    return handler.handle(request)

@bolt_app.command("/criar-chamado")
def handle_command(ack, body, client):
    ack()
    channel_id = body["channel_id"]
    if not get_channel_config(channel_id):
        client.chat_postEphemeral(channel=channel_id, user=body["user_id"], text=f"⚠️ Canal inválido. Para adicionar o workflow acesse a pagina de configuração no navegador.")
        return
    client.views_open(trigger_id=body["trigger_id"], view=build_ticket_modal_fast(channel_id))

@bolt_app.view("view_create_ticket")
def handle_submission(ack, body, view, client):
    ack()
    start = time.time()
    
    try:
        channel_id = view["private_metadata"]
        config = get_channel_config(channel_id)
        vals = view["state"]["values"]
        title = vals["blk_title"]["inp_title"]["value"]
        desc = vals["blk_desc"]["inp_desc"]["value"]

        # Posta Msg Carregando
        msg_wait = client.chat_postMessage(
            channel=channel_id,
            text=f"⏳ Criando chamado: {title}...",
            blocks=[{"type": "context", "elements": [{"type": "mrkdwn", "text": "⚙️ *Enviando para o Jira...* Aguarde."}]}]
        )

        payload = {
            "action": "create_ticket",
            "user_id": body["user"]["id"],
            "channel_id": channel_id,
            "message_ts": msg_wait["ts"],
            "title": title,
            "description": desc,
            "project_key": config["project_key"],
            "timestamp": start
        }
        
        queue.send_message(payload)
        log_metric(PROVIDER, "SlackToJira", "enqueue_modal", start)
        
    except Exception as e:
        print(f"Erro submit: {e}")

# --- USA REGEX PARA CAPTURAR QUALQUER BOTÃO 'btn_dyn_' ---
@bolt_app.action(re.compile("^btn_dyn_.*"))
def handle_dynamic_transition(ack, body):
    ack()
    start = time.time()
    try:
        # value="KAN-123|31"
        raw_value = body["actions"][0]["value"]
        issue_key, trans_id = raw_value.split("|")
        
        queue.send_message({
            "action": "transition_ticket",
            "issue_key": issue_key,
            "target_status": trans_id,
            "timestamp": start
        })
        log_metric(PROVIDER, "SlackToJira", "enqueue_transition", start)
    except Exception as e:
        print(f"Erro botão: {e}")

# --- FLUXO JIRA ---

@app.route('/api/jira/webhook', methods=['POST'])
@app.route("/jira/webhook", methods=["POST"])
def jira_webhook():
    start = time.time()
    data = request.json
    if data and data.get("webhookEvent") == "jira:issue_updated":
        queue.send_message({
            "action": "update_status_display",
            "issue_key": data["issue"]["key"],
            "new_status": data["issue"]["fields"]["status"]["name"],
            "summary": data["issue"]["fields"]["summary"],
            "timestamp": start
        })
    return jsonify({"status": "ok"}), 200

# --- BENCHMARK ---

@app.route('/api/benchmark/load', methods=['POST'])
@app.route("/benchmark/load", methods=["POST"])
def benchmark_load():
    queue.send_message({"action": "create_ticket", "is_benchmark": True, "timestamp": time.time()})
    return jsonify({"ok": True}), 200

if __name__ == "__main__":
    app.run(port=3000)