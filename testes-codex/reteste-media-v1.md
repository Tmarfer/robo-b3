# WIN: rompimento, reteste e média — hipótese exploratória v1

Proposta para pesquisa de Thiago, inspirada na ficha
[sr-inversao](https://app.notion.com/p/d191f4ba09ac49e7ae8e01ce1e99c4e1).
A ideia é testar se um rompimento da faixa do pregão anterior, confirmado e seguido
de um retorno ao nível, oferece entradas melhores que reagir a cada barra. A média
serve como filtro de direção; não é prova de tendência ou de vantagem.

## Regras definidas antes da rodada

- WIN contínuo da Clear, M15 para sinal, M5 para execução. Dados de 03/04/2023 a
  30/12/2025. O primeiro ano é parcial. O primeiro dia de exportação, 30/03/2023,
  é incompleto; o pregão seguinte fica fora por não ter referência completa.
- Níveis = máxima e mínima do pregão anterior. Não operar no dia de rolagem listado
  em `config/rolagens.yaml`. O filtro MME20 de fechamentos M15 reinicia na rolagem;
  M15 é gerado de M5 com três barras completas. Não preencher lacunas.
- Compra: duas barras M15 consecutivas fecham acima da máxima anterior. Depois, uma
  barra posterior toca ou atravessa essa máxima e fecha acima dela e da MME20; a
  MME20 deve estar subindo em relação à barra M15 anterior. Venda é espelhada: dois
  fechamentos abaixo da mínima anterior, reteste que toca a mínima e fecha abaixo,
  abaixo da média que está caindo. Os dois fechamentos e o reteste têm de ocorrer
  no mesmo pregão. Recuar e fechar do outro lado cancela a confirmação daquele lado.
- O sinal só é conhecido no fechamento M15. Entrar na abertura da M5 seguinte, se
  houver barra exatamente nesse horário, no mesmo pregão. Uma operação por dia;
  não operar após 16:45. Dias sem barra M5 das 17:00 ficam fora: não se usa um
  fechamento desconhecido para inventar a saída.
- 1 contrato. Stop de 300 pontos e alvo de 600 pontos contados a partir do preço
  preenchido; sem trailing. Se nenhum for atingido, encerrar na abertura das 17:00.
  Stop e alvo na mesma M5: assumir stop. Salto além do stop: usar abertura. Uma ordem
  limitada de alvo aberta além do alvo recebe preço de abertura. Entrada, stop e
  saída por tempo têm 5 pontos de derrapagem adversa; alvo limitado não tem.
  Comissão R$ 0,25 por lado; R$ 0,20/ponto.
- Três amostras visuais foram escolhidas por data antes de traçar a hipótese:
  05/06/2023, 05/06/2024 e 05/06/2025. Elas não constituem amostra estatística.

## Leitura dos resultados

Mostrar todos os negócios, anos, operações por ano, resultado líquido, fator de lucro,
drawdown, acerto e ambiguidades. Estes dados já foram vistos em outros experimentos;
qualquer resultado é exploratório. Não se abre outubro de 2026. Não há reconstrução
de ticks por interpolação e o histórico de 2026 não integra esta rodada. Um resultado
positivo não basta para aprovação; custos, execução e comparações precisam de revisão.

Na primeira execução, o resumo herdado não contabilizou as saídas por horário porque
o nome `tempo` diferia do esperado pelo agregador. As operações estavam registradas;
o manifesto original foi preservado, mas sua contagem `por_motivo` é inválida.
Uma nova rodada foi feita com a contagem corrigida, sem mudar as regras da estratégia.
