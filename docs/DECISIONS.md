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

## Recuperação como etapa do RAG

O objetivo é recuperar trechos pertinentes de um corpus que pode mudar e fornecer evidências na resposta. Um prompt longo com todos os textos repetiria centenas de milhares de caracteres por pergunta e dificultaria a inspeção do trecho usado. Embeddings multilíngues são usados para comparar perguntas em português com o significado dos documentos.

RAG não elimina alucinações. Recuperação pode selecionar o artigo errado ou uma orientação histórica; geração pode afirmar algo que a fonte não sustenta. Recuperação e suporte da resposta precisam de avaliações separadas. A geração em `/ask` usa os trechos recuperados com validação de citações e uma segunda chamada de revisão. Três casos foram verificados com o provedor real; a avaliação ampliada continua pendente.

## E5 quantizado em ONNX

O ambiente alvo tem memória limitada. A versão ONNX quantizada do multilingual-e5-small reduz o tamanho do arquivo de pesos de cerca de 470 MB para 118 MB, segundo os metadados do repositório na revisão usada. ONNX Runtime e tokenizers permitem inferência local sem instalar PyTorch. Isso não implica que o uso total de RAM seja igual ao tamanho do arquivo.

Os vetores têm 384 dimensões. São usados os prefixos específicos para pergunta/documento, pooling pela máscara de atenção e normalização L2, conforme o [model card](https://huggingface.co/intfloat/multilingual-e5-small). A revisão e os hashes impedem mudanças silenciosas no modelo baixado. Nenhum texto é enviado a um serviço de inferência externo.

O tokenizer verifica o limite de 512 tokens; o código rejeita entradas acima do limite. Não há truncamento silencioso que poderia remover a exceção ou o número procurado.

## Índice exato e recorte explícito

O recorte inicial contém duas páginas explicativas e onze artigos da LC 214, produzindo 50 chunks por seção/artigo. A coleta integral continua preservada. Remissões a artigos fora desse recorte não são resolvidas automaticamente; o resultado da busca inclui a limitação temporal e a referência original.

Para 50 vetores, NumPy permite busca exata simples e inspecionável. Produto interno de vetores unitários equivale a cosseno; não há perda por aproximação. FAISS ou um banco vetorial podem ser comparados quando volume, filtros ou concorrência justificarem. Uma nova geração do índice só é ativada após completar os artefatos, sem apagar a anterior.

## Baseline e limites da avaliação

O baseline lexical calcula TF-IDF com log-TF e cosseno, ajustando o vocabulário somente nos documentos. Usa o mesmo recorte e top-k do E5. O conjunto de perguntas foi separado em desenvolvimento, teste e diagnósticos antes da primeira avaliação, sem calibrar limiar pelo teste.

Nos oito casos de teste, E5 acertou a evidência esperada em primeiro lugar em cinco; TF-IDF, em quatro. Ambos acertaram entre os cinco primeiros em todos os oito. Três falhas de primeiro resultado do E5 ocorreram em incidência geral, vigência integral do modelo e extinção de tributos. A divisão atual gera alguns trechos curtos, que podem perder contexto; na próxima revisão, os casos já examinados servirão como regressão, e novas perguntas permitirão avaliar as mudanças.

Perguntas sem suporte também receberam scores altos. Similaridade mede proximidade do embedding, não validade jurídica nem possibilidade de responder. `/search` retorna candidatos sem classificar o escopo; `/ask` decide se responde e revisa as evidências em outra chamada. Esses mecanismos precisam de avaliação própria com o modelo real.

## Geração estruturada e fontes locais

O cliente da Groq usa HTTPX e configuração no servidor. O modelo inicial, `qwen/qwen3.8-27b`, oferece saída estruturada e cota gratuita, mas é preview. O modelo pode ser substituído por outro compatível, mediante nova avaliação. Referência: [saídas estruturadas na Groq](https://console.groq.com/docs/structured-outputs).

O LLM produz afirmações com citações literais e identificadores do índice. O servidor confere a existência dos trechos, os números e os percentuais, e monta títulos e URLs a partir dos metadados. Outra chamada revisa suporte e adequação à pergunta. Se qualquer etapa reprovar a evidência, o rascunho é descartado. A validação de referências é determinística; a revisão semântica é probabilística e usa o mesmo modelo, portanto pode compartilhar erros da geração.

## Interface e modelo econômico

A interface usa Vue.js com TypeScript para apresentar respostas e fontes da FastAPI. Vite fornece recarga durante o desenvolvimento e gera arquivos estáticos para distribuição. As três áreas usam navegação por fragmento e `KeepAlive`, mantendo campos e respostas na memória da página, sem persistir conversas. Não foi necessário adicionar um gerenciador global de estado ou uma biblioteca de rotas.

Durante o desenvolvimento, o proxy do Vite encaminha `/api` à FastAPI. No build local, a FastAPI serve `frontend/dist` e as rotas `/api` no mesmo endereço; as rotas anteriores continuam disponíveis. Isso evita configurar CORS amplo e mantém a chave do LLM no servidor. A montagem estática é opcional, para preservar o uso da API sem Node ou build da interface.

A resposta gerada é exibida como texto, sem `v-html`. As referências abrem trechos e links provenientes da API. O simulador normaliza a entrada decimal e envia strings; cálculos e arredondamento continuam em Python. Os testes de navegador usam fixtures de contrato, e o smoke real é separado para não consumir cota em cada execução.

A primeira demonstração não exige conta de usuário ou histórico privado. O módulo econômico começará com um único indicador público e validação cronológica, mantendo previsão estatística e simulação hipotética como operações distintas.

## Custos, privacidade e operação

A aplicação executa localmente. Na escolha do backend de geração, os principais critérios serão memória, latência, custo e qualidade em português.

Antes de produção seriam necessários revisão de vigência, controle de atualização e índices, avaliação ampliada, observabilidade, limites de requisições, proteção contra instruções maliciosas nos documentos, política de dados e revisão humana de usos tributários. São pendências, não recursos implementados.
