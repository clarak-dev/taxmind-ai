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
