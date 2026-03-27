import json
import logging
import traceback
import azure.functions as func

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

try:
    from app.api.main import app as flask_app
    from app.workers.worker import execute_create_ticket, execute_transition, execute_update_display

    @app.route(route="{*route}", methods=["GET", "POST"])
    def flask_api_handler(req: func.HttpRequest, context: func.Context) -> func.HttpResponse:
        logging.info('Executando request HTTP encaminhado ao Flask.')
        return func.WsgiMiddleware(flask_app).handle(req, context)

    @app.queue_trigger(arg_name="msg", queue_name="fila-tcc", connection="AzureWebJobsStorage")
    def queue_worker_handler(msg: func.QueueMessage):
        logging.info(f"Nova mensagem na fila Azure recebida! ID = {msg.id}")
        try:
            body_str = msg.get_body().decode('utf-8')
            body = json.loads(body_str)
            action = body.get("action")
            
            if action == "create_ticket":
                execute_create_ticket(body)
            elif action == "transition_ticket":
                execute_transition(body)
            elif action == "update_status_display":
                execute_update_display(body)
            else:
                logging.warning(f"Ação não mapeada no Worker: {action}")
                
        except Exception as e:
            logging.error(f"Erro ao processar mensagem da fila no Azure: {e}", exc_info=True)
            raise e

except Exception as e:
    err_msg = traceback.format_exc()
    logging.error(f"FATAL STARTUP ERROR: {err_msg}")
    
    @app.route(route="debug_crash", methods=["GET"])
    def debug_crash(req: func.HttpRequest) -> func.HttpResponse:
        return func.HttpResponse(body=f"Crash during initialization:\n\n{err_msg}", status_code=500)
