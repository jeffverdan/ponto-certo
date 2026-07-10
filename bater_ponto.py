"""
Bate o ponto no Flit.

Fluxo:
1. Confere se hoje e dia util (pula sabado/domingo/feriado nacional).
2. Abre o navegador com o perfil persistente salvo (chrome_profile/).
3. Concede permissao de camera/localizacao (sem precisar clicar no popup).
4. Clica em "Marcar ponto".
5. Espera a validacao facial ao vivo (voce precisa estar na frente da
   camera nesse momento) e o modal de confirmacao aparecer.
6. Clica em "Confirmar".
7. Baixa o comprovante em ./comprovantes.

Seletores sao baseados em texto visivel na tela (mais resistentes a
mudancas de layout do que classes CSS), mas podem precisar de ajuste
fino se o Flit mudar os textos dos botoes.
"""

import datetime
import sys

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

from comum import (
    BASE_DIR,
    PROFILE_DIR,
    SESSAO_OK_MARKER,
    URL,
    aguardar_elemento_com_texto,
    carregar_credenciais,
    clicar_por_texto,
    fazer_login,
    habilitar_acessibilidade,
    is_dia_util,
    log,
    notificar,
)

COMPROVANTES_DIR = BASE_DIR / "comprovantes"
ERRO_SCREENSHOT = BASE_DIR / "erro_bater_ponto.png"
TIMEOUT_VALIDACAO_FACIAL_MS = 60_000
TIMEOUT_PADRAO_MS = 20_000

def bater_ponto() -> None:
    if not is_dia_util():
        log("Hoje nao e dia util (fim de semana ou feriado). Nada a fazer.")
        return

    if not SESSAO_OK_MARKER.exists():
        log("ERRO: perfil ainda nao configurado. Rode setup_login.py primeiro.")
        notificar("Ponto Certo - ERRO", "Sessao nao configurada. Rode setup_login.py.")
        return

    notificar("Ponto Certo", "Batendo ponto agora - fique em frente a camera.")

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            headless=False,
            args=[
                "--force-renderer-accessibility"
            ],
        )
        context.grant_permissions(["camera", "geolocation"], origin=URL)
        page = context.pages[0] if context.pages else context.new_page()

        try:
            # TESTE DE VIDEO
            # page = context.new_page()
            # page.goto("https://webrtc.github.io/samples/src/content/getusermedia/gum/")
            # page.wait_for_timeout(30000)
            # return

            
            page.goto(URL, wait_until="domcontentloaded")
            # page.wait_for_timeout(30000)
            # return

            # O Flit e Flutter Web: sem isso, nenhum botao/campo tem
            # texto/label de verdade no DOM e nenhum seletor abaixo
            # funciona (ver comum.habilitar_acessibilidade).            
            habilitar_acessibilidade(page)            
            page.wait_for_timeout(1_500)            
            log("Verificando se sessao expirou...")
            campo_cpf = page.locator('input[aria-label="CPF"]')
            log(f"Campo CPF encontrado? {campo_cpf.count() > 0}")
            # Sessao expirada -> volta pra tela de login
            if campo_cpf.count() > 0:
                credenciais = carregar_credenciais()
                if not credenciais:
                    log("Sessao expirada e sem .env configurado. Rode setup_login.py.")
                    notificar(
                        "Ponto Certo - ERRO",
                        "Sessao expirada! Rode setup_login.py para logar de novo.",
                    )
                    return

                log("Sessao expirada. Logando de novo com as credenciais do .env...")
                cpf, senha = credenciais
                fazer_login(page, cpf, senha)
                aguardar_elemento_com_texto(page, "Marcar ponto", TIMEOUT_PADRAO_MS)
                log("Login automatico refeito com sucesso.")
            
            habilitar_acessibilidade(page)
            log("Sessao valida. Clicando em 'Marcar ponto'...")
            clicar_por_texto(page, "Marcar ponto", TIMEOUT_PADRAO_MS)
            log("Cliquei em 'Marcar ponto'. Aguardando validacao facial...")

            # Espera o modal de confirmacao (data/hora + botao Confirmar),
            # que so aparece depois que a foto ao vivo foi validada, e
            # confirma.
            clicar_por_texto(page, "Confirmar", TIMEOUT_VALIDACAO_FACIAL_MS)
            log("Ponto confirmado.")

            # Tela de comprovante -> baixa o arquivo
            COMPROVANTES_DIR.mkdir(exist_ok=True)
            with page.expect_download(timeout=TIMEOUT_PADRAO_MS) as download_info:
                clicar_por_texto(page, "Download", TIMEOUT_PADRAO_MS)
            download = download_info.value

            carimbo = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            destino = COMPROVANTES_DIR / f"{carimbo}_{download.suggested_filename}"
            download.save_as(str(destino))
            log(f"Comprovante salvo em: {destino}")

            notificar("Ponto Certo", "Ponto batido e comprovante salvo com sucesso.")

        except PlaywrightTimeoutError as e:
            _salvar_screenshot_erro(page)
            log(f"ERRO (timeout): {e}")
            notificar(
                "Ponto Certo - ERRO",
                "Nao consegui bater o ponto a tempo. Confira o log.",
            )
        except Exception as e:  # noqa: BLE001 - queremos logar qualquer falha
            _salvar_screenshot_erro(page)
            log(f"ERRO inesperado: {e}")
            notificar("Ponto Certo - ERRO", "Falha ao bater o ponto. Confira o log.")
        finally:
            # Perfil persistente ja salva tudo em disco sozinho -
            # so precisa fechar.
            context.close()


def _salvar_screenshot_erro(page) -> None:
    try:
        page.screenshot(path=str(ERRO_SCREENSHOT))
        log(f"Screenshot do erro salvo em: {ERRO_SCREENSHOT}")
    except Exception as e:
        log(f"Nao consegui salvar screenshot do erro: {e}")


if __name__ == "__main__":
    bater_ponto()
    sys.exit(0)
