import os
import subprocess

print("Iniciando build do PDV - WillCommerce...")

# Garante que o pyinstaller seja chamado via módulo python
comando = [
    "python", "-m", "PyInstaller",
    "--noconfirm",
    "--onedir",
    "--windowed", # Nao abre console CMD no fundo
    "--name", "WillPDV",
    "--icon", "NONE", # Depois podem adicionar um .ico
    "--add-data", "src/database/esquema.py;src/database", 
    "src/app.py" # Ponto de entrada
]

try:
    subprocess.run(comando, check=True)
    print("Build finalizado com sucesso! Executavel em ./dist/WillPDV/WillPDV.exe")
except subprocess.CalledProcessError as e:
    print(f"Erro no build: {e}")
