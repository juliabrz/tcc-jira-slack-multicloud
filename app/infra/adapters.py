import os
import json
import time
import uuid
import boto3
from botocore.exceptions import ClientError
from threading import Lock

_local_file_lock = Lock()

class LocalQueueProvider:
    def __init__(self):
        self.queue_dir = os.path.join(os.getcwd(), "queues", "local_queue")
        self.queue_file = os.path.join(self.queue_dir, "queue.json")
        if not os.path.exists(self.queue_dir):
            os.makedirs(self.queue_dir)
        # Garante que o arquivo existe e é uma lista válida
        if not os.path.exists(self.queue_file):
            with open(self.queue_file, "w") as f:
                json.dump([], f)

    def send_message(self, message_body):
        """Salva mensagem no arquivo JSON com segurança de Thread"""
        with _local_file_lock: # Bloqueia outros acessos enquanto escreve
            try:
                # 1. Lê o atual
                with open(self.queue_file, "r") as f:
                    try:
                        messages = json.load(f)
                    except json.JSONDecodeError:
                        messages = [] # Se corrompeu, reseta
                
                # 2. Adiciona o novo
                message = {
                    "MessageId": str(uuid.uuid4()),
                    "Body": json.dumps(message_body),
                    "ReceiptHandle": str(uuid.uuid4())
                }
                messages.append(message)
                
                # 3. Salva tudo de volta
                with open(self.queue_file, "w") as f:
                    json.dump(messages, f, indent=2)
                    
                print(f"[LOCAL] Mensagem salva: {message_body.get('action')}")
                
            except Exception as e:
                print(f"[LOCAL] Erro ao salvar na fila: {e}")

    def receive_messages(self, max_number=1):
        """Lê mensagens do arquivo"""
        # Nota: O worker roda em processo separado, então o Lock da API não afeta aqui diretamente.
        # Por isso usamos tratamento de erro robusto.
        try:
            if not os.path.exists(self.queue_file): return []
            
            with open(self.queue_file, "r") as f:
                try:
                    messages = json.load(f)
                except json.JSONDecodeError:
                    return [] # Arquivo vazio ou lendo durante escrita
            
            if not messages: return []

            # Simula formato SQS
            output = []
            for msg in messages[:max_number]:
                output.append({
                    'body': json.loads(msg['Body']),
                    'handle': msg['ReceiptHandle']
                })
            return output

        except Exception as e:
            print(f"[LOCAL] Erro leitura: {e}")
            return []

    def delete_message(self, receipt_handle):
        """Remove mensagem processada"""
        try:
            with open(self.queue_file, "r") as f:
                try:
                    messages = json.load(f)
                except: return

            # Filtra removendo a mensagem processada
            new_messages = [m for m in messages if m['ReceiptHandle'] != receipt_handle]

            with open(self.queue_file, "w") as f:
                json.dump(new_messages, f, indent=2)
                
        except Exception as e:
            print(f"[LOCAL] Erro delete: {e}")

class AWSQueueProvider:
    def __init__(self):
        self.sqs = boto3.client('sqs', region_name=os.getenv("AWS_REGION", "us-east-1"))
        self.queue_url = os.getenv("AWS_SQS_URL")

    def send_message(self, message_body):
        self.sqs.send_message(
            QueueUrl=self.queue_url,
            MessageBody=json.dumps(message_body)
        )

    def receive_messages(self, max_number=1):
        response = self.sqs.receive_message(
            QueueUrl=self.queue_url,
            MaxNumberOfMessages=max_number,
            WaitTimeSeconds=2 # Long polling
        )
        messages = []
        if 'Messages' in response:
            for msg in response['Messages']:
                messages.append({
                    'body': json.loads(msg['Body']),
                    'handle': msg['ReceiptHandle']
                })
        return messages

    def delete_message(self, receipt_handle):
        self.sqs.delete_message(
            QueueUrl=self.queue_url,
            ReceiptHandle=receipt_handle
        )

class AzureQueueProvider:
    def __init__(self):
        from azure.storage.queue import QueueClient
        conn_str = os.getenv("AZURE_STORAGE_CONNECTION_STRING") or os.getenv("AzureWebJobsStorage")
        queue_name = os.getenv("AZURE_QUEUE_NAME", "fila-tcc")
        if not queue_name:
            queue_name = "fila-tcc"
        print(f"[AZURE] Conectando na fila: {queue_name}")
        self.client = QueueClient.from_connection_string(conn_str, queue_name)

    def send_message(self, message_body):
        import base64
        try:
            # Azure requer base64 em alguns casos, mas aqui mandamos texto
            msg = json.dumps(message_body)
            # Encode to b64 to be safe
            msg_b64 = base64.b64encode(msg.encode('utf-8')).decode('ascii')
            self.client.send_message(msg_b64)
            print(f"[AZURE] Mensagem enviada para fila com sucesso.")
        except Exception as e:
            print(f"[AZURE] ERRO FATAL AO ENVIAR PARA FILA: {e}")
            raise e

    def receive_messages(self, max_number=1):
        import base64
        msgs = self.client.receive_messages(messages_per_page=max_number, visibility_timeout=30)
        output = []
        for m in msgs:
            try:
                # Decode b64
                body_str = base64.b64decode(m.content).decode('utf-8')
                body = json.loads(body_str)
                output.append({
                    'body': body,
                    'handle': m # Azure usa o objeto mensagem inteiro para deletar
                })
            except:
                print("Erro decode Azure")
        return output

    def delete_message(self, message_handle):
        self.client.delete_message(message_handle)


def get_queue_provider():
    provider = os.getenv("CLOUD_PROVIDER", "LOCAL").upper()
    if provider == "AWS":
        return AWSQueueProvider()
    elif provider == "AZURE":
        return AzureQueueProvider()
    else:
        return LocalQueueProvider()