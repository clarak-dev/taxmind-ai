# Respostas com documentos

## Configuração

O modelo inicial é `qwen/qwen3.8-27b`, na Groq. A escolha considera a cota gratuita e o suporte a JSON estruturado estrito. O modelo está listado como preview e pode mudar ou ser descontinuado. Disponibilidade e limites dependem da conta; confira o [catálogo](https://console.groq.com/docs/models) e os [limites](https://console.groq.com/docs/rate-limits).

`python -m scripts.configure_llm` solicita a chave em um terminal interativo, sem exibi-la ou gravá-la no histórico do shell. O comando cria `.env` e preserva arquivos existentes. `.env.example` também pode ser copiado e preenchido no editor.

| Variável | Valor |
| --- | --- |
| `TAXMIND_LLM_PROVIDER` | `groq`, único provedor implementado nesta etapa |
| `TAXMIND_LLM_MODEL` | `qwen/qwen3.8-27b`; aceita outro modelo compatível com saída estruturada estrita |
| `GROQ_API_KEY` | Chave configurada somente no servidor |

Variáveis do processo têm precedência sobre `.env`. Os valores no arquivo são literais, sem interpolação ou comentários na mesma linha. O cliente usa HTTPX, já presente nas dependências.

## Geração e revisão

`/ask` aceita `question` de 3 a 500 caracteres e `top_k` de 1 a 5. O fluxo usa o índice existente, sem limiar de similaridade tratado como probabilidade de acerto.

1. Recupera os trechos e solicita um rascunho com até quatro afirmações e evidências literais.
2. Confere se cada identificador pertence à busca, se a citação está no trecho e se os números aparecem nas evidências, preservando percentuais.
3. Uma segunda chamada ao mesmo LLM revisa o suporte de cada afirmação e a adequação da resposta à pergunta.
4. Se a revisão aprovar todas as afirmações, o servidor monta a resposta e suas fontes. Caso contrário, descarta o rascunho e informa falta de suporte.

As instruções restringem o uso de conhecimento externo e tratam pergunta e documentos como dados, sem autoridade para mudar as regras. O LLM não executa ferramentas, consulta URLs ou participa dos cálculos do simulador. URLs e títulos da resposta vêm dos metadados do índice.

Uma resposta aceita usa duas chamadas ao provedor; a abstenção durante a geração usa uma. Não há repetição automática nem troca para outro serviço quando a cota termina.

## Contrato

O resultado contém `status`, `answer`, `claims`, `citations`, `reason`, `provider`, `model`, `prompt_version`, `index_generation` e `latency_ms`. Cada afirmação identifica suas citações. Cada citação inclui título, URL, seção, trecho, data de acesso, ressalvas temporais e offsets no texto limpo do documento.

| Situação | Resposta |
| --- | --- |
| Afirmações aceitas | HTTP 200, `status=answered`, resposta e fontes |
| Evidência ausente, inválida ou reprovada | HTTP 200, `status=abstained`, mensagem fixa, sem rascunho ou fontes inventadas |
| Configuração ausente ou credencial recusada | HTTP 503 |
| Limite do provedor | HTTP 429 |
| Timeout | HTTP 504 |
| Resposta do provedor incompleta ou inválida | HTTP 502 |

`/health` informa `rag_status=configured` quando encontra configuração local válida. Isso não comprova autenticação, cota, acesso ao modelo ou disponibilidade do índice. Busca e simulação continuam funcionando sem chave.

## Avaliação

Os testes offline usam respostas controladas para verificar contratos e falhas. Não medem a qualidade de um LLM real. Com a chave configurada e o índice pronto:

```powershell
.\.venv\Scripts\python.exe -m scripts.evaluate_rag --case dev-cbs-competencia --case ood-clima --case insufficient-personal
.\.venv\Scripts\python.exe scripts/smoke_api.py --rag
```

Sem `--case`, o avaliador usa as 16 perguntas de `evaluation/questions.json`. Por padrão, aguarda 65 segundos entre perguntas para reduzir disputas pela cota; isso não garante que todos os limites da conta sejam respeitados. Uma falha do provedor interrompe a execução e fica registrada como erro operacional, sem contar como abstenção correta.

O relatório `reports/rag-evaluation.json` guarda decisões, respostas, fontes, versões e verificações parciais das âncoras de referência. Relatórios existentes são preservados: renomeie o anterior antes de repetir. O smoke salva `reports/rag-api-smoke.json` após confirmar uma resposta citada por HTTP real.

A correspondência de âncoras é uma verificação parcial, sem avaliação semântica independente. A revisão humana de suporte e atualidade fica pendente em cada caso. Não há resultado com provedor real registrado nesta etapa.

## Limites

A validação literal identifica referências inexistentes; não demonstra que uma frase interpreta corretamente a fonte. Geração e revisão usam o mesmo modelo em chamadas separadas e podem compartilhar erros. Não há garantia de resistência a instruções maliciosas, atualização jurídica ou cobertura integral da lei. A abstenção também pode recusar perguntas respondíveis.

Pergunta e trechos são enviados ao provedor externo. A aplicação não mantém histórico de conversas; a avaliação salva as perguntas públicas e suas respostas. Use somente perguntas sem dados pessoais ou empresariais.

A primeira versão é executada localmente. Uma demonstração pública ainda exige limites de requisições, controle de concorrência e validação das cotas e da memória do servidor.
