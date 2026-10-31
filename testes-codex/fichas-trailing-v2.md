# Três estratégias do Notion com stop móvel — v2

Mantém sinais, períodos, fontes e custos de `fichas-v1.md`. Thiago escolheu manter
stop inicial de 300 pontos, ativar o trailing depois de 300 pontos favoráveis e
acompanhar o melhor preço a uma distância de 150 pontos. Não há alvo fixo de 600.
Saídas por sinal contrário e fim do pregão continuam como na v1.

## Execução e incerteza

- Um contrato; preço preenchido com 5 pontos de derrapagem adversa na entrada e nas
  saídas; comissão R$ 0,25 por lado. O stop inicial parte do preço preenchido.
- Para compra, stop inicial = entrada − 300. A partir de entrada + 300, stop é
  o maior preço atingido menos 150, sem recuar. Para venda, regras espelhadas.
  Salto além do stop é executado na abertura, com derrapagem.
- A sequência de máxima e mínima dentro da barra é desconhecida. Se o stop vigente
  e um movimento favorável forem possíveis na mesma barra, supõe-se o toque no stop
  primeiro. Se o stop antigo não foi tocado, mas ativação e toque no trailing forem
  possíveis na mesma barra, usa-se uma sequência adversa plausível, identificada
  como ambígua. Isto é uma suposição, não reconstrução de ticks nem garantia de
  limite das perdas reais. Sem toque possível, o stop atualizado vale na próxima barra.
- Os períodos e fontes são os da v1: desenvolvimento 2023–2025 em M5/M15; janeiro
  a setembro de 2026 em M5/M15; e 11/02–30/09/2026 em M1/M5/M15 para comparação.
  Outubro de 2026 fica de fora. O período de 2026 já foi explorado e não é validação
  independente. O fechamento do último candle é usado como hipótese de saída de tempo.

Os resultados não devem ser comparados como se houvesse uma sequência exata de
negócios. O dashboard precisa mostrar a quantidade de barras ambíguas por combinação.
