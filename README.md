# Crédito no Brasil — o ciclo de 2025-26

Apresentação (deck HTML autocontido, SVG inline, sem dependências externas de JS)
sobre o ciclo de crédito brasileiro, construída sobre os dados primários do
[dashboard-bcb](https://github.com/rlavourinha/dashboard-bcb): BCB/SGS, IF.data,
SCR.data e BIS/OCDE/Banco Mundial.

**Deck:** https://rlavourinha.github.io/credito-brasil

## Pipeline

```
dados_deck.py    # extrai as séries do dashboard-bcb (SGS ao vivo + CSVs locais) -> _dados.json
build_deck.py    # _dados.json + _template.html -> index.html (22 slides)
```

Para atualizar após uma divulgação nova do BCB: rode o refresh do dashboard-bcb,
depois `python dados_deck.py && python build_deck.py` e commite.

## Convenções

- Gráficos em SVG inline gerados em Python; template montado com `.replace(sentinela)`.
- Série sempre completa (sem seletor de janela); número real + MM12 quando volátil.
- Sem barras empilhadas no tempo; linhas independentes ou barras lado a lado.
- Caixa verde (`.sl-output`) = a leitura de uma frase de cada slide.
- Chip de versão no cabeçalho (v · data · corte dos dados · nº de slides).
