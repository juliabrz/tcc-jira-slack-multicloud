import os
import csv
import statistics
import matplotlib.pyplot as plt

def extract_queue_latency(filepath, message_col):
    """
    Lê o arquivo CSV exportado da Nuvem, encontra a coluna da mensagem bruta
    e recorta a string do log (ex: [METRICS] AZURE,Worker,...,115.41,BENCHMARK,)
    para extrair o valor de duração em Float.
    """
    latencies = []
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                msg = row.get(message_col, "")
                
                # Procura fatiar nossa linha mágica gerada pelo TCC
                if "[METRICS]" in msg and "BENCHMARK" in msg:
                    parts = msg.split(',')
                    try:
                        # No formato: [METRICS] NUVEM,ROLE,ACTION,TIMESTAMP_START,LATENCY_MS,BENCHMARK
                        # O índice [4] será a Latência em Milissegundos
                        val = float(parts[4])
                        latencies.append(val)
                    except ValueError:
                        continue
    return latencies

def create_queue_chart():
    print("🎨 Iniciando parser dos arquivos nativos de Log da Nuvem...")
    
    base_dir = os.path.join("data", "output", "stats")
    
    # Arquivos exatos que a usuária salvou
    aws_file = os.path.join(base_dir, "CloudWatch_Logs.csv")
    azure_file = os.path.join(base_dir, "Application_Insights_Logs.csv")
    
    aws_data = extract_queue_latency(aws_file, "@message")
    azure_data = extract_queue_latency(azure_file, "message")
    
    if not aws_data and not azure_data:
        print("❌ Nenhum dado CSV foi encontrado em data/output/stats/ ou eles estão vazios.")
        return
        
    data_to_plot = []
    labels = []
    colors = []
    
    if aws_data:
        data_to_plot.append(aws_data)
        labels.append("AWS Serverless\n(Amazon SQS Polling)")
        colors.append('#FF9900') # Laranja AWS
        
    if azure_data:
        data_to_plot.append(azure_data)
        labels.append("Azure Serverless\n(Storage Queue Trigger)")
        colors.append('#0078D4') # Azul Azure
        
    # Inicializa o Canvas
    plt.figure(figsize=(9, 6))
    
    # Desenha o Boxplot
    box = plt.boxplot(data_to_plot, patch_artist=True, labels=labels, 
                      boxprops=dict(alpha=0.8),
                      medianprops=dict(color="black", linewidth=1.5),
                      flierprops=dict(marker='o', color='red', alpha=0.5))
    
    # Aplica as cores das provedores Cloud nos blocos
    for patch, color in zip(box['boxes'], colors):
        patch.set_facecolor(color)
        
    # Estiliza os textos e os Eixos do Gráfico (Nota a Escala brutal!)
    plt.title('Dispersão do Trânsito em Fila Assíncrona\nEscala de Latência End-to-End', fontsize=16, pad=20, weight='bold')
    plt.ylabel('Latência em Milissegundos (ms)', fontsize=12, weight='bold')
    plt.grid(axis='y', linestyle='--', alpha=0.6)
    
    # Anota Medianas nas Caixas
    for i, d in enumerate(data_to_plot, 1):
        if d:
            med = statistics.median(d)
            mean = statistics.mean(d)
            max_whisker = sorted(d)[-1]
            
            # Anota a Mediana ao lada da caixa para melhor leitura
            plt.text(i, med * 1.05, f'{med:.1f}ms', horizontalalignment='center', color='black', weight='bold')
            print(f"[{labels[i-1].replace(chr(10), ' ')}] Média de Tempo Morto na Fila: {mean:.1f}ms | Pior Cenário: {max_whisker:.1f}ms")

    # Salva o resultado visual
    output_img = os.path.join(base_dir, "boxplot_filas_nuvem_oculta.png")
    plt.savefig(output_img, dpi=300, bbox_inches='tight')
    
    print(f"\n📊 Incrível! A grande prova do TCC acaba de ser gerada em: {output_img}")
    print("🖼️ Abrindo o gráfico na sua tela agora...")
    
    try:
        plt.show()
    except Exception as e:
        print("Visualização de tela bloqueada via terminal.")

if __name__ == "__main__":
    create_queue_chart()
