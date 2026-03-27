import os
from typing import Dict, Any, Optional
import boto3
import json

def get_table():
    provider = os.getenv("CLOUD_PROVIDER", "LOCAL").upper()
    
    if provider == "AZURE":
        from azure.data.tables import TableClient
        conn_str = os.getenv("AZURE_STORAGE_CONNECTION_STRING") or os.getenv("AzureWebJobsStorage")
        table_name = os.getenv("CHANNEL_CONFIGS_TABLE", "ChannelConfigs") or "ChannelConfigs"
        print(f"[AZURE] Conectando na tabela: {table_name}")
        return TableClient.from_connection_string(conn_str=conn_str, table_name=table_name), provider
        
    dynamodb = boto3.resource('dynamodb', region_name=os.getenv("AWS_REGION", "us-east-1"))
    table_name = os.getenv("CHANNEL_CONFIGS_TABLE", "ChannelConfigs")
    return dynamodb.Table(table_name), provider

def load_configs() -> dict:
    """Lê todas configs cadastradas (apenas para painel/admin)"""
    table, provider = get_table()
    try:
        if provider == "AZURE":
            items = table.list_entities()
            return {item['RowKey']: {
                'channel_id': item['RowKey'],
                'project_key': item.get('project_key', ''),
                'board_id': item.get('board_id', ''),
                'transitions': eval(item.get('transitions', '{}'))
            } for item in items}
        else:
            response = table.scan()
            items = response.get('Items', [])
            return {item['channel_id']: item for item in items}
    except Exception as e:
        print(f"Erro ao buscar configs no DB ({provider}): {e}")
        return {}

def save_config(channel_id: str, project_key: str, board_id: str, transitions: dict):
    """Salva/Atualiza a configuração de um canal"""
    table, provider = get_table()
    try:
        if provider == "AZURE":
            table.upsert_entity(entity={
                'PartitionKey': 'config',
                'RowKey': channel_id,
                'project_key': project_key,
                'board_id': board_id,
                'transitions': str(transitions)
            })
        else:
            table.put_item(
                Item={
                    'channel_id': channel_id,
                    'project_key': project_key,
                    'board_id': board_id,
                    'transitions': transitions
                }
            )
    except Exception as e:
        print(f"Erro ao salvar config no DB ({provider}): {e}")

def get_channel_config(channel_id: str) -> Optional[Dict[str, Any]]:
    """Busca a config de um canal específico"""
    table, provider = get_table()
    try:
        if provider == "AZURE":
            try:
                entity = table.get_entity(partition_key="config", row_key=channel_id)
                return {
                    'channel_id': entity['RowKey'],
                    'project_key': entity.get('project_key'),
                    'board_id': entity.get('board_id'),
                    'transitions': eval(entity.get('transitions', '{}'))
                }
            except Exception:
                return None
        else:
            response = table.get_item(Key={'channel_id': channel_id})
            return response.get('Item')
    except Exception as e:
        print(f"Erro ao buscar config do canal no DB ({provider}): {e}")
        return None