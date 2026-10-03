import os

def rename_in_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        new_content = content
        new_content = new_content.replace('WillCommerce', 'WillCommerce')
        new_content = new_content.replace('WILLCOMMERCE', 'WILLCOMMERCE')
        new_content = new_content.replace('willcommerce', 'willcommerce')
        new_content = new_content.replace('WillCommerce', 'WillCommerce')
        new_content = new_content.replace('WILLCOMMERCE', 'WILLCOMMERCE')
        new_content = new_content.replace('Willyan', 'Willyan')
        new_content = new_content.replace('Willyan', 'Willyan')
        
        if new_content != content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"Atualizado: {filepath}")
    except Exception as e:
        # Ignore binary or permission errors
        pass

for root, dirs, files in os.walk('.'):
    # Skip .git and env dirs
    if '.git' in root or '__pycache__' in root or 'dist' in root or 'build' in root:
        continue
    for file in files:
        if file.endswith('.py') or file.endswith('.md') or file.endswith('.html'):
            filepath = os.path.join(root, file)
            rename_in_file(filepath)
            
print("Substituição concluída.")
