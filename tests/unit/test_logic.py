import pytest
from unittest.mock import MagicMock, patch
import os
import sys

# --- CONFIGURAÇÃO DE AMBIENTE (Antes do Import) ---
# Definimos credenciais falsas para garantir que não dependemos do .env
os.environ["SLACK_BOT_TOKEN"] = "xoxb-fake-token-para-teste-unitario"
os.environ["SLACK_SIGNING_SECRET"] = "fake-signing-secret"
os.environ["CLOUD_PROVIDER"] = "LOCAL"  # Garante uso do adapter local

# --- O TRUQUE DO MOCK ---
# O 'slack_bolt.App' tenta validar o token na internet ao iniciar.
# Usamos o 'patch' para interceptar a chamada 'auth_test' e retornar Sucesso ({'ok': True})
# Fazemos isso ANTES de importar o main_api.
with patch("slack_sdk.web.client.WebClient.auth_test", return_value={"ok": True}):
    from app.api.main import app

# --- TESTES ---

@pytest.fixture
def client():
    """Configura o cliente de teste do Flask"""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_benchmark_route(client):
    """
    Testa a rota de benchmark simulando o envio para a fila.
    """
    # Substituímos o método send_message real por um Mock para não criar arquivos/rede
    with patch('app.api.main.queue.send_message') as mock_send:
        
        response = client.post('/benchmark/load', json={"latency_ms": 0})
        
        # Validações
        assert response.status_code == 200
        assert response.json["ok"] is True
        
        # Garante que a função de envio foi chamada
        mock_send.assert_called_once()
        
        # Verifica se o payload enviado está correto
        payload_enviado = mock_send.call_args[0][0]
        assert payload_enviado["action"] == "create_ticket"
        assert payload_enviado["is_benchmark"] is True

def test_slack_payload_format(client):
    """
    Testa o handshake de verificação de URL do Slack.
    """
    import json
    
    # O Slack manda isso para verificar se sua API existe
    challenge_code = "desafio_teste_123"
    payload = {
        "token": "token_verificacao",
        "challenge": challenge_code,
        "type": "url_verification"
    }
    
    # Precisamos mockar o handler do Bolt, pois ele rejeitaria a assinatura fake
    # Mockamos a resposta interna do Bolt para devolver o challenge
    from flask import Response
    mock_response = Response(
        response=json.dumps({"challenge": challenge_code}), 
        status=200, 
        mimetype="application/json"
    )

    with patch('slack_bolt.adapter.flask.SlackRequestHandler.handle', return_value=mock_response):
        response = client.post('/slack/events', json=payload)
        
        assert response.status_code == 200
        assert challenge_code in response.get_data(as_text=True)

def test_queue_failure_handling(client):
    """
    Testa se a API lida bem com falhas na fila (ex: erro 500 em vez de crashar).
    """
    with patch('app.api.main.queue.send_message') as mock_send:
        # Simulamos uma falha crítica na fila
        mock_send.side_effect = Exception("Erro fatal na fila")
        
        response = client.post('/benchmark/load', json={})
        
        assert response.status_code == 500
        assert "Erro fatal na fila" in response.json["error"]