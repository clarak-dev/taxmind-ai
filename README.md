# TaxMind AI

Projeto educacional de engenharia de IA para consultar documentos públicos da Reforma Tributária do Consumo e comparar cenários hipotéticos.

**Em desenvolvimento:** API, simulador determinístico, ingestão documental e recuperação semântica implementados. A busca retorna trechos oficiais com fontes; geração por LLM e interface continuam no [roadmap](docs/ROADMAP.md).

## Executar localmente

Python 3.11+; validado nesta entrega com Python 3.12.14 no Windows. No PowerShell, a partir desta pasta:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe -m pytest -q --junitxml=reports/pytest.xml
.\.venv\Scripts\python.exe -m app.ingestion
.\.venv\Scripts\python.exe -m app.embeddings download
.\.venv\Scripts\python.exe -m app.retrieval build
.\.venv\Scripts\python.exe -m scripts.evaluate_retrieval
.\.venv\Scripts\python.exe scripts/smoke_api.py
.\.venv\Scripts\python.exe scripts/smoke_api.py --retrieval
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Abra http://127.0.0.1:8000/docs. Ingestão e primeiro download do modelo requerem internet. Após preparar os arquivos locais, a indexação e a busca executam offline. Os testes automatizados usam fixtures técnicas e não exigem download do modelo ou acesso aos portais.

É necessário ter um interpretador Python instalado. Os comandos usam diretamente o executável da venv; não é necessário ativá-la ou alterar a política de execução do PowerShell.

`requirements.txt` descreve a API e o processamento básico; `requirements-retrieval.txt` adiciona ONNX Runtime e tokenizers; `requirements-dev.txt` inclui pytest. O comando acima instala o conjunto completo por `requirements-lock.txt`, com as versões efetivamente verificadas. Não são necessários conta, chave ou serviço pago.

## API e simulação

| Rota | Comportamento |
| --- | --- |
| `GET /health` | Estado da API e indicação explícita de RAG ainda não implementado |
| `POST /simulate` | Comparação de duas taxas hipotéticas sobre a mesma base sem tributo |
| `POST /search` | Recuperação semântica top-k com trecho, seção, URL e metadados da fonte |
| `GET /sources` | Fontes cadastradas, coletadas e efetivamente indexadas, com recorte explícito |
| `GET /docs` e `/openapi.json` | Contrato e exploração da API |

```powershell
$scenario = @{
  base_amount = "100.00"
  current_rate_percent = "10"
  proposed_rate_percent = "15"
} | ConvertTo-Json
Invoke-RestMethod -Uri http://127.0.0.1:8000/simulate -Method Post -ContentType 'application/json' -Body $scenario
```

Nesse exemplo hipotético, os tributos são R$ 10,00 e R$ 15,00, e a diferença é R$ 5,00. Fórmula: `tributo = base × taxa / 100`. Cada tributo é arredondado para centavos com `ROUND_HALF_UP`; o total soma base e tributo já arredondado. Taxas são percentuais, não frações. Valores monetários usam `Decimal` e são serializados como strings no JSON.

Base entre zero e R$ 1 trilhão, até duas casas decimais; taxas de 0% a 100%, até quatro casas. O limite da base é técnico. Campos ausentes, extras, valores negativos, não finitos ou acima desses limites retornam HTTP 422.

O simulador não contém alíquotas oficiais nem calcula obrigações reais. Não modela créditos, exceções, regimes, incidência por produto ou transição. Seu propósito é manter a aritmética separada da futura geração textual.

## Ingestão e rastreabilidade

O catálogo [data/sources.json](data/sources.json) seleciona três fontes:

- [Receita Federal: Entenda a Reforma Tributária do Consumo](https://www.gov.br/receitafederal/pt-br/acesso-a-informacao/acoes-e-programas/reforma-tributaria-do-consumo/entenda).
- [Receita Federal e CGIBS: comunicado sobre 2026](https://www.gov.br/receitafederal/pt-br/assuntos/noticias/2025/dezembro/comunicado-conjunto).
- [Câmara: texto atualizado da LC 214/2025](https://www2.camara.leg.br/legin/fed/leicom/2025/leicomplementar-214-16-janeiro-2025-796905-normaatualizada-pl.html).

Fluxo implementado: catálogo validado → download HTML com timeout → extração do conteúdo principal → remoção de scripts, navegação e texto marcado como excluído → texto limpo → chunks com sobreposição → corpus JSON e relatório de proveniência.

Cada documento guarda título, órgão, URL original/final, horário UTC, escopo temporal, ressalvas de vigência, SHA-256 do HTML e do texto e cabeçalhos de versão quando disponíveis. O SHA-256 identifica o conteúdo coletado; não autentica juridicamente o documento. Cada chunk guarda o documento de origem, identificador estável e offsets no texto limpo, permitindo recuperar título e URL por `document_id`.

Resultados locais:

- `data/raw/<fonte>/<sha256>.html`: snapshots originais, preservados por hash.
- `data/processed/corpus.json`: textos e trechos preparados, substituído somente após todas as fontes passarem pelas validações.
- [reports/ingestion.json](reports/ingestion.json): contagens, metadados e hashes da coleta real; sem copiar o texto integral.

Os HTMLs e o corpus ficam fora do Git. Uma falha interrompe o comando com código 1 e preserva o corpus anterior; snapshots já coletados permanecem. Somente URLs HTTPS dos portais selecionados são aceitas, inclusive em redirecionamentos. A ingestão é um comando local, sem endpoint de upload de URLs.

Limitações: fonte oficial não garante atualidade de todas as orientações. A data de acesso não é a vigência da regra. O comunicado é histórico e pode ter atos posteriores. A LC tem efeitos escalonados; nesta etapa não há interpretação automatizada por dispositivo ou tratamento estruturado de tabelas. A URL do Planalto consultada bloqueou acesso; foi usado o texto atualizado da Câmara.

## Busca semântica

O [recorte de indexação](config/retrieval_scope.json) usa as duas páginas explicativas e os artigos 1–4, 343–348 e 544 da LC 214. O corpus integral coletado é preservado. Esse recorte não cobre toda a lei, suas remissões ou exceções.

O índice atual tem **50 trechos e 384 dimensões**. A segmentação respeita limites de artigos e seções; artigos longos são divididos com sobreposição, mantendo seção e offsets. O limite de 512 tokens é verificado antes da inferência; textos maiores são rejeitados em vez de truncados silenciosamente.

```powershell
$query = @{ question = "O que é a CBS e de quem é sua competência?"; top_k = 5 } | ConvertTo-Json
Invoke-RestMethod -Uri http://127.0.0.1:8000/search -Method Post -ContentType 'application/json; charset=utf-8' -Body ([System.Text.Encoding]::UTF8.GetBytes($query))
```

Modelo: [intfloat/multilingual-e5-small](https://huggingface.co/intfloat/multilingual-e5-small), versão ONNX quantizada executada na CPU. Revisão, tamanhos e hashes dos arquivos estão em [config/embedding_model.json](config/embedding_model.json). São baixados aproximadamente 136 MB para `data/models/`, fora do Git. Os prefixos `query:`/`passage:`, a média por máscara de atenção e a normalização L2 seguem o model card. Referências e licença declarada em [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

A busca usa produto interno de vetores normalizados em NumPy, equivalente ao cosseno. O volume inicial não exige banco vetorial. O índice guarda hashes do corpus, recorte, modelo e artefatos; alterações incompatíveis invalidam a busca. Novas gerações são preservadas em `data/index/`, e o ponteiro ativo só muda após a construção terminar. Reinicie a API depois de reconstruir o índice.

`/search` aceita pergunta de 3 a 500 caracteres e `top_k` de 1 a 10. Sem modelo ou índice válido, retorna HTTP 503. `/sources` pode listar o catálogo mesmo sem baixar o modelo. A inicialização da API e `/simulate` não carregam a sessão ONNX.

**Similaridade não é confiança.** A busca sempre retorna vizinhos quando existe um índice, inclusive para perguntas fora do escopo. Não há resposta gerada, classificador de escopo ou recusa automática nesta versão.

## Avaliação de recuperação

O conjunto inicial tem 16 perguntas: 3 de desenvolvimento, 8 de teste com âncoras de evidência e 5 diagnósticos sem suporte esperado. Nenhum limiar foi calibrado. As métricas verificam a recuperação de âncoras rotuladas, não correção tributária ou suporte de respostas geradas.

| Método | Hit@1 no teste | Hit@5 no teste | MRR@5 no teste |
| --- | --- | --- | --- |
| E5 quantizado | 5/8 (62,5%) | 8/8 (100%) | 0,78125 |
| TF-IDF lexical | 4/8 (50%) | 8/8 (100%) | 0,69792 |

Ambos recuperaram a evidência esperada entre os cinco primeiros nesta pequena amostra. Os resultados não demonstram superioridade geral dos embeddings. Perguntas com números de artigos favorecem correspondência lexical; rótulos por âncoras também podem deixar de reconhecer trechos úteis não anotados.

Relatórios: [avaliação por pergunta](reports/retrieval-evaluation.json), [índice](reports/index.json), [58 testes offline](reports/tests-retrieval.json) e [HTTP real com modelo](reports/retrieval-api-smoke.json). O relatório de avaliação guarda identificadores, offsets e hashes dos trechos; os textos completos continuam no corpus local. Latência medida separa carga do modelo da execução de consultas.

## Evidências e próximos passos

Consulte o [progresso](PROGRESS.md), a [auditoria técnica](docs/AUDIT.md), o [roadmap](docs/ROADMAP.md) e as [decisões de arquitetura](docs/DECISIONS.md). Relatórios registram execuções observadas; a avaliação de geração ainda está pendente.

Próximo incremento: backend de LLM configurável, `/ask`, validação das citações e abstenção quando não houver suporte. A interface e a hospedagem de uma demonstração continuam pendentes.

Use somente documentos públicos ou dados sintéticos. Não incluir arquivos empresariais, informações de clientes ou credenciais. Nenhum dado profissional privado é necessário para executar este projeto.
