# VPS Hostinger — preparação e acesso

VPS: Hostinger KVM 2 (2 vCPU, 8 GB RAM), Ubuntu. Os scripts ficam em `infra/vps/` e são
numerados na ordem de execução. Todos podem ser rodados de novo sem estragar o que já foi feito.

## 1. Chave SSH no seu computador (uma vez)

No Windows (PowerShell) ou Linux/macOS:

```bash
ssh-keygen -t ed25519 -C "robo-b3" -f ~/.ssh/robo-b3
```

No hPanel da Hostinger: **VPS → Configurações → Chaves SSH → Adicionar** e cole o conteúdo de
`~/.ssh/robo-b3.pub`. (Ou, se ainda entra com senha: `ssh-copy-id -i ~/.ssh/robo-b3.pub root@IP_DA_VPS`.)

Adicione ao `~/.ssh/config` do seu computador (no Windows: `C:\Users\SEU_USUARIO\.ssh\config`):

```sshconfig
Host robo-b3-root
    HostName IP_DA_VPS
    User root
    IdentityFile ~/.ssh/robo-b3

Host robo-b3
    HostName IP_DA_VPS
    User robo
    IdentityFile ~/.ssh/robo-b3
    ForwardAgent yes
    # túneis: dashboard (8080) e noVNC do MT5 (3000)
    LocalForward 8080 127.0.0.1:8080
    LocalForward 3000 127.0.0.1:3000
```

## 2. Bootstrap (como root, uma vez)

Ainda sem o repositório na VPS, envie só o script:

```bash
scp infra/vps/00-bootstrap.sh robo-b3-root:/root/
ssh robo-b3-root 'bash /root/00-bootstrap.sh'
```

O script cria o usuário `robo` (pede uma senha para o `sudo`), copia sua chave, desativa login por
senha **somente se a chave existir**, ativa `ufw` (só SSH), fail2ban, atualizações de segurança,
fuso `America/Sao_Paulo` e swap de 2 GB.

> **Antes de fechar a sessão root**, abra outro terminal e confirme: `ssh robo-b3`.
> Se falhar, o terminal web do hPanel continua funcionando para corrigir.

## 3. Antigravity via SSH

O Antigravity (fork do VS Code) usa o mesmo `~/.ssh/config`:

1. Paleta de comandos → **Remote-SSH: Connect to Host…** → `robo-b3`
   (se a extensão Remote-SSH não vier instalada, instale pelo painel de extensões)
2. Abra a pasta `/home/robo/robo-b3` depois do passo 5
3. O terminal integrado já roda **na VPS** — os próximos comandos podem ser feitos por ali

Alternativa sem IDE: `ssh robo-b3` em qualquer terminal. Os túneis do `LocalForward`
sobem junto com a conexão.

## 4. Docker (como `robo`)

```bash
bash 01-docker.sh      # copie com: scp infra/vps/01-docker.sh robo-b3:~
exit && ssh robo-b3    # relogar para o grupo docker valer
docker run --rm hello-world
```

## 5. GitHub e clone

```bash
bash 02-github.sh SEU_USUARIO_GITHUB/robo-b3
```

O script gera uma **deploy key somente leitura**, mostra a chave pública para você colar em
GitHub → repo → Settings → Deploy keys, testa a conexão e clona em `~/robo-b3`.
Para dar `git push` a partir da VPS (editando pelo Antigravity), use o `ForwardAgent yes` acima:
sua chave pessoal do GitHub é usada sem ficar gravada na VPS. Ver [fluxo-git.md](fluxo-git.md).

## 6. Diagnóstico

```bash
cd ~/robo-b3 && bash infra/vps/03-diagnostico.sh | tee logs/diagnostico-$(date +%F).txt
```

Cole o resultado no Notion. Itens importantes para as próximas fases: memória livre, disco,
se há virtualização aninhada (VM Windows) e quais portas estão expostas.

## 7. Laboratório e dados

```bash
make docker-build
make docker-test
# do seu computador, enviar CSV exportado do MT5:
scp WIN_N_M1.csv robo-b3:~/robo-b3/data/raw/
# na VPS:
docker compose run --rm lab relatorio-dados data/raw/WIN_N_M1.csv
```

## 8. Atualizar o código

```bash
bash infra/vps/deploy.sh
```

Faz `git pull --ff-only`, reconstrói a imagem e roda os testes. Recusa se houver alterações
locais não commitadas. Fazer fora do pregão quando o MT5 estiver rodando.

## Segurança — lembretes

- Docker publica portas **por fora do ufw**. No `docker-compose.yml` toda porta é presa a
  `127.0.0.1`; acesso só pelos túneis SSH.
- `.env` e `config/risk.yaml` ficam fora do git (`chmod 600 .env`).
- A senha do MT5 fica no próprio terminal (salvar senha no primeiro login), não no `.env`.
- O painel da Hostinger tem um firewall próprio; se ativar, libere só a porta 22.

## O que NÃO roda na VPS: Profit Pro

Resposta da Nelogica (27/10/2026, solicitação 3427474): no Linux, editor NTSL, automação em
simulação e exportação de dados não estão disponíveis, e a licença do Profit Pro vendido pela Clear
ainda depende de validação para Linux. A alternativa (VM Windows na VPS) não tem suporte deles.

Decisão: **Profit Pro fica no computador Windows**. A VPS cuida de Python, dados, backtest,
monitoramento e MT5 demo. Detalhes no Notion, seção "Compatibilidade do Profit Pro com a VPS Linux".
