# Estado do projeto

Atualizado em 11/11/2026.

| Componente | Situação |
| --- | --- |
| API | `/health`, `/simulate`, `/search`, `/sources` e OpenAPI disponíveis |
| Simulador | Cálculo determinístico de cenários hipotéticos |
| Ingestão | Três fontes oficiais, com metadados de origem |
| Busca semântica | E5 quantizado na CPU, com 50 trechos indexados |
| Avaliação de recuperação | Comparação inicial com TF-IDF em 16 perguntas |
| Testes | 58 testes passando, além do teste da API com o modelo local |
| Geração por LLM | Pendente |
| Interface | Pendente |

## Limitações conhecidas

O índice cobre duas páginas da Receita e onze artigos da LC 214. Ele não inclui toda a lei nem resolve remissões para outros dispositivos. O recorte está em [retrieval_scope.json](../config/retrieval_scope.json) e pode ser consultado por `/sources`.

A data de coleta não define a vigência de uma regra. As páginas explicativas podem ter orientações históricas, e os dispositivos legais têm efeitos em períodos diferentes.

A busca retorna vizinhos mesmo quando a pergunta não tem resposta nos documentos. Similaridade alta não basta para decidir se há suporte. Esse comportamento será tratado junto com a geração por LLM.

Os resultados de recuperação usam uma amostra pequena e rótulos por âncoras de texto. Ainda falta avaliar a fundamentação de respostas geradas.

Próximas entregas no [roadmap](ROADMAP.md); histórico em [PROGRESS.md](../PROGRESS.md).
