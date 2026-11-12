# Roadmap

## API e ingestão — concluído

API FastAPI com `/health`, `/simulate` e OpenAPI. O simulador compara duas taxas hipotéticas; a ingestão reúne documentos públicos da Receita e da Câmara com metadados de origem.

## Busca semântica — concluído no recorte inicial

Embeddings E5 em ONNX, busca exata em NumPy e consulta de fontes por `/sources`. O índice cobre duas páginas explicativas e onze artigos da LC 214. A avaliação inicial compara a recuperação com um baseline TF-IDF.

A cobertura integral da lei, as remissões e o tratamento de tabelas continuam pendentes. A escolha do recorte e do modelo está em [DECISIONS.md](DECISIONS.md).

## Respostas com LLM — implementação inicial

- [x] Integrar a Groq por HTTP com configuração local e saída estruturada.
- [x] Criar `/ask`, usando os trechos recuperados como contexto.
- [x] Conferir referências, trechos literais e números; montar fontes a partir do índice.
- [x] Implementar decisão de abstenção e revisão das afirmações em uma segunda chamada.
- [x] Testar contratos, falhas do provedor e descarte de rascunhos sem suporte com fixtures.
- [x] Verificar uma resposta com fonte e duas abstenções com o LLM real.
- [ ] Ampliar a avaliação, incluindo perguntas numéricas, e revisar suporte, citações e latência.

Os três casos iniciais estão em [rag-initial-validation.json](../reports/rag-initial-validation.json). A amostra não substitui a avaliação ampliada nem a revisão da interpretação jurídica.

## Interface — primeira versão concluída

Interface em Vue.js com TypeScript para perguntas, fontes e simulador. Inclui citações expansíveis, estados de espera, abstenção, erros de conexão e cota, validação de parâmetros e navegação adaptada ao celular. O frontend compilado pode ser servido pela FastAPI, no mesmo endereço.

Os testes do navegador usam fixtures de contrato. Uma verificação separada usou a API e o LLM reais, conferindo os trechos citados no corpus e um cálculo hipotético. Execução e comandos estão em [FRONTEND.md](FRONTEND.md).

## Hospedagem — pendente

Publicar a API com o índice e configurar o LLM no servidor. Validar memória, cotas, concorrência e limites de consultas antes de abrir a demonstração. O build estático da interface está pronto; uma hospedagem separada precisa de configuração explícita das origens permitidas. Cadastro e histórico privado ficam fora desta entrega.

## Série econômica — entrega planejada

Selecionar uma série pública pertinente ao mercado de alimentação, verificando cobertura, frequência e condições de reutilização no IBGE ou Banco Central. Começar com um único alvo, divisão cronológica, baseline sazonal e regressão com lags e calendário. Publicar MAE/RMSE observados e expor a inferência na API e na interface. Essa previsão ficará separada da simulação tributária e não será apresentada como efeito causal da reforma.

## Validação

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m scripts.evaluate_retrieval
.\.venv\Scripts\python.exe scripts/smoke_api.py --retrieval
```

A avaliação e o teste de busca pela API exigem o modelo e o índice preparados conforme o [README](../README.md).
