# Interface web

O frontend usa Vue 3, TypeScript e Vite. A interface tem três áreas: perguntas com fontes, comparação de cenários hipotéticos e consulta aos documentos disponíveis. Não há painel econômico com valores de exemplo; esse módulo depende de uma série pública e de um modelo avaliado.

Capturas da versão verificada: [computador](images/frontend-desktop.png) e [celular](images/frontend-mobile.png).

## Executar a aplicação

Pré-requisitos: API, corpus, índice e chave do LLM preparados conforme o [README](../README.md); Node.js 22.12+ e npm. O desenvolvimento foi feito com Node 24 no Windows.

Na raiz do projeto, no PowerShell:

```powershell
Set-Location frontend
npm.cmd ci
npm.cmd run build
Set-Location ..
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Abra http://127.0.0.1:8000. A FastAPI serve apenas o conteúdo compilado de `frontend/dist`, depois das rotas da API. O diretório do projeto, a chave e os documentos locais não são publicados como arquivos estáticos. Faça o build antes de iniciar a API; se ela já estiver em execução sem a interface, reinicie-a.

`npm.cmd` evita o bloqueio de `npm.ps1` no PowerShell sem mudar a política de execução do computador. Em Linux ou macOS, use `npm` e o executável Python da sua venv.

## Durante o desenvolvimento

Mantenha a API na porta 8000. Em outro terminal, na pasta `frontend`:

```powershell
npm.cmd run dev
```

Abra http://127.0.0.1:5173. O Vite encaminha as chamadas de `/api` para a FastAPI. Isso permite atualizar a interface durante o desenvolvimento sem abrir CORS para qualquer origem.

## Integração

| Área | Operação |
| --- | --- |
| Estado da conexão | `GET /api/health` |
| Assistente | `POST /api/ask` |
| Simulador | `POST /api/simulate` |
| Documentos e cobertura | `GET /api/sources` |

As rotas anteriores, como `/ask` e `/simulate`, continuam disponíveis. As entradas e saídas são tipadas em `frontend/src/api.ts`. A chave da Groq é lida apenas pela FastAPI. Nenhuma variável `VITE_` deve conter segredo, pois essas variáveis entram no código do navegador.

Na execução com frontend e API juntos, o endereço relativo `/api` é suficiente. `VITE_API_BASE_URL` permite configurar um endereço público em outro ambiente. Uma hospedagem separada exige HTTPS e autorização explícita da origem no backend; essa configuração ainda não foi implementada.

## Comportamento da interface

O assistente distingue resposta citada, abstenção e erro operacional. As afirmações são exibidas como texto; HTML retornado pelo modelo não é executado. Os números das referências abrem o trecho correspondente, com título, URL e data de acesso. A lista de documentos mostra a cobertura parcial da lei.

O simulador aceita vírgula ou ponto decimal, valida limites e envia os valores como strings. A aritmética e o arredondamento continuam na API com `Decimal`. Se os parâmetros forem alterados depois da comparação, a interface avisa que os resultados precisam ser atualizados. As taxas preenchidas inicialmente são exemplos hipotéticos.

A navegação usa três endereços com fragmento, como `/#fontes`. `KeepAlive` preserva campos e respostas ao trocar de área, somente na memória da página. Recarregar a página encerra esse estado. Não há cadastro, histórico persistente ou cookies de análise.

O layout se adapta ao celular, com labels, foco de teclado, atalho para o conteúdo, estados de espera e mensagens de erro. A tipografia é hospedada junto da aplicação, sem requisição ao Google Fonts. Licenças ficam em `frontend/public/licenses`.

## Verificação

Na pasta `frontend`:

```powershell
npm.cmd test
npm.cmd run test:e2e
```

Os testes unitários verificam entradas decimais, links e o cliente HTTP. Os testes de navegador usam fixtures explícitas para conferir respostas, abstenções, limite de uso, fontes, simulação, navegação e comportamento em duas larguras. Esses testes não avaliam a qualidade de um LLM real.

No Windows, os testes de navegador usam o Edge instalado. `PLAYWRIGHT_CHANNEL` permite escolher outro navegador compatível. Em Linux, instale o Chromium do Playwright com `npx playwright install chromium` antes de executar os testes.

Com o build pronto e a aplicação na porta 8000, a verificação real é separada:

```powershell
npm.cmd run smoke:live
```

Esse comando faz uma pergunta pública ao LLM real, confere as citações no corpus coletado e testa um cálculo hipotético e a lista de fontes. Consome a cota do provedor e salva `reports/frontend-live-smoke.json`. As capturas para revisão ficam em `.local-notes/frontend-preview`, fora do Git. Uma falha de cota não deve ser contada como abstenção correta.

## Hospedagem

A interface está preparada para execução local e build estático. Uma demonstração hospedada depende da publicação da API, do índice e da configuração do LLM no servidor. Não há demonstração pública hospedada nesta etapa.
