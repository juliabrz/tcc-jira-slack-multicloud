import os
import csv
import statistics
import matplotlib.pyplot as plt

def read_data(filepath):
    """Lê as durações ms (apenas os sucessos) do CSV fornecido."""
    latencies = []
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['status'] == '200':
                    latencies.append(float(row['duration_ms']))
    return latencies

def create_boxplot():
    print("🎨 Gerando o Gráfico Comparativo de Boxplot...")
    
    # Busca dinamicamente na pasta de relatórios
    base_dir = os.path.join("data", "output", "stats")
    aws_file = os.path.join(base_dir, "resultado_stress_AWS_cloud.csv")
    azure_file = os.path.join(base_dir, "resultado_stress_AZURE_cloud.csv")
    
    # Extrai a coluna de milissegundos
    aws_data = read_data(aws_file)
    azure_data = read_data(azure_file)
    
    if not aws_data and not azure_data:
        print("❌ Nenhum dado CSV encontrado. Certifique-se de executar o cloud_stress_test.py para ambas as nuvens primeiro!")
        return
        
    data_to_plot = []
    labels = []
    colors = []
    
    if aws_data:
        data_to_plot.append(aws_data)
        labels.append("AWS Serverless\n(API Gateway)")
        colors.append('#FF9900') # Laranja AWS
        
    if azure_data:
        data_to_plot.append(azure_data)
        labels.append("Azure Serverless\n(App Services)")
        colors.append('#0078D4') # Azul Microsoft
        
    # Inicializa o tamanho da figura
    plt.figure(figsize=(9, 6))
    
    # Desenha o Boxplot
    box = plt.boxplot(data_to_plot, patch_artist=True, labels=labels, 
                      boxprops=dict(alpha=0.8),
                      medianprops=dict(color="black", linewidth=1.5),
                      flierprops=dict(marker='o', color='red', alpha=0.5))
    
    # Aplica as cores das provedores Cloud nos blocos
    for patch, color in zip(box['boxes'], colors):
        patch.set_facecolor(color)
        
    # Estiliza os textos e os Eixos do Gráfico
    plt.title('Dispersão de Latência HTTP (Boxplot)\nAWS vs Azure', fontsize=16, pad=20, weight='bold')
    plt.ylabel('Latência em Milissegundos (ms)', fontsize=12, weight='bold')
    plt.grid(axis='y', linestyle='--', alpha=0.6)
    
    # Roda as três estatísticas puras no Canvas (Média, Menor, Maior)
    for i, d in enumerate(data_to_plot, 1):
        if d:
            med = statistics.median(d)
            mean = statistics.mean(d)
            q1 = sorted(d)[len(d)//4]
            q3 = sorted(d)[3*len(d)//4]
            iqr = q3 - q1
            min_whisker = sorted(d)[0]
            max_whisker = sorted(d)[-1]
            
            plt.text(i, med, f'{med:.1f}ms', horizontalalignment='center', color='black', weight='bold', verticalalignment='bottom')
            print(f"[{labels[i-1]}] Média: {mean:.1f}ms | Mediana: {med:.1f}ms | Amplitude (Pior caso): {max_whisker:.1f}ms")

    # Garante que as pastas de salvamento existem
    os.makedirs(base_dir, exist_ok=True)
    
    output_img = os.path.join(base_dir, "boxplot_latencia_multicloud.png")
    plt.savefig(output_img, dpi=300, bbox_inches='tight')
    
    print(f"\n📊 Sucesso! O arquivo de imagem foi salvo em: {output_img}")
    print("🖼️ Abrindo o gráfico na sua tela agora...")
    
    # Tenta abrir o gráfico na tela interativa da usuária
    try:
        plt.show()
    except Exception as e:
        print("Visualização de tela bloqueada (mas o arquivo '.png' foi gerado corretamente na pasta!)")

if __name__ == "__main__":
    create_boxplot()
