import time
import csv
import os

LOG_FILE = "dados_tcc.csv"

def init_log():
    # Na arquitetura serverless apenas confiamos nos logs em nuvem.
    pass

def log_metric(provider, flow, operation, start_time, entity_id="N/A", tag=""):
    end_time = time.time()
    duration = (end_time - start_time) * 1000 # ms
    
    csv_line = f"{provider},{flow},{operation},{end_time:.4f},{duration:.2f},{entity_id},{tag}"
    print(f"[METRICS] {csv_line}")