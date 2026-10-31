# Rompimento falso da barra anterior com stop móvel — v2

Escolhas de Thiago: usar a máxima e mínima da barra anterior; testar stops iniciais
de 3 e de 5 ticks; ao alcançar 4 ticks de ganho a partir do preço preenchido, mover
o stop para proteger 2 ticks e então mantê-lo a 2 ticks do melhor preço alcançado.
WIN: 1 tick = 5 pontos. As regras são espelhadas para compra e venda.

## Regras fixadas antes da rodada

- Sinais em M1, somente barras consecutivas no mesmo pregão. Se o preço ultrapassar
  a máxima anterior em pelo menos um tick e voltar para um tick abaixo daquela
  máxima, vender. Se perder a mínima em um tick e recuperar para um tick acima,
  comprar. Em abertura além do nível considera-se o rompimento já armado. Não se
  presume movimento no intervalo sem negócios entre o fechamento e a abertura.
- Uma posição de um contrato por vez e no máximo uma entrada em cada barra M1.
  Nenhuma entrada na última barra. Ao encerrar uma operação, não reentrar na mesma
  barra. Posições abertas são zeradas no fechamento da última barra disponível.
- Preenchimento no preço de gatilho, ou na abertura se o stop foi ultrapassado em
  um salto, com derrapagem adversa de 5 pontos na entrada e em qualquer saída.
  Comissão simulada R$ 0,25 por lado; cada ponto do WIN vale R$ 0,20. Não há alvo fixo.
- Stop inicial é calculado a partir do preço efetivamente preenchido. A partir de
  quatro ticks de excursão favorável, o stop passa a acompanhar o melhor preço em
  distância de dois ticks, nunca voltando contra a posição. Saltos podem executar
  a preços piores do que o stop. Fim de pregão usa o último fechamento disponível,
  com execução nesse fechamento como hipótese, não garantia.
- Dados: WIN M1 da Clear, 11/02/2026 a 30/09/2026. O primeiro dia da exportação é
  parcial e fica de fora; outubro de 2026 não entra. Período exploratório, não é
  validação independente. A série de M1 mais longa disponível não cobre 2023–2025.

## Limitação decisiva: ordem dos preços

As barras M1 não guardam a ordem das negociações. A simulação descreve dois caminhos
hipotéticos: abertura → máxima → mínima → fechamento e abertura → mínima → máxima →
fechamento, em passos de um tick. Cada cenário é uma suposição completa, não uma
reconstituição dos negócios, nem um limite matemático para todos os caminhos possíveis.
As duas sequências usam os mesmos OHLC e podem produzir entradas, stops e resultados
diferentes. Não são dados tick a tick; spread, liquidez e atrasos também não são
conhecidos. A comparação serve para medir a sensibilidade, não para provar lucratividade.

## Revisão depois da primeira rodada

A rodada de caminhos retos gerou frequência e ganhos artificiais porque a interpolação
supõe trajetos monotônicos que os OHLC não sustentam. Os resultados dessa rodada são
**inválidos para avaliação financeira**, mesmo com duas ordens de extremos. O manifesto
é preservado para auditoria. Em seguida, faz-se diagnóstico separado com sinal no
fechamento e entrada na abertura da barra seguinte, e tratamento adverso da ambiguidade.
Essa confirmação altera o instante de entrada solicitado e deve ser apresentada como
aproximação, não como a execução exata da estratégia original.

### Diagnóstico com sinal confirmado e tratamento adverso

- Sinal de venda: uma barra supera a máxima anterior em pelo menos 1 tick e fecha
  pelo menos 1 tick abaixo dela. O sinal de compra é o espelho. Se ambos ocorrerem
  na mesma barra, descartar o sinal. A entrada ocorre na abertura seguinte, somente
  no mesmo pregão e com barras consecutivas; ela pode diferir do retorno intrabar.
- Dentro de cada barra, se o stop já em vigor e uma melhora forem possíveis, executar
  o stop primeiro. Se o stop anterior não tiver sido tocado e o preço puder ativar
  o trailing, admitir que o preço tenha voltado ao pior stop móvel alcançável segundo
  a mínima/máxima da barra, mesmo que outro caminho também seja possível. Isso é uma
  hipótese adversa sobre o caminho, não a observação dos negócios ou garantia de um
  limite de perdas reais. Quando não houver toque possível, registrar o maior avanço
  do stop ao fim da barra. Aplicam-se as mesmas hipóteses de custos e gaps acima.
