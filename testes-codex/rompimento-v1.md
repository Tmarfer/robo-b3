# Experimento Codex: rompimento da máxima anterior — v1

Hipótese proposta por Thiago: comprar o rompimento da máxima da barra anterior no WIN,
com alvo de 3% e stop de 10% do preço de entrada. Ambas as porcentagens são do índice,
não do capital. Este teste é exploratório; não envia ordens.

## Definições para a primeira medição

- WIN contínuo M5, desenvolvimento de 31/03/2023 a 30/12/2025. 2023 é parcial.
- Um contrato, somente compras; uma posição por vez, com novas entradas após a saída.
- A primeira barra de cada pregão só serve de referência. A entrada acontece quando
  uma barra seguinte atinge a máxima da barra M5 anterior mais 5 pontos; se abrir acima,
  usa-se a abertura. Exigem-se barras consecutivas, sem atravessar pregões ou lacunas.
- Alvo em 103% e stop em 90% da entrada, arredondados ao tick de 5 pontos.
  Alvo arredondado para cima, stop para baixo. Após o preenchimento, monitorar até
  o alvo ou o stop, ou zerar no fechamento da última barra disponível do pregão.
  Não se abre posição na última barra. Pode haver várias operações no mesmo pregão.
- Derrapagem de 5 pontos contra na entrada, stop e saída por tempo; alvo limitado
  sem derrapagem. Comissão R$ 0,25 por lado, valor do ponto R$ 0,20 por contrato.
- Se stop e alvo forem atingidos na mesma barra, vale o stop; na barra de entrada,
  uma mínima abaixo do stop também conta como stop por prudência, pois a ordem dos
  preços não é conhecida em M5. Saltos além do stop saem na abertura da barra.
- Não abrir nova posição na mesma barra da saída. Pregões sem duas barras consecutivas
  não operam. A última barra disponível pode não representar o encerramento oficial
  se houver falha de dados; por isso o resultado depende da qualidade do histórico.

Comparar resultado por ano, número de operações, custos, drawdown e motivos de saída.
Não escolher parâmetros depois de ver o resultado e chamar isso de validação. O período
reservado de 2026 só é acessado mediante pedido explícito. Em 31/10/2026, Thiago
autorizou uma rodada de 02/01/2026 a 30/09/2026; outubro permanece intocado. Essa
rodada parcial fica separada do desenvolvimento. Os custos são hipóteses, não uma nota
de corretagem. A série contínua pode conter efeitos de rolagem.
