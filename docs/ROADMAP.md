# Roadmap

## API e ingestão — concluído

API FastAPI com `/health`, `/simulate` e OpenAPI. O simulador compara duas taxas hipotéticas; a ingestão reúne documentos públicos da Receita e da Câmara com metadados de origem.

## Busca semântica — concluído no recorte inicial

Embeddings E5 em ONNX, busca exata em NumPy e consulta de fontes por `/sources`. O índice cobre duas páginas explicativas e onze artigos da LC 214. A avaliação inicial compara a recuperação com um baseline TF-IDF.

A cobertura integral da lei, as remissões e o tratamento de tabelas continuam pendentes. A escolha do recorte e do modelo está em [DECISIONS.md](DECISIONS.md).

## Respostas com LLM — próxima etapa

- [ ] Escolher um backend compatível com os recursos de execução.
- [ ] Criar `/ask`, usando os trechos recuperados como contexto.
- [ ] Incluir título, URL e trecho nas citações e conferir se correspondem às fontes.
- [ ] Tratar perguntas fora do escopo ou sem evidência suficiente.
- [ ] Avaliar suporte das afirmações, números, citações e latência.

A entrega deve incluir uma pergunta respondida com fonte verificável e uma pergunta recusada por falta de suporte, usando o backend real.

## Demonstração — planejado

Interface simples em Streamlit ou Gradio para explorar perguntas e fontes. A hospedagem depende da validação do backend e do consumo de recursos.

## Série econômica — extensão futura

Explorar uma série pública com divisão cronológica, baseline e métricas de erro. Essa previsão ficará separada da simulação tributária e não será apresentada como efeito causal da reforma.

## Validação

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m scripts.evaluate_retrieval
.\.venv\Scripts\python.exe scripts/smoke_api.py --retrieval
```

A avaliação e o teste de busca pela API exigem o modelo e o índice preparados conforme o [README](../README.md).
