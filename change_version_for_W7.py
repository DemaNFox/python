import os
import subprocess

def switch_version(version):
    """Функция для переключения версий Python и активации соответствующего виртуального окружения"""
    
    if version == '3.8':
        # Переключение на Python 3.8
        os.system('pyenv global 3.8.10')
        print("Переключаемся на Python 3.8...")
        
        # Активация виртуального окружения для Python 3.8
        activate_venv('venv_py38')
    
    elif version == 'latest':
        # Переключение на последнюю версию Python
        os.system('pyenv global 3.12.0')
        print("Переключаемся на последнюю версию Python...")
        
        # Активация виртуального окружения для последней версии Python
        activate_venv('venv_py312')

def activate_venv(venv_name):
    """Функция для активации виртуального окружения"""
    
    venv_path = os.path.join(os.getcwd(), venv_name, 'Scripts', 'activate')
    
    if os.path.exists(venv_path):
        # Активация виртуального окружения
        subprocess.call(venv_path, shell=True)
        print(f"Активировано виртуальное окружение: {venv_name}")
    else:
        print(f"Виртуальное окружение {venv_name} не найдено.")

if __name__ == "__main__":
    # Пример использования скрипта
    print("Выберите версию Python: '3.8' или 'latest'")
    version = input("Введите версию: ").strip()
    
    if version in ['3.8', 'latest']:
        switch_version(version)
    else:
        print("Неверная версия Python.")
