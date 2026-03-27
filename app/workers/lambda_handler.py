import json
import logging
from app.workers.worker import execute_create_ticket, execute_transition, execute_update_display

logger = logging.getLogger("WorkerLambda")
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """
    Função engatilhada pelo AWS SQS.
    Recebe as mensagens na fila e processa chamando as funções extraídas do loop do worker.
    """
    records = event.get('Records', [])
    logger.info(f"Iniciando processamento de {len(records)} records provenientes do SQS.")
    
    for record in records:
        try:
            # O SQS envia o payload como string JSON na propriedade 'body'
            body_str = record.get('body', '{}')
            body = json.loads(body_str)
            action = body.get("action")
            
            logger.info(f"Executando ação: {action}")
            
            if action == "create_ticket":
                execute_create_ticket(body)
            elif action == "transition_ticket":
                execute_transition(body)
            elif action == "update_status_display":
                execute_update_display(body)
            else:
                logger.warning(f"Ação desconhecida recebida: {action}")
                
        except Exception as e:
            logger.error(f"Erro ao processar record: {e}", exc_info=True)
            # Ao lançar a exceção de volta, o Lambda vai notificar o SQS de que
            # a mensagem falhou, e a AWS a colocará de volta na fila (DLQ ou Retry)
            raise e
            
    return {"statusCode": 200, "body": "Fila processada com sucesso"}
