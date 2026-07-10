"""
Login inicial - roda uma unica vez (ou sempre que quiser renovar a sessao
na mao). Usa um perfil persistente do Chrome (pasta chrome_profile/) pra
guardar a sessao - cookies, localStorage E IndexedDB (o Flit usa
Firebase Auth, que guarda o login em IndexedDB; por isso nao usamos
mais storage_state.json, que so salva cookies+localStorage e nao
"colava" a sessao entre execucoes).

Se existir um arquivo .env com FLIT_CPF e FLIT_SENHA, o login e feito
sozinho. Sem .env, abre o navegador e espera voce logar manualmente.
"""

from playwright.sync_api import sync_playwright

from comum import (
    PROFILE_DIR,
    SESSAO_OK_MARKER,
    URL,
    aguardar_elemento_com_texto,
    carregar_credenciais,
    fazer_login,
    log,
)

ERRO_SCREENSHOT = PROFILE_DIR.parent / "erro_setup_login.png"


def main() -> None:
    credenciais = carregar_credenciais()
    PROFILE_DIR.mkdir(exist_ok=True)

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            headless=False,
            args=["--force-renderer-accessibility"],
        )
        page = context.pages[0] if context.pages else context.new_page()
        page.goto(URL)

        try:
            if credenciais:
                cpf, senha = credenciais
                print("Credenciais encontradas em .env - fazendo login automatico...")
                fazer_login(page, cpf, senha)
                aguardar_elemento_com_texto(page, "Marcar ponto", 20_000)
                print("Login automatico feito com sucesso.")
            else:
                print("=" * 60)
                print("Nenhum .env encontrado (ou incompleto).")
                print("Faca login manualmente na janela do navegador (CPF + senha).")
                print("Quando estiver na tela inicial do Flit (Ola, <seu nome>),")
                print("volte aqui no terminal e pressione ENTER.")
                print("=" * 60)
                input()
        except Exception as e:
            page.screenshot(path=str(ERRO_SCREENSHOT))
            log(f"ERRO no setup_login.py: {e}")
            print(f"\nDeu erro: {e}")
            print(f"Salvei um screenshot da tela em: {ERRO_SCREENSHOT}")
            print("Manda esse print pra eu conseguir ver exatamente onde travou.")
            context.close()
            raise

        SESSAO_OK_MARKER.write_text(
            "Login confirmado por setup_login.py.", encoding="utf-8"
        )
        print(f"Sessao salva no perfil: {PROFILE_DIR}")
        log("Sessao (re)gerada via setup_login.py.")
        context.close()


if __name__ == "__main__":
    main()
