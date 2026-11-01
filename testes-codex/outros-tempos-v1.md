# Comparação de tempos: falso rompimento e reteste

Especificação escrita antes da rodada. Para falso rompimento, adaptar o diagnóstico
confirmado de `rompimento-falso-v2.md`: sinal no fechamento da barra e entrada na
abertura da próxima barra consecutiva no tempo M1, M5 ou M15. Usar stop inicial
3 e 5 ticks, trailing 4/2 ticks, um contrato e os mesmos custos e hipótese adversa
da rodada anterior. Não é a entrada intrabar: os extremos não revelam sua sequência.
Os pregões são obtidos da série disponível, inclusive rolagens, como na rodada original.

Para o reteste de `reteste-media-v1.md`, usar sinal e execução no mesmo tempo M1,
M5 ou M15. As duas confirmações, reteste e MME20 são calculadas no próprio tempo,
com entrada na abertura seguinte, stop 300 e alvo 600 pontos, saídas e custos
anteriores. Dias de rolagem continuam excluídos. Esta é uma nova adaptação e a
versão original M15/M5 continua preservada.

M5/M15: 03/04/2023–30/12/2025 e 02/01–30/09/2026, da fonte M5. M1/M5/M15:
11/02–30/09/2026, da mesma fonte M1. Agregação exige barras completas; não preenche
lacunas. Outubro não entra e 2026 já foi explorado. Não interpretar a grade como
validação independente. A data e amplitude dos sinais variam entre os tempos.
