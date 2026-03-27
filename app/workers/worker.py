import os
import time
import logging
from dotenv import load_dotenv
from slack_sdk import WebClient
from jira import JIRA
from app.infra.adapters import get_queue_provider
from app.core.metrics import log_metric
from app.infra.database import save_link, get_link

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("Worker")

queue = get_queue_provider()
PROVIDER = os.getenv("CLOUD_PROVIDER", "LOCAL")
slack = WebClient(token=os.environ["SLACK_BOT_TOKEN"])

# Conexão Jira
try:
    jira = JIRA(
        server=os.environ["JIRA_SERVER"],
        basic_auth=(os.environ["JIRA_EMAIL"], os.environ["JIRA_API_TOKEN"])
    )
except Exception as e:
    logger.error(f"Erro Jira: {e}")
    jira = None

# --- UI HELPERS ---

def get_jira_transitions(issue_key):
    if not jira: return []
    try:
        return [{'id': t['id'], 'name': t['name']} for t in jira.transitions(issue_key)]
    except: return []

def build_blocks(issue_key, title, user_id, status, transitions):
    status_lower = status.lower()
    icon = "🚨"
    if "progress" in status_lower or "andamento" in status_lower: icon = "🏃"
    if "done" in status_lower or "concluído" in status_lower: icon = "✅"
    
    jira_url = os.environ.get('JIRA_SERVER', '')
    
    btns = []
    for t in transitions[:5]:
        
        btn = {
            "type": "button",
            "text": {"type": "plain_text", "text": t['name'][:30]},
            "value": f"{issue_key}|{t['id']}", 
            "action_id": f"btn_dyn_{t['id']}" 
        }
            
        btns.append(btn)

    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"{icon} *[{status.upper()}]* <{jira_url}/browse/{issue_key}|{issue_key}>\n*Resumo:* {title}\n*Solicitante:* <@{user_id}>"
            }
        }
    ]
    
    if btns:
        blocks.append({"type": "actions", "elements": btns})
        
    return blocks

def build_detail_blocks(desc, prio, assignee, created):
    return [
        {"type": "section", "text": {"type": "mrkdwn", "text": f"*📖 Detalhes:*\n{desc}"}},
        {"type": "divider"},
        {"type": "section", "fields": [
            {"type": "mrkdwn", "text": f"*Prioridade:*\n{prio}"},
            {"type": "mrkdwn", "text": f"*Responsável:*\n{assignee}"},
            {"type": "mrkdwn", "text": f"*Data:*\n{created[:10] if created else 'N/A'}"}
        ]}
    ]

# --- EXECUÇÃO ---

def execute_create_ticket(data):
    if data.get("is_benchmark"):
        log_metric(PROVIDER, "Worker", "execution_benchmark_queue", data.get("timestamp", time.time()), "BENCHMARK")
        return

    try:
        message_ts = data.get("message_ts")

        # 1. Jira
        project_key = data.get("project_key")
        issue_fields = {
            'project': {'key': project_key},
            'summary': data.get("title"),
            'description': f"{data.get('description')}\n\nSolicitante: <@{data.get('user_id')}>",
            'issuetype': {'name': 'Task'}
        }
        
        try:
            issue_fields['priority'] = {'name': 'Medium'}
            issue = jira.create_issue(fields=issue_fields)
        except:
            if 'priority' in issue_fields: del issue_fields['priority']
            issue = jira.create_issue(fields=issue_fields)
        
        # 2. Botões Dinâmicos
        avail_transitions = get_jira_transitions(issue.key)
        blocks = build_blocks(issue.key, data["title"], data["user_id"], "To Do", avail_transitions)
        
        if message_ts:
            slack.chat_update(
                channel=data["channel_id"],
                ts=message_ts,
                blocks=blocks,
                text=f"Ticket criado: {issue.key}"
            )
        else:
            resp = slack.chat_postMessage(channel=data["channel_id"], blocks=blocks, text=f"Ticket: {issue.key}")
            message_ts = resp["ts"]

        # 3. Thread
        save_link(issue.key, data["channel_id"], message_ts, data["user_id"])
        
        prio = issue.fields.priority.name if hasattr(issue.fields, 'priority') and issue.fields.priority else "Normal"
        assignee = issue.fields.assignee.displayName if issue.fields.assignee else "N/A"
        details = build_detail_blocks(data["description"], prio, assignee, issue.fields.created)
        
        slack.chat_postMessage(channel=data["channel_id"], thread_ts=message_ts, text="Detalhes", blocks=details)
        logger.info(f"Ticket criado: {issue.key}")

        # LOG METRIC
        log_metric(PROVIDER, "Worker", "execution_create_ticket", data.get("timestamp", time.time()), issue.key)

    except Exception as e:
        logger.error(f"Erro create: {e}")
        if message_ts:
            slack.chat_update(channel=data["channel_id"], ts=message_ts, text=f"❌ Erro Jira: {e}", blocks=[])

def execute_transition(data):
    try:
        jira.transition_issue(data["issue_key"], data["target_status"])
        logger.info(f"Transition: {data['issue_key']} -> {data['target_status']}")

        # LOG METRIC
        log_metric(PROVIDER, "Worker", "execution_transition", data.get("timestamp", time.time()), data["issue_key"])

    except Exception as e: logger.error(f"Erro transition: {e}")

def execute_update_display(data):
    try:
        link = get_link(data["issue_key"])
        if link:
            avail_transitions = get_jira_transitions(data["issue_key"])
            blocks = build_blocks(data["issue_key"], data["summary"], link["user_id"], data["new_status"], avail_transitions)
            
            slack.chat_update(
                channel=link["channel_id"], 
                ts=link["message_ts"], 
                blocks=blocks, 
                text=f"Status Update: {data['new_status']}"
            )

            # LOG METRIC
            # O timestamp deve vir do payload original no main.py
            start_t = data.get("timestamp", time.time())
            log_metric(PROVIDER, "Worker", "execution_update_display", start_t, data["issue_key"])

    except Exception as e: logger.error(f"Erro update: {e}")

def start():
    logger.info(f"--- WORKER DINÂMICO ({PROVIDER}) ---")
    while True:
        try:
            msgs = queue.receive_messages(max_number=1)
            if msgs:
                for m in msgs:
                    queue.delete_message(m['handle'])
                    body = m['body']
                    act = body.get("action")
                    if act == "create_ticket": execute_create_ticket(body)
                    elif act == "transition_ticket": execute_transition(body)
                    elif act == "update_status_display": execute_update_display(body)
            else:
                time.sleep(0.1 if PROVIDER == "LOCAL" else 1)
        except Exception as e:
            logger.error(f"Loop: {e}")
            time.sleep(1)

if __name__ == "__main__":
    start()