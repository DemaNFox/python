import os
from tqdm import tqdm

def load_ignore_list(ignore_file):
    """Загружает список исключений из файла .bundleignore"""
    ignore_list = set()
    if os.path.exists(ignore_file):
        with open(ignore_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):  # Игнорируем комментарии
                    ignore_list.add(line)
    return ignore_list

def should_ignore(path, ignore_list):
    """Проверяет, нужно ли игнорировать файл или папку"""
    for ignore in ignore_list:
        if ignore in path or path.endswith(ignore):
            return True
    return False

def get_unique_filename(directory, base_name="build.txt"):
    """Генерирует уникальное имя для файла, если такой уже существует"""
    base_path = os.path.join(directory, base_name)
    
    if not os.path.exists(base_path):
        return base_path  # Если файла нет, используем стандартное имя

    # Генерируем build_1.txt, build_2.txt и т. д.
    index = 1
    while True:
        new_filename = f"build_{index}.txt"
        new_path = os.path.join(directory, new_filename)
        if not os.path.exists(new_path):
            return new_path
        index += 1

def count_files(source_dir, ignore_list):
    """Подсчитывает количество файлов, которые будут обработаны (для прогресс-бара)"""
    total_files = 0
    for root, dirs, files in os.walk(source_dir):
        dirs[:] = [d for d in dirs if not should_ignore(os.path.join(root, d), ignore_list)]
        for file in files:
            file_path = os.path.join(root, file)
            if not should_ignore(file_path, ignore_list):
                total_files += 1
    return total_files

def bundle_files(source_dir):
    """Собирает все файлы в указанной директории в один текстовый файл"""
    ignore_list = load_ignore_list(os.path.join(source_dir, ".bundleignore"))

    # Определяем путь для сохранения файла (в папке со скриптом)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_file = get_unique_filename(script_dir)

    total_files = count_files(source_dir, ignore_list)

    with open(output_file, "w", encoding="utf-8") as bundle, tqdm(total=total_files, desc="📦 Объединение файлов", unit="файл") as pbar:
        for root, dirs, files in os.walk(source_dir):
            dirs[:] = [d for d in dirs if not should_ignore(os.path.join(root, d), ignore_list)]
            
            for file in files:
                file_path = os.path.join(root, file)
                if should_ignore(file_path, ignore_list):
                    continue

                # Делаем путь относительным к указанной папке
                relative_path = os.path.relpath(file_path, source_dir)

                bundle.write(f"\n\n=== НАЧАЛО ФАЙЛА: {relative_path} ===\n\n")
                
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        bundle.write(f.read())
                except Exception as e:
                    bundle.write(f"\n[Ошибка чтения файла: {e}]\n")

                bundle.write(f"\n\n=== КОНЕЦ ФАЙЛА: {relative_path} ===\n")
                pbar.update(1)

    print(f"\n✅ Файлы собраны в: {output_file}")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Собирает все файлы в папке в один текстовый файл.")
    parser.add_argument("source_dir", help="Папка, из которой собираем файлы")

    args = parser.parse_args()
    
    bundle_files(args.source_dir)
