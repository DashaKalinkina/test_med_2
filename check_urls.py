import os
import re


def check_files_for_pattern(directory, pattern):
    problematic_files = []

    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.html'):
                filepath = os.path.join(root, file)
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if re.search(pattern, content):
                        problematic_files.append(filepath)

    return problematic_files


# Проверяем использование views.
print("Поиск 'url_for(\"views.\"'...")
for file in check_files_for_pattern('templates', r'url_for\s*\(\s*[\'"]views\.'):
    print(f"  Найдено в: {file}")

# Проверяем использование login без auth.
print("\nПоиск 'url_for(\"login\"' без 'auth.'...")
for file in check_files_for_pattern('templates', r'url_for\s*\(\s*[\'"]login[\'"]'):
    print(f"  Найдено в: {file}")

# Проверяем использование register без auth.
print("\nПоиск 'url_for(\"register\"' без 'auth.'...")
for file in check_files_for_pattern('templates', r'url_for\s*\(\s*[\'"]register[\'"]'):
    print(f"  Найдено в: {file}")