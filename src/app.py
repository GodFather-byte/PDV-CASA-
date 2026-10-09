"""Ponto de entrada do PDV: python -m src.app  (ou iniciar_pdv.bat no Windows).

Com `--sync` roda só a verificação de licença e de versão nova na nuvem (sem janela), a partir do mesmo programa:
python -m src.app --sync   ou   WillPDV.exe --sync

Com `--autoteste [arquivo] [--rede]` confere se o programa instalado está inteiro (ver src/autoteste.py) e encerra.
"""
import sys

if __name__ == "__main__":
    if "--autoteste" in sys.argv[1:]:
        from src.autoteste import executar
        resto = [a for a in sys.argv[1:] if not a.startswith("--")]
        sys.exit(executar(resto[0] if resto else None, rede="--rede" in sys.argv[1:]))
    if "--sync" in sys.argv[1:]:
        from src.sync.sincronizador import main as sincronizar
        sincronizar()
    else:
        from src.ui.app import main
        main()
