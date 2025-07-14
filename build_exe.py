import os
import sys
import subprocess

# PyInstaller komutu ve parametreleri (onefile modu)
pyinstaller_cmd = [
    sys.executable, '-m', 'PyInstaller',
    '--noconfirm',
    '--onefile',
    '--windowed',
    '--name', 'FNSS',
    'src/main.py'
]

print('> FNSS için PyInstaller (onefile) build başlatılıyor...')

try:
    subprocess.run(pyinstaller_cmd, check=True)
    print('\n> Build tamamlandı! dist/FNSS.exe dosyasını kullanabilirsiniz.')
except subprocess.CalledProcessError as e:
    print(f'Build sırasında hata oluştu: {e}') 