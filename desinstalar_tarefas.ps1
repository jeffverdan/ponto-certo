# Remove todas as tarefas do Ponto Certo do Agendador de Tarefas do Windows.

$Nomes = @(
    "PontoCerto_Lembrete_0858", "PontoCerto_Ponto_0900",
    "PontoCerto_Lembrete_1158", "PontoCerto_Ponto_1200",
    "PontoCerto_Lembrete_1258", "PontoCerto_Ponto_1300",
    "PontoCerto_Lembrete_1758", "PontoCerto_Ponto_1800"
)

foreach ($n in $Nomes) {
    schtasks /delete /tn $n /f 2>$null
    Write-Host "Removida: $n"
}
