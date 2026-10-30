# Imagem do MT5 com Wine >= 10. O terminal se atualiza sozinho (build 6092 em 30/10/2026) e, com o
# Wine 9.0 da lprett/mt5linux (Alpine 3.20), avisa "unsupported Wine" e a ponte Python dá
# (-10005, 'IPC timeout'). Aqui só o Wine é trocado, vindo do Alpine edge (Wine 11.0 em 30/10).
#
# O edge muda com o tempo: um build novo pode trazer outro Wine. Por isso a imagem só é refeita
# de propósito, fora do pregão, e a versão instalada fica registrada em docs/mt5.md.
FROM lprett/mt5linux@sha256:bbb3bf9a7db0e8a02471aa76cbf81bad260b794a4f905f9d303dd753857290c3

# Wine 11 precisa de GnuTLS para criptografia e usa -i (não -init) no wineboot.
# Em reinícios, não aplicar a configuração novamente deve retornar sucesso sob set -e.
RUN apk add --no-cache --upgrade \
    --repository=https://dl-cdn.alpinelinux.org/alpine/edge/community \
    --repository=https://dl-cdn.alpinelinux.org/alpine/edge/main \
    wine gnutls \
 && sed -i 's/wineboot -init/wineboot -i/' /app/src/automation.sh \
 && grep -q 'wineboot -i >&2 2>/dev/null' /app/src/automation.sh \
 && sed -i 's/test \$FIRST_RUN || return$/test "$FIRST_RUN" || return 0/' /app/src/config.sh \
 && grep -q 'test "$FIRST_RUN" || return 0' /app/src/config.sh \
 && wine --version
