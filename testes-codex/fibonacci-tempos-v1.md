# Comparação de tempos das quatro fichas Fibonacci

Especificação anterior à rodada. As regras de `fibonacci-v1.md` e
`retracao-38-50-v1.md` são mantidas, com estas alterações de escala: sinais e
execução no mesmo tempo M1, M5 ou M15; entrada na abertura da barra seguinte à
barra de sinal. A primeira hora do Fibogap continua sendo a primeira hora, com
60, 12 ou 4 barras completas. Os pivôs são confirmados pelo fechamento no tempo
selecionado, com a mesma reversão de 300 pontos. Não há calibração por tempo;
o alvo estrutural, stop inicial, trailing 300/150, custos e filtros anteriores
são mantidos. As decisões não usam informação posterior ao sinal.

A grade longa compara M5 e M15 na fonte M5 em 03/04/2023–30/12/2025 e
02/01–30/09/2026; a grade comum compara M1/M5/M15, todos derivados da mesma fonte
M1, em 11/02–30/09/2026. Outubro não entra. As barras incompletas agregadas são
removidas, sem preenchimento. Os recortes são exploratórios; 2026 não é validação
independente. A comparação de regras em tempos diferentes não mantém as mesmas
entradas; só as duas saídas de um mesmo tempo usam entradas pareadas. O preço dentro
da barra é desconhecido, portanto o backtest usa hipótese adversa de execução.
