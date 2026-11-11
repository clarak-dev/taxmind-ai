# Progresso

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
