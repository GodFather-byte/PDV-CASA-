import re

with open('src/ui/login.py', 'r', encoding='utf-8') as f:
    content = f.read()

import_licenca = 'from src.core.licenca import verificar_bloqueio, LicencaExpirada\n'
if import_licenca not in content:
    content = content.replace('from src.core.erros import ErroNegocio', import_licenca + 'from src.core.erros import ErroNegocio')

nova_entrar = '''    def entrar(self) -> None:
        try:
            verificar_bloqueio()
        except LicencaExpirada as e:
            self.lbl_msg.configure(text=str(e))
            self.lbl_msg.configure(fg="#ff4444")
            from tkinter import simpledialog
            from src.core.licenca import validar_e_salvar_licenca, LicencaInvalida
            token = simpledialog.askstring("Licença Expirada", "Sua licença acabou. Digite o código de renovação:", parent=self)
            if token:
                try:
                    validar_e_salvar_licenca(token)
                    self.lbl_msg.configure(text="Licença renovada! Tente logar novamente.", fg="#5be39a")
                except LicencaInvalida as err:
                    self.lbl_msg.configure(text=str(err), fg="#ff4444")
            return
            
        try:
            self.operador = self.ctx.acesso.autenticar(self.var_usuario.get(), self.var_senha.get())
        except ErroNegocio as e:
            self.lbl_msg.configure(text=str(e))
            self.var_senha.set("")
            self.ent_senha.focus_set()
            return
        self.destroy()'''

content = re.sub(r'    def entrar\(self\) -> None:.*?self\.destroy\(\)', nova_entrar, content, flags=re.DOTALL)

with open('src/ui/login.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Login UI com verificação de licença injetado!')
