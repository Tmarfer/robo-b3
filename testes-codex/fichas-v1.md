# Três fichas do Notion — pesquisa exploratória

Thiago autorizou em 31/10/2026 testar três ideias e comparar tempos gráficos até
setembro de 2026, excluindo outubro. A escolha de parâmetros ou tempos usando 2026
torna esse período exploratório: ele não valida independentemente a escolha.

## Fichas e sinais (apenas barras fechadas)

1. [Médias 5/20](https://app.notion.com/410535f5974b4c26a0e551e73b5cdb92):
   cruzamento de médias simples de fechamento de 5 e 20 barras, para compra/venda.
2. [MACD 12/26/9](https://app.notion.com/ddc7919616c8497e89b2c970e988ad48):
   cruzamento da diferença entre médias exponenciais 12 e 26 com sua média
   exponencial de 9, para compra/venda. Inicialização exponencial pandas adjust=False.
3. [Estocástico lento 14/3/3](https://app.notion.com/fc27da1244d34b398863ec1da901850c):
   %K lento cruza %D para cima com ambos abaixo de 20: compra; cruzamento para baixo
   com ambos acima de 80: venda. %K bruto = 100 × (fechamento − mínima de 14) /
   (máxima de 14 − mínima de 14); média de 3 e outra média de 3. Faixa zero = sem sinal.

## Execução e limites comuns

- Um contrato WIN, posição comprada ou vendida; sinal de fechamento executado na
  abertura da barra seguinte do mesmo pregão, apenas se for consecutiva. Saída no
  sinal contrário e eventual reversão; para estocástico, o sinal contrário é o da
  zona oposta. Nenhuma posição carregada entre pregões: saída no fechamento da última
  barra disponível. A execução exata desse fechamento é hipótese otimista.
- Adaptação comum definida antes de medir: stop de 300 pontos e alvo de 600 pontos
  a partir do preço de entrada; stop e alvo na mesma barra resolvidos pelo stop.
  Stops em salto executam na abertura, inclusive derrapagem. A ausência de dados
  dentro da barra impede saber a sequência real de preços.
- Derrapagem de 5 pontos na entrada e em saída por stop, sinal ou fim de pregão;
  alvo limitado sem derrapagem. Comissão R$ 0,25 por lado; R$ 0,20 por ponto.
  Nova entrada só depois de sinal novo; não reentrar na barra em que stop/alvo saiu.
- Indicadores carregam histórico entre pregões, mas são reinicializados em rolagem,
  conforme `config/rolagens.yaml`, para não misturar contratos. Eles não usam dados
  futuros. Só barras completas com todos os minutos componentes são reamostradas.
- Período longo: M5 e M15, 31/03/2023–30/12/2025; 2023 é parcial. 2026: M5 e M15,
  02/01–30/09. Comparação equivalente de M1/M5/M15: 11/02–30/09/2026 a partir do
  mesmo M1; o início parcial de 10/02 é excluído. O último dia de outubro nunca entra.
- Esta grade de tempos e regras é exploratória, não demonstra vantagem, nem garante
  que a maior pontuação se repita. Não otimizar parâmetros posteriormente sem
  informar a mudança. Negócios, tamanho, custos e rolagens são hipóteses verificáveis.
