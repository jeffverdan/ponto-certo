# Registra as tarefas do Ponto Certo no Agendador de Tarefas do Windows.
# Rode este script uma vez, no PowerShell, dentro desta pasta (nao precisa ser admin).
#
# Cria 8 tarefas, de segunda a sexta:
#   08:55 lembrete | 09:00 bate ponto (entrada manha)
#   11:55 lembrete | 12:00 bate ponto (saida almoco)
#   12:55 lembrete | 13:00 bate ponto (volta almoco)
#   17:55 lembrete | 18:00 bate ponto (saida)
#
# Feriados/fins de semana sao ignorados automaticamente pelos proprios
# scripts (comum.py), entao pode deixar as tarefas rodando o ano todo.

$ErrorActionPreference = "Stop"

$ProjectDir = $PSScriptRoot

# Usa o Python de dentro do .venv (isolado do resto do sistema).
# Cai pro Python do PATH so se o .venv nao existir.
$VenvPythonw = Join-Path $ProjectDir ".venv\Scripts\pythonw.exe"
$VenvPython = Join-Path $ProjectDir ".venv\Scripts\python.exe"

if (Test-Path $VenvPythonw) {
    $PythonExe = $VenvPythonw
} elseif (Test-Path $VenvPython) {
    $PythonExe = $VenvPython
    Write-Warning "pythonw.exe nao encontrado no .venv, usando python.exe (pode piscar uma janela de console)."
} else {
    Write-Warning ".venv nao encontrado nesta pasta. Rode 'python -m venv .venv' e instale as dependencias antes."
    $PythonExe = (Get-Command pythonw.exe -ErrorAction SilentlyContinue).Source
    if (-not $PythonExe) {
        $PythonExe = (Get-Command python.exe -ErrorAction SilentlyContinue).Source
        if (-not $PythonExe) {
            throw "Python nao encontrado nem no .venv nem no PATH. Instale o Python e crie o .venv primeiro."
        }
    }
}

$Dias = "MON,TUE,WED,THU,FRI"

function Criar-Tarefa {
    param($Nome, $Script, $Horario)
    $Acao = "`"$PythonExe`" `"$ProjectDir\$Script`""
    schtasks /create /tn "PontoCerto_$Nome" /tr $Acao /sc weekly /d $Dias /st $Horario /f | Out-Null
    Write-Host "Tarefa criada: PontoCerto_$Nome ($Horario)"
}

Criar-Tarefa "Lembrete_0858" "lembrete.py"    "08:58"
Criar-Tarefa "Ponto_0900"    "bater_ponto.py" "09:00"
Criar-Tarefa "Lembrete_1158" "lembrete.py"    "11:58"
Criar-Tarefa "Ponto_1200"    "bater_ponto.py" "12:00"
Criar-Tarefa "Lembrete_1258" "lembrete.py"    "12:58"
Criar-Tarefa "Ponto_1300"    "bater_ponto.py" "13:00"
Criar-Tarefa "Lembrete_1758" "lembrete.py"    "17:58"
Criar-Tarefa "Ponto_1800"    "bater_ponto.py" "18:00"

Write-Host ""
Write-Host "Pronto! 8 tarefas criadas (4 lembretes + 4 pontos), segunda a sexta."
Write-Host "Para conferir: abra o 'Agendador de Tarefas' do Windows e procure por 'PontoCerto_'."
Write-Host "Para remover tudo depois: .\desinstalar_tarefas.ps1"
