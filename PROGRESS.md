# Progresso

## 11/11/2026 — Interface web

A primeira interface tem assistente, simulador e fontes, com Vue.js e TypeScript. É possível fazer uma pergunta, abrir o trecho citado, comparar duas taxas hipotéticas e conferir os documentos disponíveis. O layout se adapta ao celular e informa espera, falta de suporte e falhas do serviço.

O frontend compilado é servido pela própria FastAPI. As rotas anteriores foram preservadas, com equivalentes sob `/api`. Os cálculos continuam em Python e a chave do LLM permanece no servidor. Campos e respostas são mantidos apenas na memória da página ao trocar de área.

Passaram 100 testes Python, 16 testes TypeScript e 16 verificações de navegador em computador e celular. Uma verificação separada usou o frontend compilado, a API e o LLM reais: houve resposta com fonte para a pergunta sobre a competência da CBS, abertura da citação e comparação hipotética de taxas. Os resultados estão em [reports/frontend-checks.json](reports/frontend-checks.json) e [reports/frontend-live-smoke.json](reports/frontend-live-smoke.json).

A aplicação funciona localmente. Hospedagem pública, avaliação ampliada das respostas e previsão econômica continuam pendentes. Os comandos para executar e testar a interface estão em [docs/FRONTEND.md](docs/FRONTEND.md).

## 11/11/2026 — Primeiras respostas com o LLM real

A integração com a Groq foi verificada com três perguntas públicas. A pergunta sobre a competência da CBS recebeu a resposta “A CBS é um tributo de competência federal”, acompanhada de um trecho correspondente da Receita Federal. As perguntas sobre o clima e sobre o valor exato dos tributos de uma empresa sem informações suficientes foram recusadas.

As respostas estão em [reports/rag-initial-validation.json](reports/rag-initial-validation.json). Uma tentativa interrompida pela cota do serviço foi preservada em [reports/rag-evaluation.json](reports/rag-evaluation.json), como erro operacional.

Os 97 testes offline passaram novamente com a configuração local presente. O [teste HTTP com Uvicorn](reports/rag-api-smoke.json) também confirmou `/ask` com resposta citada usando o serviço real. A avaliação ampliada, incluindo perguntas numéricas e revisão da interpretação jurídica, continua pendente. A próxima entrega é a interface Vue.js com TypeScript.

## 11/11/2026 — Respostas com fontes

O endpoint `/ask` integra a busca existente à Groq. As respostas são formadas por afirmações com evidências literais; título e URL vêm dos metadados do índice. O código confere referências e números, e outra chamada revisa o suporte das afirmações. Se faltar suporte, o rascunho é descartado.

A chave é configurada localmente em `.env`. Falhas de credencial, cota, conexão ou formato retornam erros operacionais, sem se passar por respostas ou abstenções. A simulação e a busca continuam funcionando sem chave.

Os 97 testes offline passaram. O teste HTTP também confirmou as rotas existentes com embeddings locais e o erro esperado em `/ask` sem configuração. A execução está registrada em [reports/tests-rag.json](reports/tests-rag.json).

A avaliação com o provedor real ainda está pendente. Os comandos de configuração e avaliação estão em [docs/RAG.md](docs/RAG.md). A revisão usa o mesmo modelo da geração e pode compartilhar seus erros; a existência de uma citação não comprova que ela sustenta a interpretação.

Depois da avaliação, a próxima entrega será a interface Vue.js com TypeScript. O módulo econômico começará com uma série pública e validação cronológica.

## 11/11/2026 — Busca semântica

A API agora permite buscar trechos dos documentos com `/search` e consultar as fontes disponíveis em `/sources`.

- Embeddings com multilingual-e5-small quantizado em ONNX, executado na CPU.
- Índice com 50 trechos das duas páginas da Receita e de 11 artigos da LC 214.
- Divisão por artigo e seção, mantendo o vínculo com o documento original.
- Validação de versões para evitar buscas com um índice incompatível com o corpus ou o modelo.

A avaliação compara E5 e TF-IDF no mesmo conjunto de perguntas. Nos oito casos de teste, a evidência esperada apareceu em primeiro lugar em cinco consultas com E5 e em quatro com TF-IDF. Ambos a encontraram entre os cinco primeiros resultados em todos os oito casos. A amostra ainda é pequena; os resultados por pergunta estão em [reports/retrieval-evaluation.json](reports/retrieval-evaluation.json).

Os 58 testes passaram. A busca também foi testada pela API com o modelo local. Os scripts de teste e avaliação estão descritos no [README](README.md).

O principal ponto a resolver é a falta de suporte: perguntas fora do escopo também recebem vizinhos com score alto. A próxima etapa é integrar o LLM, conferir as citações e permitir que a aplicação deixe de responder quando os documentos forem insuficientes.

## 11/11/2026 — API e ingestão

Primeira versão com FastAPI, documentação OpenAPI e simulador de cenários hipotéticos em `/simulate`.

O cálculo usa `Decimal`, taxas informadas pelo usuário e arredondamento em centavos. A ingestão coleta três documentos oficiais e guarda texto, URL, data de acesso e hashes. Os metadados da coleta estão em [reports/ingestion.json](reports/ingestion.json).

Essa versão começou com 38 testes para cálculo, validação de entradas e ingestão. O simulador não calcula obrigações tributárias reais.
