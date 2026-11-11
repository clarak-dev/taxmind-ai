# Auditoria técnica — 11/11/2026

## Escopo

Revisão do TaxMind AI: contrato HTTP, simulador hipotético, documentos públicos e recuperação semântica. O histórico da primeira versão permanece em `PROGRESS.md`.

## Estado verificado

| Item | Estado | Evidência |
| --- | --- | --- |
| API e OpenAPI | IMPLEMENTADO | `/health`, `/simulate`, `/search`, `/sources`, `/docs` e `/openapi.json`; HTTP real |
| Simulador | IMPLEMENTADO no escopo hipotético | Decimal, validação de limites, arredondamento e aviso de limitações |
| Ingestão e chunks | IMPLEMENTADO | Três fontes oficiais, metadados, hashes e offsets verificados |
| Testes | IMPLEMENTADO | 58 casos aprovados em `reports/tests-retrieval.json`; sem download do modelo |
| Embeddings e índice | IMPLEMENTADO no recorte inicial | E5 quantizado CPU, 50 chunks, três fontes, modelo e índice com hashes |
| LLM e `/ask` | PENDENTE | Sem geração de respostas |
| Avaliação de recuperação | IMPLEMENTADO como avaliação inicial | 16 perguntas, baseline TF-IDF e resultados por caso |
| Avaliação de geração | PENDENTE | Nenhuma resposta por LLM avaliada |
| Interface | PENDENTE | API disponível localmente, sem interface de perguntas |

Histórico de execução em [PROGRESS.md](../PROGRESS.md); entregas previstas no [roadmap](ROADMAP.md).

## Prioridades técnicas

1. Escolher um backend de LLM compatível com os recursos disponíveis.
2. Integrar geração com fontes verificáveis e abstenção quando faltar suporte.
3. Avaliar afirmações, números, referências e perguntas sem resposta nos documentos.
4. Criar uma interface simples para demonstrar perguntas, respostas e fontes.

## Riscos observados e tratamento

- Ambiente validado com Python 3.12.14 no Windows e dependências isoladas em venv. Versões registradas em `requirements-lock.txt`.
- Planalto retornou página de bloqueio. A LC 214 foi coletada no portal oficial da Câmara.
- Documentos oficiais podem conter histórico, ressalvas e efeitos futuros. Proveniência e escopo foram registrados; falta validação de vigência por artigo antes de responder sobre regras atuais.
- A LC domina o corpus coletado. O índice inicial usa onze artigos, sem cobertura integral da lei ou de suas remissões. Esse recorte é exposto em `/sources`.
- Perguntas sem evidência podem receber scores altos. Nenhum limiar de confiança ou recusa foi implementado.
- Ainda não existe RAG completo com geração. Testes de API e avaliação de recuperação não comprovam qualidade de respostas geradas ou ausência de alucinação.
