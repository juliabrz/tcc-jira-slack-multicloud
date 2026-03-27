import requests
import os
import time
import concurrent.futures
import csv
import statistics
import sys

# ==============================================================================
# CONFIGURAÇÕES DO TESTE (EDITE AQUI PARA CADA CENÁRIO)
# ==============================================================================

# 1. Escolha o nome do provedor para salvar no arquivo (LOCAL, AWS, AZURE)
PROVIDER_NAME = "LOCAL" 

# 2. Cole a URL correta do seu ambiente
# LOCAL:
TARGET_URL = "https://830a25454c27.ngrok-free.app/benchmark/load"
# AWS (Exemplo):
# TARGET_URL = "https://xyz.awsapprunner.com/benchmark/load"
# AZURE (Exemplo):
# TARGET_URL = "https://tcc-app.azurecontainerapps.io/benchmark/load"

# 3. Configurações de Carga
TOTAL_REQUESTS = 100    # Total de requisições para enviar
CONCURRENCY = 10        # Usuários simultâneos (Threads)
TIMEOUT = 10            # Tempo limite em segundos para cada req

# ==============================================================================

def send_request(req_id):
    """
    Envia uma requisição e mede o tempo de ida e volta (Round Trip Time)
    """
    payload = {
        "latency_ms": 0, # Pede para o servidor não dormir, queremos testar a rede/processamento puro
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
    print(f"\n🚀 INICIANDO BENCHMARK: [{PROVIDER_NAME}]")
    print(f"URL Alvo: {TARGET_URL}")
    print(f"Carga: {TOTAL_REQUESTS} requests | {CONCURRENCY} threads\n")
    
    results = []
    start_global = time.time()
    
    # Executa em paralelo usando Threads
    with concurrent.futures.ThreadPoolExecutor(max_workers=CONCURRENCY) as executor:
        futures = {executor.submit(send_request, i): i for i in range(TOTAL_REQUESTS)}
        
        completed = 0
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            results.append(res)
            
            completed += 1
            # Barra de progresso simples
            if completed % 10 == 0:
                sys.stdout.write(f"\rProcessados: {completed}/{TOTAL_REQUESTS}")
                sys.stdout.flush()

    total_time = time.time() - start_global
    print(f"\n\n✅ Teste finalizado em {total_time:.2f} segundos.")

    # --- SALVAR CSV ---
    filename = os.path.join("data", "output", "stats", f"resultado_stress_{PROVIDER_NAME}_2.csv")
    
    # Filtra apenas sucessos para o cálculo estatístico
    success_times = [r["duration_ms"] for r in results if r["status"] == 200]
    errors = [r for r in results if r["status"] != 200]

    with open(filename, mode='w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["provider", "request_id", "status", "duration_ms", "error"])
        
        for r in results:
            writer.writerow([PROVIDER_NAME, r["id"], r["status"], f"{r['duration_ms']:.2f}", r["error"]])
            
    print(f"📁 Dados salvos em: {filename}")

    # --- RELATÓRIO FINAL ---
    print("\n--- RESUMO ESTATÍSTICO ---")
    if success_times:
        print(f"Sucessos: {len(success_times)} / {TOTAL_REQUESTS}")
        print(f"Média Latência: {statistics.mean(success_times):.2f} ms")
        print(f"Mínima: {min(success_times):.2f} ms")
        print(f"Máxima: {max(success_times):.2f} ms")
        print(f"Mediana: {statistics.median(success_times):.2f} ms")
        print(f"Throughput: {len(success_times) / total_time:.2f} req/s")
    else:
        print("❌ Nenhuma requisição teve sucesso. Verifique a URL ou o servidor.")

    if errors:
        print(f"\n⚠️ Erros encontrados: {len(errors)}")
        print(f"Primeiro erro: {errors[0]['error']}")

if __name__ == "__main__":
    run_benchmark()