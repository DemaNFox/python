import os
import argparse

def load_ignore_list(ignore_file):
    ignore_list = set()
    if os.path.exists(ignore_file):
        with open(ignore_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    ignore_list.add(line)
    ignore_list.add(".bundleignore")
    return ignore_list

def should_ignore(path, ignore_list):
    for ignore in ignore_list:
        if ignore in path or path.endswith(ignore):
            return True
    return False

def build_tree(root_path, ignore_list, prefix=""):
    try:
        entries = sorted(os.listdir(root_path))
    except PermissionError:
        return [prefix + "[Permission Denied]"]

    entries = [e for e in entries if not should_ignore(os.path.join(root_path, e), ignore_list)]
    tree_lines = []
    for index, entry in enumerate(entries):
        path = os.path.join(root_path, entry)
        connector = "└── " if index == len(entries) - 1 else "├── "
        display_name = entry + " [DIR]" if os.path.isdir(path) else entry
        tree_lines.append(prefix + connector + display_name)
        if os.path.isdir(path):
            extension = "    " if index == len(entries) - 1 else "│   "
            tree_lines.extend(build_tree(path, ignore_list, prefix + extension))
    return tree_lines

def save_structure(source_dir):
    ignore_file = os.path.join(source_dir, ".bundleignore")
    ignore_list = load_ignore_list(ignore_file)

    tree = [os.path.basename(os.path.abspath(source_dir)) or source_dir]
    tree.extend(build_tree(source_dir, ignore_list))

    output_file = os.path.join(os.getcwd(), "structure.txt")
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(tree))
    print(f"\n✅ Структура сохранена в: {output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Строит древовидную структуру проекта и сохраняет в файл.")
    parser.add_argument("source_dir", help="Путь к директории проекта")
    args = parser.parse_args()

    save_structure(args.source_dir)
