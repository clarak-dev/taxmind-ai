# Decisões de arquitetura

## FastAPI, Pydantic e testes

FastAPI fornece um contrato OpenAPI explorável. Pydantic valida tipos, limites e campos extras antes do cálculo. A lógica aritmética fica em `simulator.py`, independente da camada HTTP. Isso permite testar a regra sem servidor e validar o contrato com `TestClient`; o smoke adicional usa HTTP real com Uvicorn.

Entradas inválidas retornam HTTP 422 antes da execução do cálculo. O contrato é verificado em `tests/test_api.py`; a execução com servidor real está registrada em `reports/api-smoke.json`.

Referências: [testes no FastAPI](https://fastapi.tiangolo.com/tutorial/testing/) e [tipos numéricos no Pydantic](https://docs.pydantic.dev/latest/api/standard_library_types/).

## Decimal e hipótese explícita

Dinheiro é calculado em decimal, com arredondamento documentado. Para base de R$ 0,05 e taxa hipotética de 10%, o tributo de R$ 0,005 é arredondado para R$ 0,01. As taxas são entradas obrigatórias; não há alíquota oficial implícita. LLM não participa da conta.

Essa separação mantém o resultado aritmético reproduzível e explicita que uma hipótese de taxa não representa uma regra tributária vigente.

## Ingestão antes do LLM

Sem corpus verificável, uma resposta aparentemente correta não tem proveniência demonstrável. O pipeline começa por três fontes explícitas, sem crawler amplo. HTTPX define timeout, valida status e restringe redirecionamentos aos portais selecionados. BeautifulSoup extrai HTML localmente, inclusive acentuação e marcações de exclusão.

Guardamos HTML por hash, texto limpo e offsets dos chunks. O SHA-256 ajuda a detectar alterações e ligar experimentos ao conteúdo usado. Não comprova vigência nem autenticidade jurídica. URL e órgão registram a origem consultada.

O `document_id` liga cada chunk aos metadados da fonte. Os offsets permitem conferir `chunk.text` no texto limpo. A coleta aborta diante de bloqueio ou fonte incompleta e preserva o corpus anterior. Referência: [timeouts no HTTPX](https://www.python-httpx.org/advanced/timeouts/).

## Por que RAG — decisão para a próxima entrega

O objetivo é recuperar trechos pertinentes de um corpus que pode mudar e fornecer evidências na resposta. Um prompt longo com todos os textos repetiria centenas de milhares de caracteres por pergunta e dificultaria a inspeção do trecho usado. Embeddings multilíngues permitirão testar perguntas em português formuladas com palavras diferentes da fonte.

RAG não elimina alucinações. Recuperação pode selecionar o artigo errado ou uma orientação histórica; geração pode afirmar algo que a fonte não sustenta. Precisamos medir recuperação e suporte da resposta separadamente, conferir números e permitir abstenção. O modelo de embeddings, índice e LLM ainda não foram escolhidos ou executados.

O estágio atual cobre a API e a ingestão rastreável. A escolha do modelo de embeddings e do índice dependerá de avaliação de recuperação e dos recursos necessários para execução local.

## Custos, privacidade e operação

A primeira entrega executa localmente e não envia perguntas a um provedor de IA. Dependências e documentos são baixados de fontes públicas. A próxima entrega deve comparar custo, memória, latência e capacidade em português antes de escolher backend. Não adicionar infraestrutura cloud apenas para ampliar a lista de tecnologias.

Antes de produção seriam necessários revisão de vigência, controle de atualização e índices, avaliação ampliada, observabilidade, limites de requisições, proteção contra instruções maliciosas nos documentos, política de dados e revisão humana de usos tributários. São pendências, não recursos implementados.
