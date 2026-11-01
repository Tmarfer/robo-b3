# Stop móvel curto 30/15 — Fibogap e retração

As regras de entrada, stop estrutural inicial, alvo padrão, custos e filtros são as
mesmas de `fibonacci-v1.md` e `retracao-38-50-v1.md`. O teste substitui apenas a
saída móvel: ao alcançar 30 pontos favoráveis, o stop passa a proteger 15 pontos a
partir da entrada; depois acompanha o melhor preço a 15 pontos de distância. O
stop nunca recua. A saída móvel não tem alvo fixo. As operações do trailing e da
saída padrão usam as mesmas entradas em cada tempo.

Comparar M5/M15 no histórico longo e M1/M5/M15 no recorte comum de 11/02–30/09/2026,
com um contrato, custos e hipótese adversa já documentados. Outubro de 2026 fica
excluído; o trecho de 2026 é exploratório.
