with open('src/hardware/dispositivos.py', 'r', encoding='utf-8') as f:
    content = f.read()

novo_balanca = '''class Balanca:
    def __init__(self, modelo: str = "Nenhuma", porta: str | None = None):
        self.modelo = modelo or "Nenhuma"
        self.porta = porta

    @property
    def configurada(self) -> bool:
        return self.modelo != "Nenhuma" and bool(self.porta)

    def ler_peso(self) -> float:
        """Peso em kg. Comunica via Serial com Toledo ou Filizola."""
        if not self.configurada:
            raise DispositivoIndisponivel("Balança não configurada ou sem porta COM definida.")
            
        import serial
        import time
        
        try:
            # Configuração padrão de porta serial para balanças BR (9600 ou 4800, 8, N, 1)
            # Para Toledo Prix 3 e Filizola CS
            with serial.Serial(self.porta, 9600, timeout=1) as ser:
                ser.flushInput()
                
                if 'filizola' in self.modelo.lower():
                    # Filizola responde ao ENQ (0x05)
                    ser.write(b'\\x05')
                    time.sleep(0.1)
                    
                # Lê os próximos 20 bytes (normalmente manda pacotes de 6 a 10 bytes)
                dado = ser.read(20)
                
                if not dado:
                    raise DispositivoIndisponivel("Balança não respondeu (timeout). Verifique o cabo.")
                    
                # Protocolo Toledo (STX + 5 ou 6 bytes + ETX) ou Filizola
                # Exemplo: b'\\x0201234\\x03'
                import re
                match = re.search(b'\\x02(\\d{5,6})\\x03', dado)
                if match:
                    peso_str = match.group(1).decode('ascii')
                    # Assume 3 casas decimais (gramas -> kg)
                    return int(peso_str) / 1000.0
                else:
                    raise DispositivoIndisponivel(f"Dados não reconhecidos no protocolo: {dado}")
                    
        except serial.SerialException as e:
            raise DispositivoIndisponivel(f"Erro na porta serial {self.porta}: {e}")
'''

# Use simple string replacement
start_idx = content.find('class Balanca:')
end_idx = content.find('class Gaveta:')

if start_idx != -1 and end_idx != -1:
    content = content[:start_idx] + novo_balanca + "\n\n" + content[end_idx:]
    with open('src/hardware/dispositivos.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('Hardware Balança serial atualizado!')
else:
    print('Indices não encontrados!')
