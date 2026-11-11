# Plano incremental

Plano de evolução do TaxMind AI. Cada entrega inclui testes e evidências de execução. O corpus usa documentos públicos; cenários de cálculo usam entradas hipotéticas explícitas.

## Entrega 1 — API e corpus oficial

Arquivos: `app/main.py`, `app/simulator.py`, `app/ingestion.py`, `data/sources.json`, `tests/`, dependências, `scripts/smoke_api.py`, `docs/` e `reports/`.

Critérios: `/health` e `/simulate` com OpenAPI; cálculo hipotético e validação; três fontes oficiais coletadas com metadados; chunks rastreáveis; falhas de coleta preservam corpus anterior. Comandos:

```powershell
.\.venv\Scripts\python.exe -m pytest -q --junitxml=reports/pytest.xml
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m app.ingestion
.\.venv\Scripts\python.exe scripts/smoke_api.py
```

Estado: concluída. Resultados em [PROGRESS.md](../PROGRESS.md). O endpoint de perguntas ainda não foi implementado.

## Entrega 2 — recuperação e geração

### 2A. Recuperação antes da geração

Arquivos previstos: `app/retrieval.py`, `app/ingestion.py`, `app/main.py`, `tests/test_retrieval.py`, `evaluation/questions.json` e `scripts/evaluate_retrieval.py`.

- Revisar chunks por seção/artigo e números em tabelas; preservar proveniência e escopo temporal.
- Verificar licença e requisitos de um modelo multilíngue de sentence-transformers; registrar versão/revisão, dimensão e normalização.
- Gerar embeddings locais; usar FAISS se a instalação e o volume justificarem. Índice deve registrar o hash do corpus e a revisão do modelo para evitar versões incompatíveis.
- Implementar top-k e `/sources`; separar documento cadastrado, coletado e efetivamente indexado.
- Criar perguntas rotuladas manualmente com trechos esperados, perguntas fora do escopo e casos com números. Medir recall@k, relevância e latência; não escolher limiar pelo conjunto final de teste.

Validação prevista:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts/evaluate_retrieval.py
```

Estado: planejada. Os novos arquivos e o comando de avaliação ainda não existem. A escolha do modelo depende da revisão de licença, tamanho e recursos locais.

### 2B. Respostas fundamentadas

Arquivos previstos: `app/generation.py`, `app/main.py`, `tests/test_ask.py`, `scripts/evaluate_rag.py` e, se necessário, `.env.example`.

- Escolher backend configurável de LLM, priorizando execução local; registrar requisitos de memória, latência e eventuais custos.
- Criar `/ask` com resposta, título, URL, trecho e identificador de chunk. Documentos são dados, nunca instruções para o modelo.
- Validar que citações apontam para chunks recuperados e que números têm suporte; abster-se quando não houver evidência suficiente. Limiar de similaridade isolado não prova suporte.
- Avaliar uma pergunta sustentada, uma fora do escopo, uma com documentação insuficiente e perguntas numéricas. Separar testes de contrato com mocks de avaliação real do modelo.
- Guardar respostas, fontes, cobertura de citações, avaliação de suporte e latência em `reports/`; indicar método manual/automático e tamanho da amostra.

Critério: ao menos uma resposta com trecho oficial verificável e uma recusa observadas com backend real. Não declarar o RAG pronto com base apenas em testes mockados.

## Entrega 3 — demonstração

Interface simples em Streamlit ou Gradio para pergunta, fontes e limitações. Hospedagem de uma demonstração após validar o backend e as respostas com documentos oficiais.

## Extensão futura — série econômica

Avaliar uma série pública com divisão cronológica, baseline ingênuo/sazonal e MAE/RMSE reais. A inferência deve ser separada da simulação tributária e não representar uma estimativa causal dos efeitos da reforma.
