"""
Lembrete leve: so dispara uma notificacao desktop X minutos antes do
horario de bater ponto, pra voce ja estar na frente da camera.

Nao abre navegador nem toca no Flit - so avisa.
Agendado no Task Scheduler para rodar as 08:55, 11:55, 12:55 e 17:55.
"""

import sys

from comum import is_dia_util, log, notificar


def main() -> None:
    if not is_dia_util():
        log("Lembrete: hoje nao e dia util, nada a avisar.")
        return

    notificar(
        "Ponto Certo",
        "Bater ponto em 5 minutos - deixe a camera livre e fique por perto.",
    )
    log("Lembrete enviado.")


if __name__ == "__main__":
    main()
    sys.exit(0)
