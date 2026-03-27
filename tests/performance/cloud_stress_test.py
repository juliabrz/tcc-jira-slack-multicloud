import requests
import os
import time
import concurrent.futures
import csv
import statistics
import sys
import json
from dotenv import load_dotenv

load_dotenv()

# ==============================================================================
# SCRIPT DE STRESS TEST: MULTI-CLOUD (AWS vs AZURE)
# ==============================================================================

# 1. Escolha a nuvem alvo para testar (AWS ou AZURE)
PROVIDER_NAME = "AWS"

# 2. Escolha o tipo de teste:
# "SLACK": Testa latência pura do Servidor HTTP em responder
# "BENCHMARK": Testa a capacidade física da Nuvem de enfileirar na Queue/SQS
TEST_ROUTE = "BENCHMARK"

# URLs Base carregadas do arquivo oculto .env
URLS = {
    "AWS": os.getenv("AWS_API_URL"),
    "AZURE": os.getenv("AZURE_API_URL")
}

base_url = URLS.get(PROVIDER_NAME)
TARGET_URL = f"{base_url}/slack/events" if TEST_ROUTE == "SLACK" else f"{base_url}/benchmark/load"

# 3. Configurações de Carga (Simulando 50 requisições enviadas ao mesmo tempo)
TOTAL_REQUESTS = 50    
CONCURRENCY = 10       # 10 Requisições sendo enviadas em paralelo
TIMEOUT = 10           # Tempo limite (segundos)

# ==============================================================================

def send_request(req_id):
    """
    Envia a carga baseada na Rota escolhida para o Teste.
    """
    if TEST_ROUTE == "SLACK":
        payload = {
            "type": "url_verification",
            "challenge": f"tcc_benchmark_{req_id}"
        }
    else:
        # Payload para a fila 
        payload = {
            "latency_ms": 0,
            "is_benchmark": True
        }
    
    
    start_time = time.time()
    try:
        response = requests.post(TARGET_URL, json=payload, timeout=TIMEOUT)
        end_time = time.time()
        
        duration_ms = (end_time - start_time) * 1000
        
        return {
            "id": req_id,
            "status": response.status_code,
            "duration_ms": duration_ms,
            "error": None
        }
    except Exception as e:
        end_time = time.time()
        return {
            "id": req_id,
            "status": 0,
            "duration_ms": (end_time - start_time) * 1000,
            "error": str(e)
        }

def run_benchmark():
    if not TARGET_URL:
        print("⚠️ Nuvem não reconhecida.")
        return

    print(f"\n🚀 INICIANDO CLOUD BENCHMARK: [{PROVIDER_NAME}]")
    print(f"URL Alvo: {TARGET_URL}")
    print(f"Carga: {TOTAL_REQUESTS} requests | {CONCURRENCY} threads\n")
    
    results = []
    start_global = time.time()
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=CONCURRENCY) as executor:
        futures = {executor.submit(send_request, i): i for i in range(TOTAL_REQUESTS)}
        
        completed = 0
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            results.append(res)
            
            completed += 1
            if completed % 10 == 0 or completed == TOTAL_REQUESTS:
                sys.stdout.write(f"\rProcessados: {completed}/{TOTAL_REQUESTS}")
                sys.stdout.flush()

    total_time = time.time() - start_global
    print(f"\n\n✅ Teste finalizado em {total_time:.2f} segundos.")

    # --- SALVAR CSV ---
    os.makedirs(os.path.join("data", "output", "stats"), exist_ok=True)
    filename = os.path.join("data", "output", "stats", f"resultado_stress_{PROVIDER_NAME}_cloud.csv")
    
    success_times = [r["duration_ms"] for r in results if r["status"] == 200]
    errors = [r for r in results if r["status"] != 200]

    with open(filename, mode='w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["provider", "request_id", "status", "duration_ms", "error"])
        
        for r in results:
            writer.writerow([PROVIDER_NAME, r["id"], r["status"], f"{r['duration_ms']:.2f}", r["error"]])
            
    print(f"📁 Dados de milissegundos salvos em: {filename}")

    # --- RELATÓRIO FINAL ---
    print("\n--- RESUMO ESTATÍSTICO (LATÊNCIA DA API HTTP) ---")
    if success_times:
        print(f"Sucessos: {len(success_times)} / {TOTAL_REQUESTS}")
        print(f"Média Latência: {statistics.mean(success_times):.2f} ms")
        print(f"Mínima: {min(success_times):.2f} ms")
        print(f"Máxima: {max(success_times):.2f} ms")
        print(f"Mediana: {statistics.median(success_times):.2f} ms")
        print(f"Throughput Global: {len(success_times) / total_time:.2f} requisições/segundo")
    else:
        print("❌ Nenhuma requisição teve sucesso. Verifique se a nuvem está no ar.")

    if errors:
        print(f"\n⚠️ Erros encontrados: {len(errors)}")
        print(f"Primeiro erro: {errors[0]['error'] if errors[0]['error'] else f'HTTP {errors[0]['status']}'}")

if __name__ == "__main__":
    run_benchmark()
