# Estratégia: NOME — ATIVO — vX

> Escrever **antes** de codificar. Mudou uma regra? Nova versão (v2, v3…) com data e motivo.

## Hipótese
Por que isso deveria funcionar? Qual comportamento do mercado se explora?

## Dados
- Série: símbolo, fonte, período, timeframe
- Ajuste de rolagem: ajustada / não ajustada / por vencimento
- Desenvolvimento: AAAA-MM-DD a AAAA-MM-DD
- Fora da amostra (não olhar até o fim): AAAA-MM-DD a AAAA-MM-DD

## Regras
| Item | Regra |
| --- | --- |
| Horário de entradas | |
| Sinal de compra | |
| Sinal de venda | |
| Stop | |
| Alvo | |
| Saída por tempo / zeragem | |
| Tamanho (contratos) | |
| Máx. operações por dia | |
| Perda máxima diária | |

## Execução simulada no backtest
- Preço de entrada: abertura da barra seguinte / outro
- Custo por contrato (corretagem + emolumentos): R$
- Derrapagem: pontos por lado
- Stop e alvo na mesma barra M1: assumir **stop** (conservador)

## Parâmetros
Lista de parâmetros e valores testados. Quantas combinações? (muitas → risco de sobreajuste)

## Resultado
Preenchido depois. Link para o notebook/relatório e para a página no Notion.
