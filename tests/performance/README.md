# 📊 Suite de Testes de Estresse Multi-Cloud

Este diretório contém os scripts desenvolvidos para testar a resiliência corporativa e a escalabilidade (Gateway e Filas) das arquiteturas **AWS** e **Azure**. 

O script principal chama-se `cloud_stress_test.py` e ele simula dezenas de mensagens simultâneas originárias do Slack, sendo um instrumento valioso para as análises do Trabalho de Conclusão de Curso (TCC).

## 🛠 Como o Teste Funciona

O script utiliza paralelismo (`ThreadPoolExecutor` do Python) para "atacar" as APIs do Cloud Bot com muitas requisições simultâneas. Por ser parametrizável, ele evita poluir seu Jira com lixo ou estourar a sua cota grátis na nuvem.

### Variáveis de Controle
Ao abrir o `cloud_stress_test.py`, você verá duas variáveis cruciais no cabeçalho:

1. `PROVIDER_NAME`: Controla para qual nuvem o bombardeio HTTP será direcionado (`AWS` ou `AZURE`).
2. `TEST_ROUTE`: Decide a "profundidade" do estresse:
   - `"SLACK"`: Testa apenas a camada superficial (O API Gateway na Amazon ou o App Services na Microsoft). Serve para provar à banca do TCC que a Nuvem responde ao usuário do Slack em sub-milissegundos e não gera erro de "Timeout".
   - `"BENCHMARK"`: Bate na rota raiz do *Worker*. Ele força a Nuvem a enlatar dezenas de mensagens reais nas Filas Autogerenciadas (SQS/Storage Queues).

## 🚀 Como Executar

Abra seu terminal na raiz do projeto (onde fica o `requirements.txt`) e dispare o script:

```bash
python3 tests/performance/cloud_stress_test.py
```

O terminal mostrará uma barra de progresso em tempo real e, ao final, imprimirá um resumo com as médias de tempo e o *Throughput* (Vazão) Global do servidor suportado.

## 📈 Extraindo Métricas End-to-End (Bônus para o TCC)

O arquivo CSV gerado (salvo em `data/output/stats/`) vai lhe mostrar a velocidade com que as APIs responderam. Porém, em uma **Arquitetura Desacoplada**, a verdadeira métrica de "Sucesso" é o tempo que levou entre a API dizer *"OK"* e o computador da nuvem processar a mensagem do fundo da Fila. 

Se você optou pela variável `TEST_ROUTE = "BENCHMARK"`, o nosso Bot na nuvem irá imprimir nos painéis originais um log mágico do tempo que a mensagem demorou em trânsito.

- **Na AWS:** Vá no **CloudWatch** > Logs Insights, selecione o log group do Worker e execute:
  ```sql
  fields @timestamp, @message
  | filter @message like /\[METRICS\] AWS,Worker,execution_benchmark_queue/
  | sort @timestamp desc
  | limit 100
  ```

- **Na Microsoft Azure:** Vá em **Application Insights** > Logs e execute:
  ```kusto
  traces 
  | where message contains "[METRICS] AZURE,Worker,execution_benchmark_queue"
  | project timestamp, message
  | order by timestamp desc
  ```

Pegue a média milissegundos dessas consultas, coloque-as lado a lado nas Suas Conclusões e prove cientificamente qual nuvem tem as filas assíncronas operando melhor com o Python Serverless! 🏆
