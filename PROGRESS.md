# Progresso — TaxMind AI

## 11/11/2026 — API e ingestão documental

Primeira versão do projeto: API FastAPI, comparação determinística de cenários hipotéticos e pipeline de coleta e preparação de documentos oficiais.

### Estado comprovado após a entrega

| Componente | Estado | Evidência |
| --- | --- | --- |
| Auditoria e plano de entregas | FEITO | `docs/AUDIT.md`, `docs/ROADMAP.md` |
| Ambiente e dependências | FEITO localmente | Python 3.12.14, venv, lock de versões; `pip check` aprovado |
| FastAPI, `/health`, OpenAPI e `/docs` | FEITO | Testes de contrato e HTTP real |
| `/simulate` determinístico | FEITO no escopo hipotético | Validação, Decimal, arredondamento, fórmula e aviso |
| Ingestão de documentos oficiais | FEITO para as três fontes selecionadas | `reports/ingestion.json` e snapshots locais |
| Extração, chunks e proveniência | FEITO como base inicial | IDs, offsets e hashes; ainda sem segmentação jurídica |
| RAG completo | PARCIAL | Ingestão pronta; embeddings, índice, retrieval e geração ausentes |
| LLM, `/ask`, citações e recusa de perguntas | NÃO INICIADO | Nenhum modelo executado ou endpoint de pergunta implementado |
| Avaliação de retrieval e geração | NÃO INICIADO | Testes atuais não medem fundamentação de respostas |
| Interface e demo publicada | NÃO INICIADO | Sem URL de publicação |
| ML econômico | NÃO INICIADO | Sem dataset, treinamento ou métricas |

### Execuções observadas

Comandos executados a partir de `taxmind-ai`:

```powershell
.\.venv\Scripts\python.exe -m pytest -q --junitxml=reports/pytest.xml
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m app.ingestion
.\.venv\Scripts\python.exe scripts/smoke_api.py
```

- **38 testes passaram**, sem falhas, erros ou testes ignorados. Saída do pytest: 2,01 s. O XML registra 1,848 s para a suíte; os dois tempos usam escopos diferentes. Resumo em `reports/tests.json`; XML local ignorado pelo Git.
- Houve **um aviso de depreciação de Starlette/TestClient com HTTPX**. Não foi falha de execução. Reavaliar a migração para HTTPX2 quando atualizar o conjunto de dependências; versões atuais estão registradas no lock.
- `pip check`: **No broken requirements found**.
- **HTTP real aprovado** para `/health`, `/openapi.json`, `/docs` e `/simulate`, com Uvicorn temporário no loopback. O processo foi encerrado pelo script ao final. Evidência: `reports/api-smoke.json`.
- **Coleta real: 3 documentos e 1.012 chunks**: Receita/Entenda (7), Receita/Comunicado (6), Câmara/LC 214 atualizada (999). Proveniência em `reports/ingestion.json`. Inspeção dos textos coletados não encontrou caracteres de substituição U+FFFD.
- Verificação adicional do corpus real: hashes dos HTMLs e textos correspondem aos metadados; os 1.012 trechos correspondem aos offsets registrados e têm IDs únicos. JSONs do projeto foram lidos sem erro. `.gitignore` verificado para venv, `.env`, snapshots, corpus e log local.
- Os testes de ingestão usam HTML sintético identificado como fixture técnica, sem texto legal inventado. A coleta real foi uma execução separada, com internet.

Os testes cobrem cálculo e validação HTTP, limites, arredondamento, diminuição de taxa, remoção de navegação/scripts/texto riscado, rejeição de fontes inválidas, bloqueios, offsets de chunks, estabilidade de IDs, redirecionamentos externos e preservação do corpus anterior em caso de falha. Isso comprova esses comportamentos; não comprova precisão tributária nem qualidade de RAG.

### Fontes e decisões

- [Receita — Entenda](https://www.gov.br/receitafederal/pt-br/acesso-a-informacao/acoes-e-programas/reforma-tributaria-do-consumo/entenda): coletada.
- [Receita — Comunicado Conjunto](https://www.gov.br/receitafederal/pt-br/assuntos/noticias/2025/dezembro/comunicado-conjunto): coletado; orientação temporalmente delimitada a 2026, sujeita a atos posteriores.
- [Câmara — LC 214 atualizada](https://www2.camara.leg.br/legin/fed/leicom/2025/leicomplementar-214-16-janeiro-2025-796905-normaatualizada-pl.html): coletada como alternativa oficial ao bloqueio observado no Planalto.

Esta versão executa localmente, sem chave de provedor de IA ou serviço pago. O corpus contém documentos públicos; o simulador usa parâmetros hipotéticos explícitos. Decisões de arquitetura em `docs/DECISIONS.md`.

### Próximo incremento

Revisar segmentação por artigo/seção, testar embeddings multilíngues e recuperação top-k com perguntas rotuladas; registrar versão do modelo e corpus. Só depois conectar um backend real de LLM, implementar `/ask` e avaliar citações, números e abstenções. A primeira entrega está concluída; o objetivo de RAG funcional permanece pendente.

## 11/11/2026 — preparação do repositório público

Documentação revisada para descrever o escopo técnico, instruções de execução e limitações. Arquivos pessoais, notas locais, ambiente virtual, snapshots, corpus gerado e logs são excluídos do versionamento. A publicação inclui código, testes, dependências, catálogo de fontes e relatórios das execuções verificadas.

Uma cópia contendo somente os 22 arquivos selecionados para publicação foi validada: 38 testes passaram em 1,43 s, com o mesmo aviso de depreciação registrado na primeira execução. O smoke com HTTP real passou para as quatro rotas verificadas. A revisão do conteúdo selecionado não identificou credenciais ou caminhos pessoais.

Repositório público: [clarak-dev/taxmind-ai](https://github.com/clarak-dev/taxmind-ai), branch `main`. Após o envio, os 22 arquivos remotos foram comparados com os hashes locais. O acesso à página e ao README foi confirmado sem autenticação. A publicação disponibiliza o código; a demonstração hospedada e o RAG completo continuam pendentes.

## 11/11/2026 — recuperação semântica local

### Implementado

- E5 multilingual-small quantizado em ONNX Runtime CPU, com prefixos de pergunta/documento, pooling por máscara e normalização L2. Modelo original de terceiros, sem treinamento ou fine-tuning neste projeto. Revisão e hashes em `config/embedding_model.json`; licença declarada e referência em `THIRD_PARTY_NOTICES.md`.
- Download explícito de dois arquivos públicos, aproximadamente 136 MB, sem autenticação ou execução de código remoto. Não são carregados pelo processo de API até a primeira busca.
- Segmentação por artigo/seção em módulo separado, preservando a ingestão e o corpus já coletado. Recorte inicial: duas páginas da Receita e onze artigos da LC 214, descrito em `config/retrieval_scope.json`.
- Índice local com **50 chunks, três fontes e 384 dimensões**. Produto interno de vetores unitários em NumPy, sem banco vetorial ou busca aproximada. Construção real registrada em `reports/index.json`: 6,475 s, incluindo carga do modelo.
- Índice ligado a hashes do corpus, modelo e recorte; validação dos artefatos, rejeição de incompatibilidade e ativação de nova geração somente após sucesso. Modelo e índice ficam fora do Git.
- `POST /search`: pergunta, top-k, trechos candidatos, seção, título, URL, offsets, data de acesso e ressalvas temporais. `GET /sources`: cadastro, coleta e quantidade efetivamente indexada. `/health` e `/simulate` preservados; versão da API 0.2.0.

### Validação e resultados observados

```powershell
.\.venv\Scripts\python.exe -m app.embeddings download
.\.venv\Scripts\python.exe -m app.retrieval build
.\.venv\Scripts\python.exe -m scripts.evaluate_retrieval
.\.venv\Scripts\python.exe scripts/smoke_api.py --retrieval
.\.venv\Scripts\python.exe -m pytest -q --junitxml=reports/pytest-retrieval.xml
.\.venv\Scripts\python.exe -m pip check
```

- **58 testes passaram** em 2,14 s, sem falhas ou skips. O XML registra 2,112 s no escopo da suíte. Incluem testes anteriores, fronteiras de artigos, offsets, pooling/normalização, ranking, proveniência, índices ausentes/corrompidos/desatualizados, preservação do índice após falha e contrato HTTP. Resumo em `reports/tests-retrieval.json`.
- `pip check` aprovado. As versões existentes foram preservadas na instalação, e o lock completo foi atualizado. O conjunto agora inclui HTTPX2 como dependência transitiva; o aviso de TestClient observado na primeira entrega não apareceu nesta execução.
- Smoke com Uvicorn e **modelo real** aprovado para `/sources` e `/search`, além das quatro rotas anteriores. Pergunta demonstrada: “O que é a CBS e de quem é sua competência?”. Fontes e trechos em `reports/retrieval-api-smoke.json`; o servidor temporário foi encerrado.
- Avaliação real com 16 perguntas: 3 de desenvolvimento, 8 de teste com âncoras esperadas e 5 diagnósticos fora do escopo ou sem documentação suficiente. Labels definidos antes da primeira execução; nenhum limiar ajustado pelo teste. A segunda execução atualizou o formato do relatório e repetiu os mesmos resultados de ranking, sem alterar modelo, recorte, perguntas ou parâmetros.
- No teste, E5: **Hit@1 = 5/8**, **Hit@3 = 7/8**, **Hit@5 = 8/8**, **MRR@5 = 0,78125**. Baseline lexical TF-IDF: **Hit@1 = 4/8**, **Hit@3 = 7/8**, **Hit@5 = 8/8**, **MRR@5 ≈ 0,69792**. Valores por caso e latências reais em `reports/retrieval-evaluation.json`.
- Proveniência conferida para **80 resultados semânticos**: trecho corresponde aos offsets no texto coletado, e título/URL correspondem ao documento de origem. O relatório público guarda referências e hashes dos trechos, evitando duplicar o corpus.
- Validação do conjunto de publicação: os 37 arquivos selecionados passaram pela revisão de credenciais e caminhos pessoais. Uma cópia contendo somente esses arquivos, sem pesos, corpus ou índice, executou os 58 testes em 2,29 s e o smoke da API básica. O smoke de recuperação com modelo real foi executado separadamente no ambiente preparado.

### Limitações e próxima entrega

**RAG com geração permanece parcial.** `/search` retorna vizinhos, inclusive para perguntas sem suporte. Scores altos nesses diagnósticos mostram que similaridade não equivale a confiança; não existe abstenção automática. Não há `/ask`, LLM, avaliação de afirmações ou interface de perguntas.

O teste tem apenas oito casos positivos, com rótulos parciais e algumas perguntas que mencionam artigos. Não permite concluir desempenho geral ou superioridade estatística. A LC está indexada parcialmente, sem resolução automática de remissões ou estrutura de tabelas. A segmentação atual pode deixar trechos explicativos curtos sem contexto suficiente.

Próximo incremento: backend de LLM configurável compatível com recursos disponíveis, respostas com citações e abstenção quando faltar evidência, além de avaliação própria de suporte e números. Qualquer conta ou custo precisa ser avaliado antes da integração.
