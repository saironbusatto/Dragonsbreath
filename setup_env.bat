@echo off
echo Configurando variáveis de ambiente para Dragon's Breath...

REM Carrega as variáveis do arquivo .env
for /f "tokens=1,2 delims==" %%a in (.env) do (
    if not "%%a"=="" if not "%%a"=="#" (
        set %%a=%%b
        echo Configurado: %%a
    )
)

echo.
echo Variáveis configuradas! Execute agora:
echo python game.py
pause