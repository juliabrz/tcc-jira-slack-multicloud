import serverless_wsgi
from app.api.main import app

def lambda_handler(event, context):
    """
    Ponto de entrada do AWS Lambda para rodar a aplicação Flask.
    Ele pega a conexão do API Gateway e a traduz para o WSGI usado pelo Flask.
    """
    return serverless_wsgi.handle_request(app, event, context)
