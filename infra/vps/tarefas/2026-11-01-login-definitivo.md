Tarefa (fim de semana, sem pregão): validar o login definitivo do MT5. Leia o AGENTS.md e
docs/mt5.md ("Solução em três camadas"). O Thiago está disponível para logar pela tela uma vez.

0) git fetch && git checkout fix/mt5-login-definitivo && git pull
   make docker-build && make docker-test   (N passed, 1 skipped é o esperado)
   docker compose --profile mt5 build mt5

1) Primeira partida com o Wine num volume novo:
   docker compose --profile mt5 up -d --force-recreate mt5   → espere healthy.
   Veja se logou sozinho (título da janela com 1195572676; "authorized" no log do terminal).
   Se não logou: pause os cliques automáticos (docker exec mt5 pkill -STOP -f main.sh) e peça ao
   Thiago para logar pela tela UMA vez, com "Salvar senha".

2) Reinício: docker compose restart mt5. Meça quanto tempo o "stop" levou (deve ser bem menos de
   60 s, sinal de que o MT5 fechou sozinho e não foi morto). Depois de healthy: logou sozinho?

3) Recriação: docker compose --profile mt5 up -d --force-recreate mt5. Depois de healthy: NÃO pode
   aparecer "Accounts: deleted due security reason" no log; logou sozinho?

4) Repita 2 e 3 mais uma vez cada (duas partidas seguidas sem ninguém tocar na tela).

5) infra/vps/mt5-login-check.sh; echo $?  → 0 e "logado" em logs/mt5-login.log.
   docker compose --profile mt5 run --rm coletor  → 0 dias novos, sem erro.

6) Se 2, 3 e 4 logaram sozinhos:
   - leve para a main: git checkout main && git merge --ff-only fix/mt5-login-definitivo && git push
   - apague as branches já incorporadas (local e remota): fix/mt5-login-definitivo,
     fix/mt5-login-config, fix/mt5-wine11-inicializacao
   - cron do robo: acrescente  0 8 * * 1-6 /home/robo/robo-b3/infra/vps/mt5-login-check.sh
   Se algum passo falhou: NÃO leve para a main; volte o checkout para a main, recrie o mt5 com a
   imagem da main e peça ao Thiago para logar pela tela. Reporte exatamente qual camada falhou.

O mt5 termina healthy e logado em qualquer caso. Relatório no formato do AGENTS.md, com uma tabela:
passo | logou sozinho? | "deleted due security reason"? | tempo do stop.
