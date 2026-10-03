import os
import subprocess

print("Iniciando build do PDV - Casa Verde...")

# Garante que o pyinstaller seja chamado via módulo python
comando = [
    "python", "-m", "PyInstaller",
    "--noconfirm",
    "--onedir",
    "--windowed", # Nao abre console CMD no fundo
    "--name", "PDV_CasaVerde",
    "--icon", "NONE", # Depois podem adicionar um .ico
    "--add-data", "src/database/esquema.py;src/database", 
    "src/app.py" # Ponto de entrada
]

try:
    subprocess.run(comando, check=True)
    print("Build finalizado com sucesso! Executavel em ./dist/PDV_CasaVerde/PDV_CasaVerde.exe")
except subprocess.CalledProcessError as e:
    print(f"Erro no build: {e}")
