import os
import subprocess
import sys

# Функция для создания виртуального окружения и установки PyInstaller
def create_venv_and_install_pyinstaller(python_version, venv_name, pyinstaller_version=None):
    """Создает виртуальное окружение и устанавливает нужную версию PyInstaller"""
    
    # Установка выбранной версии Python с помощью pyenv
    subprocess.call(f'pyenv install -s {python_version}', shell=True)
    
    # Переключение на выбранную версию Python
    subprocess.call(f'pyenv global {python_version}', shell=True)
    
    # Путь к Python
    python_executable = subprocess.check_output('pyenv which python', shell=True).decode().strip()
    
    # Создание виртуального окружения
    print(f"Создаем виртуальное окружение {venv_name} для Python {python_version}...")
    subprocess.call(f'{python_executable} -m venv {venv_name}', shell=True)
    
    # Активация виртуального окружения
    activate_venv(venv_name)
    
    # Установка PyInstaller
    print(f"Устанавливаем PyInstaller {pyinstaller_version or 'latest'}...")
    install_pyinstaller(pyinstaller_version)
    
    print(f"Окружение {venv_name} и PyInstaller установлены.")

# Функция для активации виртуального окружения
def activate_venv(venv_name):
    """Активация виртуального окружения"""
    
    if sys.platform == "win32":
        activate_script = os.path.join(os.getcwd(), venv_name, 'Scripts', 'activate')
    else:
        activate_script = os.path.join(os.getcwd(), venv_name, 'bin', 'activate')
    
    # Выполнение команды для активации
    subprocess.call(activate_script, shell=True)
    print(f"Виртуальное окружение {venv_name} активировано.")

# Функция для установки PyInstaller
def install_pyinstaller(pyinstaller_version=None):
    """Устанавливает PyInstaller в зависимости от указанной версии"""
    if pyinstaller_version:
        subprocess.call(f'pip install pyinstaller=={pyinstaller_version}', shell=True)
    else:
        subprocess.call('pip install pyinstaller', shell=True)

# Основная функция для создания окружений для Python 3.8 и последней версии Python
def setup_env_for_project():
    # Установка окружения для Python 3.8 с PyInstaller 4.10
    create_venv_and_install_pyinstaller("3.8.10", "venv_py38", "4.10")
    
    # Установка окружения для последней версии Python с последней версией PyInstaller
    latest_python_version = subprocess.check_output('pyenv install --list | grep -Eo "^[[:space:]]*3\.[0-9]+\.[0-9]+$" | tail -1', shell=True).decode().strip()
    create_venv_and_install_pyinstaller(latest_python_version, "venv_latest")

if __name__ == "__main__":
    setup_env_for_project()
