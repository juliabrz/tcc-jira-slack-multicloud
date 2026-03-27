# 📊 Resultados do Benchmark: Transito de Filas Multi-Cloud

Este documento consolida os resultados do teste de estresse (Carga de 50 conexões paralelas) realizado nas camadas de Fila Assíncrona do projeto. O objetivo das medições abaixo é registrar a performance End-to-End da infraestrutura e as diferenças arquiteturais entre **Amazon Web Services (AWS)** e a **Microsoft Azure**.

---

## 🟩 Microsoft Azure (Storage Queue + Python Functions V2)
No teste da Microsoft Azure rodando sobre o Plano de Consumo Dinâmico (Linux), os Triggers Internos atrelados à **Storage Queue** apresentaram um comportamento de alto desempenho.

* **Amostras:** 50 executadas com sucesso.
* **Menor Tempo Registrado:** `10.43 ms` (Praticamente instantâneo).
* **Maior Tempo Registrado:** `449.11 ms` (Primeiro disparo de Cold Start).
* **Média Global Observada:** `110 ~ 130 ms`.

### 💡 Análise de Comportamento
O modelo de Triggers Assíncronos da Azure conta com um componente embutido chamado **Scale Controller**. Este controlador faz um *Polling* agressivo no disco da Fila de Armazenamento toda vez que detecta picos de carga ou enfileiramento anormal. A comunicação da mensagem vinda do App Services para a Fila (I/O) até chegar na Função Final corre tão rapidamente que a demora não ultrapassa uma casa decimal comum, sendo espetacular para processamento nativo em background.

---

## 🟧 Amazon Web Services (SQS + Lambda)
A estratégia de testes de carga focada no modelo SQS -> Lambda da Amazon Web Services revelou dados que espelham sua filosofia de precificação "On-Demand", resultando numa piora proposital de latência em cenários de teste rápido. 

* **Amostras:** 50 executadas com sucesso.
* **Menor Tempo Registrado:** `1078.81 ms` (Aproximadamente 1 segundo).
* **Maior Tempo Registrado:** `4106.20 ms` (Aproximadamente 4 segundos).
* **Média Global Observada:** `2500 ~ 3500 ms`.

### 💡 Análise de Comportamento
A discrepância de 4.000 milissegundos ocorre, em grande maioria, por conta do algoritmo do Serverless Framework AWS de **Batch Window**. Em ambientes sem reserva fixa de instâncias (Puro Lambda), a nuvem da AWS tenta agrupar agressivamente as requisições num pacote único (Delay Interno) antes de acender um container de código Python em frio (Cold Start). Isso atrasa o processamento individual em milhares de milissegundos para gerar economia máxima em massa. O tráfego do Gateway HTTP é excelente na AWS, mas o processamento SQS é "relaxado".

---

## 🏆 Conclusão Arquitetural

A utilização do padrão de Desenvolvimento *Agnostic Cloud* através de Injeção de Dependências provou seu real valor comercial neste TCC.

Se tivéssemos amarrado todo o ecossistema e SDKs num código restrito da Amazon AWS, as chamadas longas do SQS prejudicariam ativamente a velocidade de respostas dos cards no Slack. Migrando a variável `CLOUD_PROVIDER` para a **Azure**, a empresa e o TCC ganham a habilidade de resolver fluxos secundários assíncronos com a velocidade impecável do Scale Controller V2 sem reescrever uma única linha de *Business Logic*!
