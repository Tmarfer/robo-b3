# Três hipóteses de Fibonacci — WIN, pesquisa exploratória

Adaptações objetivas das fichas do Notion, escritas antes das rodadas. Elas não são
uma reprodução garantida de métodos discricionários dos livros.

- [Fibogap](https://app.notion.com/p/3d93357dd573463ea099fe3291491d0a)
- [Pivô 1-2-3 com Fibonacci](https://app.notion.com/p/b6c3b9a3529744208b83ffce90114f19)
- [Fibonacci em duas etapas](https://app.notion.com/p/7cbb23960b1640018157818f55c541fb)

## Definições comuns

- WIN M5 Clear; desenvolvimento 03/04/2023–30/12/2025 e 02/01–30/09/2026
  exploratório. 2023 e 2026 são parciais. Outubro de 2026 não é utilizado. O
  mesmo histórico já foi explorado antes: nada aqui é validação independente.
- Um contrato; no máximo uma operação por estratégia em cada pregão. Dias de
  rolagem são excluídos; indicadores e pivôs não misturam contratos. Apenas pregões
  que abrem às 09:00, sem lacunas nas quatro primeiras barras M15 e com barra M5
  das 17:00. Sinais formados após 16:30 não entram. Não carregar posições à noite.
- Sinal sempre em fechamento M15; entrada na abertura da M5 seguinte à conclusão
  do M15, com 5 pontos de derrapagem adversa. Não há entrada se faltar a barra ou
  se a abertura já estiver além do stop ou do alvo original. Stop e alvo estruturais
  são calculados com informação disponível no fechamento anterior, arredondados ao
  tick de 5 pontos: stop para fora da operação, alvo para dentro.
- Saída padrão: stop ou alvo da própria ficha; ao tocar ambos na mesma barra M5,
  assumir o stop. Em salto além do stop, preencher na abertura com derrapagem. Se
  abrir além do alvo, preencher na abertura. Fechar às 17:00 se nenhum ocorrer.
- Saída com trailing: mesmo sinal, entrada e stop estrutural inicial; sem alvo fixo.
  Após ganho de 300 pontos em relação à entrada, mover o stop para 150 pontos atrás
  do melhor preço. Não recuar o stop. Sinal de saída ou zeragem seguem iguais à
  padrão. Empregar hipótese adversa e marcar ambiguidades dentro da M5, como em
  `fichas-trailing-v2.md`; isso não recupera a sequência real dos negócios.
- Derrapagem 5 pontos adversos na entrada, saída por stop e por horário; sem
  derrapagem no alvo limitado. Comissão R$ 0,25 por lado; R$ 0,20 por ponto.

## Fibogap

Na abertura, gap de alta se preço abre acima da máxima da última M15 completa do
dia anterior; gap de baixa se abre abaixo da mínima dela. Após a primeira hora,
âncora A = mínima da última M15 anterior (alta) ou máxima dela (baixa), e âncora B
= máxima (alta) ou mínima (baixa) das quatro M15 da primeira hora. O intervalo
entre A e B forma os níveis L=0%, L+23,6%, L+76,4% e H=100%.

Depois das 10h, falha de fundo: uma barra M15 toca ou atravessa L, mas não fica
abaixo de L−11,8% da amplitude; a barra seguinte tem mínima igual ou maior e fecha
acima de L+23,6%. Compra na M5 seguinte. Stop = mínima da barra de teste − 5 pontos;
alvo = L+76,4%. Falha de topo é simétrica: testa H sem ultrapassar H+11,8%; barra
seguinte não supera a máxima e fecha abaixo de L+76,4%; venda, stop acima do teste e
alvo L+23,6%. A primeira oportunidade válida do pregão é a única considerada.

## Pivôs confirmados por ziguezague

Para as duas outras fichas, usa-se M15 **de fechamentos**, sem interpolar a ordem
interna. A partir da primeira barra do dia, um extremo de fechamento é confirmado
como pivô somente quando o fechamento recua 300 pontos em direção contrária. O
instante de confirmação, e não o da barra do extremo, determina quando pode ser
utilizado. Na primeira confirmação escolhe-se o sentido pelo movimento observado;
em empate, nenhum pivô. Pivôs reiniciam a cada pregão.

## Pivô 1-2-3

Compra: três pivôs confirmados consecutivos são fundo 1, topo 2 e fundo 3, com fundo
3 acima de fundo 1 e abaixo de topo 2. A primeira barra que fecha acima do topo 2,
na confirmação do pivô 3 ou depois, dispara a compra. Se fechar abaixo do fundo 1
antes, cancela. Stop = fundo 3 − 5 pontos; alvo = topo 2 + 0,618 × (topo 2 − fundo 1).
Venda é espelhada. Uma vez usado ou cancelado um conjunto de pivôs, ele não é reutilizado.

## Fibonacci em duas etapas

Compra: quatro pivôs confirmados consecutivos são fundo a, topo b, fundo c e topo d,
com a < c < d < b. A partir do fechamento que confirma d, calcular candidatos de
retração b − r(b−a), r em 0,382/0,5/0,618/0,786; extensão d − k(d−c), k em
1,272/1,618; projeção d − (b−c). Selecionar o trio com menor faixa, se sua
amplitude não ultrapassar 100 pontos; em empate vale a ordem das razões listadas.
Esse cluster é conhecido antes da entrada. Uma barra M15 **posterior** à confirmação
de d deve tocar a faixa do cluster e fechar acima da sua parte superior; compra na
M5 seguinte. Stop = limite inferior do cluster − 5 pontos; alvo = centro do cluster
+ 1,272 × (b − centro do cluster). Venda é espelhada. O primeiro cluster acionado
é o único do pregão. Um novo pivô confirmado substitui ou invalida o cluster anterior.

## Interpretação

As três abordagens contêm escolhas novas, especialmente confirmação de pivô, largura
do cluster e definição da falha. Quantidade reduzida de sinais e múltiplas escolhas
limitam a conclusão. A comparação é exploratória; não escolher uma operação vencedora
isolada ou usar um resultado positivo como prova de vantagem futura.
