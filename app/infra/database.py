import os
import boto3
from typing import Dict, Any, Optional

def get_table():
    provider = os.getenv("CLOUD_PROVIDER", "LOCAL").upper()
    
    if provider == "AZURE":
        from azure.data.tables import TableClient
        conn_str = os.getenv("AZURE_STORAGE_CONNECTION_STRING") or os.getenv("AzureWebJobsStorage")
        table_name = os.getenv("TICKET_LINKS_TABLE", "TicketLinks") or "TicketLinks"
        print(f"[AZURE] Conectando na tabela: {table_name}")
        return TableClient.from_connection_string(conn_str=conn_str, table_name=table_name), provider
    
    # Provider AWS padrão
    dynamodb = boto3.resource('dynamodb', region_name=os.getenv("AWS_REGION", "us-east-1"))
    table_name = os.getenv("TICKET_LINKS_TABLE", "TicketLinks")
    return dynamodb.Table(table_name), provider

def save_link(issue_key: str, channel_id: str, message_ts: str, user_id: str):
    """Salva metadados para permitir o chat_update futuro"""
    table, provider = get_table()
    try:
        if provider == "AZURE":
            table.upsert_entity(entity={
                'PartitionKey': 'links',
                'RowKey': issue_key,
                'channel_id': channel_id,
                'message_ts': message_ts,
                'user_id': user_id
            })
        else:
            table.put_item(
                Item={
                    'issue_key': issue_key,
                    'channel_id': channel_id,
                    'message_ts': message_ts,
                    'user_id': user_id
                }
            )
    except Exception as e:
        print(f"Erro ao salvar link no DB ({provider}): {e}")

def get_link(issue_key: str) -> Optional[Dict[str, Any]]:
    table, provider = get_table()
    try:
        if provider == "AZURE":
            try:
                entity = table.get_entity(partition_key="links", row_key=issue_key)
                return {
                    'issue_key': entity['RowKey'],
                    'channel_id': entity['channel_id'],
                    'message_ts': entity['message_ts'],
                    'user_id': entity['user_id']
                }
            except Exception:
                return None
        else:
            response = table.get_item(Key={'issue_key': issue_key})
            return response.get('Item')
    except Exception as e:
        print(f"Erro ao buscar link no DB ({provider}): {e}")
        return None