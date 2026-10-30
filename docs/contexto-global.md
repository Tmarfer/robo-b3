# Contexto global das 8h30 — definição

> Versão 1, escrita em 30/10/2026, **antes de qualquer cruzamento** com resultados de estratégia.
> Mudou uma regra? Nova versão, com data e motivo. Origem: avaliação do Mesa B3 de 30/10 e resposta
> do Thiago (Notion → Base de Conhecimento — Mesa B3 → Pareceres do Mesa).

## Para que serve

Medir se o cenário externo conhecido **antes da abertura** separa dias bons e ruins de uma
estratégia. Contexto não cria vantagem: só pode filtrar uma estratégia que já passou no
desenvolvimento. Filtrar uma estratégia negativa até ela ficar positiva é sobreajuste.

## Regras

1. **Hora de corte: 08:30 de Brasília.** Todo valor é o último disponível até 08:30:00. A Europa e
   os EUA mudam de horário de verão em datas diferentes do Brasil: o corte é sempre convertido do
   horário de Brasília, nunca fixado no horário de Londres ou de Nova York.
2. **Variação** = preço às 08:30 ÷ fechamento anterior − 1, em %. Na Ásia, que já fechou às 08:30,
   vale o fechamento do próprio dia.
3. **Linha válida para medir filtros** só se cada campo usado veio de fonte **intradiária com
   horário** (ou de fechamento já ocorrido antes das 08:30, caso da Ásia e dos ajustes da B3).
   Linha montada com fechamento do dia da Europa ou dos EUA é **inválida**: o campo fica vazio,
   nunca é preenchido com o fechamento.
4. **Os números vêm de script** (`robob3`, a escrever), com fonte fixa e registrada. O Mesa B3 não
   digita cotações: ele lê e escreve a leitura do dia nos Pareceres.
5. **Rótulos calculados**, nunca à mão (regra do Cenário abaixo).
6. **Campos de pós-abertura** (gap do WIN e do WDO, leilão atrasado ou estendido) servem para
   descrever o dia, **nunca como filtro**: não se conhecem às 08:30.
7. **Hipóteses de filtro registradas antes de medir**: no máximo 3 por estratégia, escritas na
   especificação dela (ex.: "não operar com S&P futuro z < −1"), medidas no desenvolvimento e
   confirmadas fora da amostra. Cruzar tudo com tudo e escolher o que deu certo é proibido.
8. O resultado da estratégia **não** fica no contexto: o cruzamento é feito em Python, juntando o
   contexto às operações do backtest pela data.

## Campos

| Grupo | Campo | Unidade | Observação |
| --- | --- | --- | --- |
| Coleta | Hora da coleta, Tipo de fonte, Válida para filtros | | regra 3 |
| Ásia (fechada) | Nikkei, Hang Seng, Xangai | % | fechamento do dia |
| Ásia (fechada) | Minério de ferro em Dalian | % | último preço da sessão diurna |
| Europa | Índice europeu fixo | % | Stoxx 600 se houver fonte intradiária; senão Euro Stoxx 50. Fixado ao validar a fonte |
| EUA | S&P 500 futuro, Nasdaq 100 futuro | % | às 08:30 |
| EUA | VIX | nível e % | às 08:30, se houver fonte com horário |
| EUA | Treasury de 10 anos | variação em pb | às 08:30 |
| Moedas e commodities | DXY, Brent | % | às 08:30 |
| Brasil | EWZ pré-mercado | % | com caixa "havia dado"; pré-mercado fino |
| Brasil | Ajuste anterior do WIN, WDO e DI1F | pontos / taxa | ajuste da B3 da véspera |
| Brasil | Dólar (NDF ou USD/BRL offshore) às 08:30 | R$ | se houver fonte com horário |
| Calendário | Vencimento do WIN, rolagem do WDO, feriado nos EUA | sim/não | calculados (`config/rolagens.yaml`) |
| Calendário | Eventos do dia | lista fixa | abaixo |
| Pós-abertura | Gap do WIN e do WDO | pontos e em ATR de 20 dias | regra 6 |
| Pós-abertura | Leilão atrasado ou estendido | sim/não | detectado no M1 (regra 6) |

## Cenário (z-score) — congelado

- **z** = variação do dia ÷ desvio-padrão da **mesma medida** (variação até as 08:30) nos **60
  pregões anteriores** daquele mercado, sem incluir o dia. Com menos de 40 valores válidos, z fica
  vazio.
- **Forte** se z > +1; **fraco** se z < −1; senão neutro.
- Regiões: **Ásia** = média dos z do Nikkei e do Hang Seng; **Europa** = índice europeu fixo;
  **EUA** = S&P 500 futuro; **Dólar** = DXY; **Petróleo** = Brent (alta / queda).
- **Neutro** quando nenhuma região, o dólar ou o petróleo está forte ou fraco e não há evento.
- Gap: em unidades de ATR de 20 dias do próprio ativo (WIN ou WDO), só para descrição.
- 60 pregões em vez de 20: com 20 valores o desvio-padrão estimado varia ~16%, com 60 ~9%; menos
  troca de rótulo por ruído da própria estimativa.

## Eventos (lista fixa)

Datas tiradas dos calendários oficiais (BCB, Fed, BLS, IBGE), reconstruíveis para 5 anos:

| Evento | Horário (Brasília) | Dia marcado |
| --- | --- | --- |
| Copom — decisão | ~18:30, depois do pregão | **dia seguinte** ("Pós-Copom") |
| FOMC — decisão | 15:00 ou 16:00, com o pregão aberto | o próprio dia |
| Payroll (EUA) | 09:30 ou 10:30 | o próprio dia |
| CPI (EUA) | 09:30 ou 10:30 | o próprio dia |
| IPCA | 09:00 | o próprio dia |

"Dia de evento" é calculado a partir desta lista. Outros eventos podem ir em observação, mas não
entram em filtro sem nova versão desta definição.

## Fontes (a validar antes do backfill)

| Dado | Candidata gratuita | Situação |
| --- | --- | --- |
| Nikkei, Hang Seng, Xangai | fechamento diário (Yahoo Finance) | serve: fecham antes das 08:30 |
| Europa, S&P e Nasdaq futuros, Brent, DXY | histórico de minuto da Dukascopy | **a validar**: acesso grátis, cobertura de 5 anos, acesso da VPS |
| VIX, Treasury 10 anos, NDF/USD-BRL | a pesquisar | pode ficar sem histórico; então não entra em filtro |
| Minério em Dalian | a pesquisar | idem |
| EWZ pré-mercado | a pesquisar | histórico gratuito raro: caixa "havia dado" |
| Ajustes WIN, WDO, DI1F | B3 (ajustes do pregão) | serve |

Um campo sem histórico confiável de 3 a 5 anos pode ser coletado daqui para a frente, mas não entra
em hipótese de filtro antes de ter dias suficientes.
