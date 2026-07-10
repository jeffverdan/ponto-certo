# Ponto Certo — automação de ponto no Flit

Automatiza login, navegação e download do comprovante no Flit
(https://web2.flitapp.com.br/). **A verificação facial continua sendo
feita ao vivo, por você** — o script abre a câmera de verdade e espera
você aparecer na hora certa; ele não grava nem reproduz vídeos para
enganar essa etapa.

Roda de segunda a sexta, nos horários 09:00 / 12:00 / 13:00 / 18:00,
pulando sábados, domingos e feriados nacionais automaticamente.

## Como funciona

- `setup_login.py` — roda uma vez (ou sempre que quiser renovar a sessão
  na mão): abre o navegador e loga. Se existir um `.env` com
  `FLIT_CPF`/`FLIT_SENHA`, loga sozinho; senão, espera você logar
  manualmente. Salva a sessão na pasta `chrome_profile/` (um perfil de
  Chrome persistente, não só um arquivo de cookies — o Flit usa
  Firebase Auth, que guarda a sessão em IndexedDB, e um perfil completo
  é a forma confiável de preservar isso entre execuções).
- `bater_ponto.py` — roda nos 4 horários de ponto: abre o navegador
  usando o perfil salvo em `chrome_profile/` (já loga sozinho, sem
  precisar refazer login), concede permissão de câmera/localização
  automaticamente (sem popup), clica em "Marcar ponto", espera a
  validação facial ao vivo e o botão "Confirmar", confirma e baixa o
  comprovante em `comprovantes/`. Se a sessão tiver expirado e houver
  `.env` configurado, ele se reloga sozinho antes de continuar.
- `lembrete.py` — roda 5 minutos antes de cada horário: só manda uma
  notificação no Windows avisando pra você ficar por perto da câmera.
- `comum.py` — funções compartilhadas (checagem de dia útil/feriado,
  log, notificação).
- `instalar_tarefas.ps1` / `desinstalar_tarefas.ps1` — registram/removem
  as 8 tarefas no Agendador de Tarefas do Windows.

Todo log de execução vai para `bater_ponto.log`, nesta mesma pasta.

## Instalação

O uso normal é no Windows (é o que `instalar_tarefas.ps1` automatiza).
Os comandos de Linux/macOS abaixo servem caso você rode/teste isso numa
outra máquina — o agendamento nesse caso é feito com `cron` (passo 6c).

1. Instale o [Python 3.10+](https://www.python.org/downloads/).
   No Windows, marque "Add python.exe to PATH" no instalador.

2. Crie o ambiente virtual (`.venv`) nesta pasta — mantém as
   dependências isoladas do resto do sistema:

   **Windows (PowerShell)**
   ```
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   ```
   (Se der erro de permissão de execução de script, rode antes:
   `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`)

   **Linux / macOS (bash)**
   ```
   python3 -m venv .venv
   source .venv/bin/activate
   ```

   Repare no `(.venv)` que aparece no início da linha do terminal —
   é o sinal de que o ambiente está ativado. Sempre que for rodar algo
   manualmente nesta pasta (fora das tarefas agendadas), ative o `.venv`
   primeiro com o comando acima.

3. Com o `.venv` ativado, instale as dependências (comando igual nos
   dois sistemas):
   ```
   pip install -r requirements.txt
   playwright install chromium
   ```

4. (Opcional, mas recomendado) Configure o login automático: copie
   `.env.example` para `.env` e preencha com seu CPF e senha reais.
   ```
   FLIT_CPF=12345678900
   FLIT_SENHA=sua_senha_aqui
   ```
   Sem esse arquivo, o script pede pra você logar manualmente sempre
   que a sessão expirar (ver seção "Login automático" abaixo).

5. Faça o login inicial (janela do navegador vai abrir):

   **Windows**
   ```
   python setup_login.py
   ```

   **Linux / macOS**
   ```
   python3 setup_login.py
   ```

   Com `.env` configurado, ele loga sozinho. Sem `.env`, faça login com
   CPF + senha manualmente, espere carregar a tela "Olá, `<seu nome>`",
   volte no terminal e aperte ENTER.

6. Registre o agendamento:

   **6a. Windows — PowerShell.** Abra o PowerShell (não o Git
   Bash/MINGW), entre na pasta e rode direto (o script já aponta pro
   Python de dentro do `.venv` automaticamente):
   ```
   cd C:\repositorios\ponto-certo
   .\instalar_tarefas.ps1
   ```
   Para remover depois: `.\desinstalar_tarefas.ps1`

   **6b. Windows — Git Bash / MINGW64.** `.ps1` não roda direto no
   bash (por isso `.\instalar_tarefas.ps1` dá "command not found").
   Chame o PowerShell explicitamente:
   ```
   powershell -ExecutionPolicy Bypass -File instalar_tarefas.ps1
   ```
   Para remover depois:
   ```
   powershell -ExecutionPolicy Bypass -File desinstalar_tarefas.ps1
   ```

   **6c. Linux / macOS** — não há script pronto (o projeto foi feito
   pensando no Windows), mas dá pra registrar com `cron`. Rode
   `crontab -e` e adicione, trocando `/caminho/ponto-certo` pelo caminho
   real desta pasta:
   ```
   58 8  * * 1-5 cd /caminho/ponto-certo && .venv/bin/python lembrete.py
   0  9  * * 1-5 cd /caminho/ponto-certo && .venv/bin/python bater_ponto.py
   58 11 * * 1-5 cd /caminho/ponto-certo && .venv/bin/python lembrete.py
   0  12 * * 1-5 cd /caminho/ponto-certo && .venv/bin/python bater_ponto.py
   58 12 * * 1-5 cd /caminho/ponto-certo && .venv/bin/python lembrete.py
   0  13 * * 1-5 cd /caminho/ponto-certo && .venv/bin/python bater_ponto.py
   58 17 * * 1-5 cd /caminho/ponto-certo && .venv/bin/python lembrete.py
   0  18 * * 1-5 cd /caminho/ponto-certo && .venv/bin/python bater_ponto.py
   ```
   Precisa de um ambiente gráfico ativo (X11/Wayland) pra câmera e
   navegador abrirem — não funciona numa sessão SSH sem interface
   gráfica.

Pronto. Nos dias úteis, o navegador vai abrir sozinho nos 4 horários —
só fique por perto da câmera quando a notificação aparecer.

## Observações importantes

- **O PC precisa estar ligado e conectado** nos horários de ponto — o
  Agendador de Tarefas não liga o computador sozinho.
- A checagem de feriado usa só o **calendário nacional** brasileiro
  (conforme combinado). Se sua empresa também folga em feriados
  estaduais/municipais, me avise depois que eu ajusto.
- A localização é resolvida pelo próprio Chrome (sem coordenadas fixas
  configuradas), como você pediu.
- **O Flit é um app Flutter Web.** Por padrão ele desenha tudo em
  canvas (pixels), sem elementos HTML com texto/label de verdade — foi
  por isso que o login não funcionava antes. O script agora clica num
  botão invisível ("Enable accessibility") logo ao abrir a página, o
  que liga a árvore de acessibilidade real do Flutter (só aí os campos
  ganham `aria-label` e os botões ficam clicáveis por texto). Também
  não uso mais `fill()` nos campos — só teclado simulado de verdade
  (`press_sequentially`), porque `fill()` não funciona nesse app.
- Os `aria-label` dos campos foram confirmados ao vivo: CPF é
  `"CPF"`, senha é `"Informe sua senha"` (input `type="password"`). O
  código ainda mantém alguns nomes alternativos + um fallback genérico
  como rede de segurança, caso o Flit mude o texto no futuro.
- Os seletores de botão (`Marcar ponto`, `Confirmar`, `Download`) são
  baseados no texto visível na tela hoje. Se o Flit mudar o texto dos
  botões, o script vai falhar e registrar o erro em `bater_ponto.log` —
  me avise para eu ajustar.
- Se a sessão expirar: com `.env` configurado, `bater_ponto.py` se
  reloga sozinho e segue o fluxo normal. Sem `.env` (ou se a senha
  salva estiver desatualizada), ele avisa por notificação e você
  precisa rodar `python setup_login.py` de novo.
- **Se você já tinha rodado `setup_login.py` antes desta correção**,
  vai existir um `storage_state.json` antigo na pasta — pode ignorar/
  apagar, ele não é mais usado. Rode `python setup_login.py` de novo
  pra gerar a pasta `chrome_profile/` (é ela que o `bater_ponto.py`
  usa agora).
- Para desativar tudo: rode `.\desinstalar_tarefas.ps1`.

## Login automático (.env)

O `.env` guarda seu CPF e senha em **texto puro**, nesta pasta, para o
script conseguir se relogar sozinho quando a sessão cair. Alguns
cuidados:

- `.env` está no `.gitignore` — nunca vai parar num commit/repositório
  remoto sem querer.
- Qualquer pessoa com acesso a esta pasta no seu PC consegue ler sua
  senha em texto puro. Se essa máquina é compartilhada com outras
  pessoas, pense se vale a pena — nesse caso pode preferir pular o
  `.env` e continuar relogando manualmente (`python setup_login.py`)
  quando a sessão expirar.
- É opcional: sem `.env`, tudo funciona igual, só que o relogin em caso
  de sessão expirada é manual.
