# Retração de 38–50% da tendência — adaptação exploratória

Fonte: [ficha retracao-38-50 no Notion](https://app.notion.com/p/d30fb32a3b964a90a73cfe5cb004829f).
A ficha não define objetivamente os pivôs; esta é uma adaptação, não reprodução
comprovada do método discricionário. As regras abaixo foram escritas antes da rodada.

## Tendência e entrada

- Mesmo procedimento de `fibonacci-v1.md`: pivôs em fechamentos M15, confirmados
  somente após reversão de 300 pontos; reiniciar a cada pregão, sem interpolar
  preços e sem usar o instante anterior à confirmação como entrada. A ficha cita
  M5; usar M15 para sinal e M5 para execução é uma escolha desta adaptação.
- Alta = últimos quatro pivôs confirmados fundo A, topo B, fundo C, topo D, com
  A < C < B < D. A última perna é C→D. Baixa é o espelho. Isso é uma definição de
  tendência, não comprovação de tendência no mercado.
- Após D estar confirmado, a primeira barra M15 que **fecha** na zona de retração
  de 38,2% a 50% da perna C→D gera sinal a favor da tendência. A confirmação de D
  pode ocorrer na própria barra de sinal, desde que o fechamento esteja na zona.
  Entrada na abertura da próxima M5; se o preço saltar além do stop ou alvo, não
  entrar. Antes do sinal, um fechamento que exceda o topo D ou a retração de 66,7%
  invalida esse conjunto de pivôs. Não reutilizar o mesmo conjunto depois de sinal.
- Stop estrutural = retração de 66,7% da perna mais um tick para fora. Alvo padrão
  = preço do pivô D. Versão móvel usa o **mesmo sinal, entrada e stop inicial**, sem
  alvo fixo: ativa com 300 pontos de ganho e acompanha a 150 pontos do melhor preço.
  O alvo padrão deve ser viável na abertura para que ambas as versões sejam avaliadas
  sobre as mesmas entradas.

## Período, execução e limites

Mesmo recorte, filtros de pregão, uma operação por dia, custos, saída às 17h,
tratamento de rolagem e hipótese adversa para ambiguidades de `fibonacci-v1.md`:
03/04/2023–30/12/2025 e 02/01–30/09/2026, no WIN, com um contrato. 2023 e 2026 são
parciais. Outubro de 2026 não integra o teste. O histórico de 2026 já foi explorado
e não é validação independente. A aproximação não recupera a ordem intrabar e a
ficha não oferece evidência de que retrações específicas gerem vantagem.
