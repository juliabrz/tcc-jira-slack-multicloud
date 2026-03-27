import os
from jira import JIRA
from dotenv import load_dotenv

load_dotenv()

# Conecta no Jira
jira = JIRA(
    server=os.environ["JIRA_SERVER"],
    basic_auth=(os.environ["JIRA_EMAIL"], os.environ["JIRA_API_TOKEN"])
)

# --- DIGITE AQUI A CHAVE DE UM TICKET QUE EXISTE E ESTÁ "TO DO" ---
ISSUE_KEY = "TM-2" # <--- Troque pelo ID de um ticket real do seu projeto

print(f"--- Buscando transições para {ISSUE_KEY} ---")
try:
    transitions = jira.transitions(ISSUE_KEY)
    for t in transitions:
        print(f"ID: {t['id']} | Nome: '{t['name']}' -> Vai para: {t['to']['name']}")
except Exception as e:
    print(f"Erro: {e}")