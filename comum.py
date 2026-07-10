"""Funcoes compartilhadas entre lembrete.py, bater_ponto.py e setup_login.py."""

import datetime
import os
import time
from pathlib import Path
import random

import holidays
from dotenv import load_dotenv
from playwright.sync_api import Page
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

BASE_DIR = Path(__file__).parent
LOG_FILE = BASE_DIR / "bater_ponto.log"
# Perfil persistente do Chrome (cookies + localStorage + IndexedDB).
# O Flit usa Firebase Auth, que guarda a sessao em IndexedDB - e
# `context.storage_state()` (a abordagem antiga, so cookies+
# localStorage) NAO salva IndexedDB, entao a sessao nunca "colava"
# entre setup_login.py e bater_ponto.py. Um profile dir persistente
# (como um perfil de verdade do Chrome) resolve isso.
PROFILE_DIR = BASE_DIR / "chrome_profile"
SESSAO_OK_MARKER = PROFILE_DIR / "SESSAO_OK.txt"
URL = "https://web2.flitapp.com.br/"

load_dotenv(BASE_DIR / ".env")


def log(msg: str) -> None:
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def is_dia_util(date: datetime.date | None = None) -> bool:
    """True se for dia util (nao e sabado/domingo nem feriado nacional)."""
    date = date or datetime.date.today()
    if date.weekday() >= 5:  # 5=sabado, 6=domingo
        return False
    br_holidays = holidays.Brazil(years=date.year)
    if date in br_holidays:
        return False
    return True


def notificar(titulo: str, mensagem: str) -> None:
    try:
        from plyer import notification

        notification.notify(title=titulo, message=mensagem, timeout=10)
    except Exception as e:  # notificacao nao pode derrubar o script
        log(f"Falha ao notificar ({titulo}): {e}")


def carregar_credenciais() -> tuple[str, str] | None:
    """Le FLIT_CPF/FLIT_SENHA do .env. Retorna None se nao configurado
    (nesse caso o login precisa ser feito manualmente)."""
    cpf = os.getenv("FLIT_CPF")
    senha = os.getenv("FLIT_SENHA")
    if not cpf or not senha:
        return None
    return cpf, senha


def habilitar_acessibilidade(page: Page, timeout_ms: int = 20_000) -> None:
    """O Flit e um app Flutter Web: por padrao ele so desenha os campos
    e botoes em canvas (pixels), sem nenhum elemento HTML com texto ou
    label de verdade - por isso nenhum seletor por texto/role funciona
    de cara (foi o motivo do login "nao funcionar").

    Duas coisas precisam acontecer pra isso mudar:

    1. O Chromium precisa ligar a arvore de acessibilidade real dele
       (isso e o sinal que o Flutter Web usa pra detectar leitor de
       tela e ligar a propria arvore de semantica). Fazemos isso via
       CDP (`Accessibility.enable`) - o mesmo mecanismo que ferramentas
       de leitor de tela/teste usam.
    2. Existe tambem um elemento invisivel `<flt-semantics-placeholder>`
       ("Enable accessibility") que o Flutter espera que seja clicado.
       Ele some do DOM quando a ativacao termina.

    AVISO HONESTO: essa ativacao se mostrou instavel nos meus testes -
    as vezes funciona rapido, as vezes demora bem mais. Por isso essa
    funcao fica tentando (clica de novo a cada ~1s) ate `timeout_ms`
    (20s por padrao) em vez de tentar só uma vez. Nao consegui
    confirmar 100% em um Playwright "real" (o sandbox onde eu testei
    bloqueia baixar o Chromium), entao se ainda assim travar, me manda
    o log que a gente ajusta - pode ser que precise de uma abordagem
    diferente (cliques por coordenada em vez de label).

    Precisa ser chamado de novo a cada `page.goto()`/reload (nao
    persiste entre carregamentos de pagina). E seguro chamar mais de
    uma vez na mesma pagina.
    """
    try:
        cdp = page.context.new_cdp_session(page)
        cdp.send("Accessibility.enable")
    except Exception as e:
        log(f"AVISO: nao consegui habilitar Accessibility via CDP: {e}")

    deadline = time.monotonic() + timeout_ms / 1000
    while time.monotonic() < deadline:
        placeholder = page.locator("flt-semantics-placeholder")
        if placeholder.count() == 0:
            break
        try:
            placeholder.evaluate("el => el.click()")
        except Exception:
            pass
        page.wait_for_timeout(1_000)

    # da um tempo extra pra arvore de semantica terminar de montar
    # depois que o placeholder some
    page.wait_for_timeout(1_500)

    # ACHADO AO VIVO: so remover o placeholder nao basta - o Flutter so
    # monta de verdade a arvore de semantica da tela atual quando
    # processa uma interacao real de ponteiro (toque/scroll) na pagina.
    # Um scroll minimo (sem clicar em nada, sem risco de navegar ou
    # acionar algo) e suficiente pra "acordar" isso, confirmado ao vivo
    # na tela inicial (nav bar + botao "Marcar ponto" so apareceram na
    # arvore de semantica depois de um scroll assim).
    try:
        page.mouse.wheel(0, 2)
        page.wait_for_timeout(300)
        page.mouse.wheel(0, -2)
        page.wait_for_timeout(1_000)
    except Exception as e:
        log(f"AVISO: scroll de 'acordar semantica' falhou: {e}")


def digitar(page: Page, locator, texto: str, timeout_ms: int = 15_000) -> None:
    """Clica no campo e digita caractere por caractere (teclado real).

    `locator.fill()` nao funciona nesses campos do Flutter: ele so troca
    o .value do input escondido via JS e dispara um evento genérico,
    sem os eventos de teclado que o Flutter realmente escuta - o campo
    fica "preenchido" no DOM mas o app continua achando que esta vazio
    (foi testado e confirmado). `press_sequentially` simula teclas de
    verdade, uma por uma, e funciona.
    """
    locator.wait_for(state="visible", timeout=timeout_ms)
    locator.click()
    for letra in texto:
        locator.press_sequentially(letra)
        page.wait_for_timeout(random.randint(60, 120))


def _posicao_do_texto(page: Page, texto: str) -> dict | None:
    """Procura, direto no DOM (sem passar pela API de accessibility do
    Playwright), um <flt-semantics role="button"> cujo texto contenha
    `texto`, e devolve o centro dele em coordenadas de viewport (o que
    `page.mouse.click()` espera). Retorna None se nao achar."""
    js = """
        (texto) => {
            const els = document.querySelectorAll('flt-semantics[role="button"]');
            for (const el of els) {
                const conteudo = (el.textContent || '').trim();
                if (conteudo.includes(texto)) {
                    const r = el.getBoundingClientRect();
                    if (r.width > 0 && r.height > 0) {
                        return {x: r.x + r.width / 2, y: r.y + r.height / 2};
                    }
                }
            }
            return null;
        }
    """
    return page.evaluate(js, texto)


def aguardar_elemento_com_texto(page: Page, texto: str, timeout_ms: int = 20_000) -> None:
    """So confere (sem clicar) que um <flt-semantics role="button"> com
    esse texto apareceu na tela."""
    deadline = time.monotonic() + timeout_ms / 1000
    while time.monotonic() < deadline:
        if _posicao_do_texto(page, texto) is not None:
            return
        page.wait_for_timeout(500)
    raise PlaywrightTimeoutError(
        f"Nao encontrei um elemento com texto '{texto}' em {timeout_ms}ms"
    )


def clicar_por_texto(page: Page, texto: str, timeout_ms: int = 20_000) -> None:
    """Acha um <flt-semantics role="button"> pelo texto e clica na
    posicao real dele na tela.

    Por que nao usar `page.get_by_role("button", name=texto)`: em
    testes ao vivo (confirmado pelo usuario, que inspecionou o elemento
    no DevTools e viu `role="button"` certinho no HTML) o Playwright
    nao estava reconhecendo esses elementos <flt-semantics> customizados
    via essa API de forma confiavel, mesmo com o elemento existindo e
    correto no DOM. Buscar via CSS (`flt-semantics[role="button"]`) +
    texto e clicar via coordenada real (`getBoundingClientRect` +
    `page.mouse.click`) evita depender desse calculo de accessibility.
    """
    deadline = time.monotonic() + timeout_ms / 1000
    while time.monotonic() < deadline:
        pos = _posicao_do_texto(page, texto)
        if pos is not None:
            page.mouse.click(pos["x"], pos["y"])
            return
        page.wait_for_timeout(500)
    raise PlaywrightTimeoutError(
        f"Nao encontrei um botao com texto '{texto}' em {timeout_ms}ms"
    )


def fazer_login(page: Page, cpf: str, senha: str, timeout_ms: int = 20_000) -> None:
    """Preenche CPF + senha e loga no Flit.

    Assume que a pagina de login ('Fazer login' / CPF) ja esta visivel.
    Nao mexe na etapa de camera/identificacao facial - login e so
    CPF+senha, a verificacao facial acontece depois, no 'Marcar ponto'.
    """
    habilitar_acessibilidade(page, timeout_ms)

    campo_cpf = page.locator('input[aria-label="CPF"]')
    digitar(page, campo_cpf, cpf, timeout_ms)
    clicar_por_texto(page, "Próxima", timeout_ms)
    

    campo_senha = _localizar_campo_senha(page, timeout_ms)
    digitar(page, campo_senha, senha, timeout_ms)
    clicar_por_texto(page, "Próxima", timeout_ms)


def _localizar_campo_senha(page: Page, timeout_ms: int):
    """Confirmado ao vivo: aria-label="Informe sua senha" (input
    type="password"). Mantem outros candidatos + fallback generico
    como rede de seguranca caso o Flit mude o texto no futuro."""
    candidatos = ["Informe sua senha", "Senha", "senha"]
    for label in candidatos:
        loc = page.locator(f'input[aria-label="{label}"]')
        try:
            loc.wait_for(state="visible", timeout=1_500)
            return loc
        except Exception:
            continue

    log(
        "AVISO: nao achei o campo de senha pelos aria-labels conhecidos "
        f"({candidatos}). Usando o ultimo <input> visivel como fallback."
    )
    return page.locator("input").last
