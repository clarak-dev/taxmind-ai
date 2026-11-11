# TaxMind AI

Projeto educacional de engenharia de IA para consultar documentos públicos da Reforma Tributária do Consumo e comparar cenários hipotéticos.

**Em desenvolvimento:** API, simulador determinístico e ingestão documental implementados. Embeddings, recuperação semântica, respostas por LLM e interface estão no [roadmap](docs/ROADMAP.md).

## Executar localmente

Python 3.11+; validado nesta entrega com Python 3.12.14 no Windows. No PowerShell, a partir desta pasta:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe -m pytest -q --junitxml=reports/pytest.xml
.\.venv\Scripts\python.exe -m app.ingestion
.\.venv\Scripts\python.exe scripts/smoke_api.py
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Abra http://127.0.0.1:8000/docs. O comando de ingestão requer internet; os testes automatizados usam fixtures técnicas sintéticas e não dependem dos portais.

É necessário ter um interpretador Python instalado. Os comandos usam diretamente o executável da venv; não é necessário ativá-la ou alterar a política de execução do PowerShell.

`requirements.txt` descreve dependências diretas; `requirements-dev.txt` inclui pytest; `requirements-lock.txt` registra as versões exatas efetivamente verificadas, incluindo dependências transitivas e de teste. Não são necessários conta, chave ou serviço pago nesta entrega.

## API e simulação

| Rota | Comportamento |
| --- | --- |
| `GET /health` | Estado da API e indicação explícita de RAG ainda não implementado |
| `POST /simulate` | Comparação de duas taxas hipotéticas sobre a mesma base sem tributo |
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

Limitações: fonte oficial não garante atualidade de todas as orientações. A data de acesso não é a vigência da regra. O comunicado é histórico e pode ter atos posteriores. A LC tem efeitos escalonados; nesta etapa não há interpretação automatizada por dispositivo. Chunks usam caracteres, ainda sem hierarquia de artigo ou tratamento estruturado de tabelas. Citações numéricas e respostas sobre vigência dependerão dessa revisão na próxima entrega. A URL do Planalto consultada bloqueou acesso; foi usado o texto atualizado da Câmara, sem tentar contornar o bloqueio.

## Evidências e próximos passos

Consulte o [progresso](PROGRESS.md), a [auditoria técnica](docs/AUDIT.md), o [roadmap](docs/ROADMAP.md) e as [decisões de arquitetura](docs/DECISIONS.md). Relatórios registram execuções observadas; ainda não há métricas de qualidade de recuperação ou geração.

Próximo incremento: segmentação por seção/artigo, embeddings multilíngues locais, recuperação top-k com fontes e avaliação do retrieval. Em seguida, backend de LLM configurável, `/ask`, validação das citações e abstenção quando não houver suporte. A interface e a hospedagem de uma demonstração continuam pendentes.

Use somente documentos públicos ou dados sintéticos. Não incluir arquivos empresariais, informações de clientes ou credenciais. Nenhum dado profissional privado é necessário para executar este projeto.
