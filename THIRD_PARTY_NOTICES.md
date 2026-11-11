# Modelos e fontes de terceiros

## Embeddings

- Modelo original: [intfloat/multilingual-e5-small](https://huggingface.co/intfloat/multilingual-e5-small).
- Licença declarada pelo repositório do modelo: MIT.
- Revisão utilizada: `614241f622f53c4eeff9890bdc4f31cfecc418b3`.
- Artefato: `onnx/model_qint8_avx512_vnni.onnx`, fornecido pelo próprio repositório do modelo. A inferência foi validada com ONNX Runtime CPU neste projeto; desempenho e compatibilidade devem ser verificados em outros ambientes.
- Referência: Liang Wang et al., [Multilingual E5 Text Embeddings: A Technical Report](https://arxiv.org/abs/2402.05672), 2024.

Os pesos e o tokenizer não são redistribuídos neste repositório. O comando de preparação baixa arquivos da revisão declarada e verifica tamanho e SHA-256. O download não usa conta ou token, e a inferência não executa código Python remoto.

## Documentos

As fontes são identificadas por órgão e URL em [data/sources.json](data/sources.json). Receita Federal, CGIBS e Câmara dos Deputados são as origens dos documentos; não há vínculo institucional com este projeto. Snapshots integrais e corpus gerado não são versionados. Trechos apresentados pela API mantêm a referência à fonte e sua data de acesso.
