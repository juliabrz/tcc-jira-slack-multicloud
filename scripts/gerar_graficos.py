import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

# ==============================================================================
# CONFIGURAÇÃO
# ==============================================================================
# Nome do arquivo CSV que você gerou (Use o do teste via Ngrok ou Local)
ARQUIVO_CSV = "resultado_stress_LOCAL_ngrok.csv"  # <--- SEU CSV AQUI

# Dados manuais para comparação (Baseado nos seus testes e estimativa do Jira)
# Cenário Síncrono: 2000ms (Jira) + 600ms (Rede) = ~2600ms
# Cenário Assíncrono (Seu): 606ms (Média do seu teste Ngrok)
COMPARATIVO = {
    "Cenários": ["Tradicional (Síncrono)", "Proposto (Assíncrono)"],
    "Tempo Médio (ms)": [2600, 606], # Ajuste aqui conforme seus resultados
    "Cor": ["#e74c3c", "#2ecc71"] # Vermelho vs Verde
}

# Estilo "Acadêmico"
sns.set_theme(style="whitegrid")
plt.rcParams.update({'font.size': 12, 'font.family': 'sans-serif'})

def plotar_comparativo():
    """Gera o Gráfico de Barras comparando Síncrono vs Assíncrono"""
    plt.figure(figsize=(8, 6))
    
    df_comp = pd.DataFrame(COMPARATIVO)
    
    # Criar Gráfico de Barras
    ax = sns.barplot(x="Cenários", y="Tempo Médio (ms)", data=df_comp, palette=COMPARATIVO["Cor"])
    
    # Títulos e Labels
    plt.title("Comparativo de Latência: Tradicional vs. Event-Driven", fontsize=14, fontweight='bold', pad=20)
    plt.ylabel("Tempo de Resposta (ms)")
    plt.xlabel("")
    
    # Adicionar os valores em cima das barras
    for p in ax.patches:
        height = p.get_height()
        ax.text(p.get_x() + p.get_width() / 2., height + 50,
                f'{int(height)} ms', ha="center", va="bottom", fontsize=12, fontweight='bold')

    # Adicionar seta de ganho
    ganho = COMPARATIVO["Tempo Médio (ms)"][0] / COMPARATIVO["Tempo Médio (ms)"][1]
    plt.text(0.5, 2000, f"Running {ganho:.1f}x Faster 🚀", 
             ha='center', va='center', fontsize=12, color='green', 
             bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="green", lw=2))

    # Salvar
    plt.tight_layout()
    plt.savefig("grafico_comparativo_ngrok.png", dpi=300)
    print("✅ Gráfico Comparativo salvo como 'grafico_comparativo.png'")
    plt.show()

def plotar_estabilidade():
    """Lê o CSV e gera o gráfico de linha das 100 requisições"""
    try:
        df = pd.read_csv(ARQUIVO_CSV)
        
        # Filtra apenas sucessos (Status 200)
        df = df[df['status'] == 200]
        
        if df.empty:
            print("⚠️ O CSV está vazio ou sem sucessos (status 200).")
            return

        plt.figure(figsize=(10, 5))
        
        # Plotar Linha
        sns.lineplot(x="request_id", y="duration_ms", data=df, marker="o", color="#3498db", linewidth=2)
        
        # Linha de Média
        media = df["duration_ms"].mean()
        plt.axhline(media, color='red', linestyle='--', label=f'Média: {media:.1f} ms')
        
        # Títulos
        plt.title("Estabilidade do Sistema sob Carga (100 Requisições)", fontsize=14, fontweight='bold', pad=15)
        plt.xlabel("ID da Requisição")
        plt.ylabel("Latência (ms)")
        plt.legend()
        
        # Salvar
        plt.tight_layout()
        plt.savefig("grafico_estabilidade_ngrok.png", dpi=300)
        print("✅ Gráfico de Estabilidade salvo como 'grafico_estabilidade.png'")
        plt.show()

    except FileNotFoundError:
        print(f"❌ Erro: Não encontrei o arquivo '{ARQUIVO_CSV}'. Verifique o nome.")

if __name__ == "__main__":
    print("--- GERANDO GRÁFICOS PARA O TCC ---")
    plotar_comparativo()
    print("-" * 30)
    plotar_estabilidade()