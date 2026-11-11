# Auditoria inicial — 11/11/2026

## Escopo

Revisão da primeira versão do TaxMind AI: contrato HTTP, simulador hipotético, preparação de documentos públicos e limitações para a próxima etapa de RAG. O projeto foi iniciado sem base de código anterior.

## Estado verificado

| Item | Estado | Evidência |
| --- | --- | --- |
| API e OpenAPI | IMPLEMENTADO | `/health`, `/simulate`, `/docs` e `/openapi.json`; smoke com HTTP real |
| Simulador | IMPLEMENTADO no escopo hipotético | Decimal, validação de limites, arredondamento e aviso de limitações |
| Ingestão e chunks | IMPLEMENTADO | Três fontes oficiais, metadados, hashes e offsets verificados |
| Testes | IMPLEMENTADO | 38 casos aprovados na execução registrada em `reports/tests.json` |
| Embeddings e índice | PENDENTE | Nenhum modelo de embeddings executado |
| LLM e `/ask` | PENDENTE | Sem geração de respostas |
| Avaliação do RAG | PENDENTE | Não há métricas de recuperação ou suporte de respostas |
| Interface | PENDENTE | API disponível localmente, sem interface de perguntas |

Histórico de execução em [PROGRESS.md](../PROGRESS.md); entregas previstas no [roadmap](ROADMAP.md).

## Prioridades técnicas

1. Segmentar documentos por artigo/seção, preservando contexto e escopo temporal.
2. Implementar e avaliar recuperação semântica antes de conectar a geração.
3. Integrar LLM com fontes verificáveis e abstenção quando faltar suporte.
4. Criar uma interface simples para demonstrar perguntas, respostas e fontes.

## Riscos observados e tratamento

- Ambiente validado com Python 3.12.14 no Windows e dependências isoladas em venv. Versões registradas em `requirements-lock.txt`.
- Planalto retornou página de bloqueio. A LC 214 foi coletada no portal oficial da Câmara.
- Documentos oficiais podem conter histórico, ressalvas e efeitos futuros. Proveniência e escopo foram registrados; falta validação de vigência por artigo antes de responder sobre regras atuais.
- A LC domina o corpus em tamanho. A próxima etapa deve avaliar segmentação por artigo e recuperação, evitando tratar a quantidade de chunks como indicador de qualidade.
- Ainda não existe RAG funcional. Ingestão bem-sucedida e testes de API não comprovam qualidade de respostas, ausência de alucinação ou desempenho de ML.
