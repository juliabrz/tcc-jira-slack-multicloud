import os
import csv
import matplotlib.pyplot as plt

def read_stability_data(filepath):
    """Extrai IDs sequenciais de requisição e sua respectiva Duração (Em caso de erro lança Y no chão)."""
    req_ids = []
    latencies = []
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['status'] == '200':
                    req_ids.append(int(row['request_id']))
                    latencies.append(float(row['duration_ms']))
                else:
                    # Em caso de erro HTTP 500, manda o ping para zero visualmente
                    req_ids.append(int(row['request_id']))
                    latencies.append(0.0)
    return req_ids, latencies

def plot_stability_chart():
    print("📈 Iniciando a Renderização do Gráfico de Estabilidade...")
    base_dir = os.path.join("data", "output", "stats")
    
    aws_file = os.path.join(base_dir, "resultado_stress_AWS_cloud.csv")
    azure_file = os.path.join(base_dir, "resultado_stress_AZURE_cloud.csv")
    
    aws_x, aws_y = read_stability_data(aws_file)
    az_x, az_y = read_stability_data(azure_file)
    
    if not (aws_y or az_y):
        print("❌ Nenhum dado CSV Front-end (API) foi encontrado.")
        return
        
    plt.figure(figsize=(10, 6))
    
    # Plota a linha da AWS
    if aws_x:
        # Reordena os dados pelo ID da requisição, porque o ThreadPool paralelo devolve as respostas fora de ordem cronológica
        aws_sorted = sorted(zip(aws_x, aws_y))
        x_aws = [v[0] for v in aws_sorted]
        y_aws = [v[1] for v in aws_sorted]
        plt.plot(x_aws, y_aws, marker='o', linestyle='-', color='#FF9900', label='AWS (API Gateway)', alpha=0.9, linewidth=2.5)
        
    # Plota a linha da AZURE
    if az_x:
        az_sorted = sorted(zip(az_x, az_y))
        x_az = [v[0] for v in az_sorted]
        y_az = [v[1] for v in az_sorted]
        plt.plot(x_az, y_az, marker='s', linestyle='-', color='#0078D4', label='Azure (App Services)', alpha=0.9, linewidth=2.5)
    
    # Estilizando as Definições do Eixo
    plt.title('Curva de Estabilidade HTTP sob Estresse Paralelo\nTempo de Resposta Contínuo (Cold Start e Jitter)', fontsize=15, pad=20, weight='bold')
    plt.xlabel('Número Cronológico da Requisição', fontsize=12, weight='bold')
    plt.ylabel('Latência em Milissegundos (ms)', fontsize=12, weight='bold')
    
    # Inclui Legenda Clara
    plt.legend(title='API Resolvers', title_fontsize='11', fontsize='10', loc='upper right')
    
    # Insere uma grade visual (Grid)
    plt.grid(axis='both', linestyle='--', alpha=0.5)
    
    # Configura um chão no Gráfico para evitar que os dados flutuem bizarramente
    plt.ylim(bottom=0)
    
    # Salva o arquivo em formato PNG Imagem
    output_img = os.path.join(base_dir, "grafico_estabilidade.png")
    plt.savefig(output_img, dpi=300, bbox_inches='tight')
    
    print(f"\n✅ Concluído! O Gráfico de Estabilidade Científica está pronto em: {output_img}")
    print("🖼️ Tentando plotar a interface gráfica na sua tela agora...")
    
    try:
        plt.show()
    except Exception as e:
        print("Finalizado.")

if __name__ == "__main__":
    plot_stability_chart()
