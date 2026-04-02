import os
import re

def find_duplicate_comments(root_dir):
    comment_patterns = [
        r'^\s*#',
        r'^\s*//',
        r'^\s*<!--',
        r'^\s*/\*'
    ]
    
    for subdir, _, files in os.walk(root_dir):
        if 'static' in subdir and 'lib' in subdir:
            continue
        for file in files:
            if file.endswith(('.py', '.html', '.css', '.js')):
                file_path = os.path.join(subdir, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                        for i in range(len(lines) - 1):
                            line1 = lines[i].strip()
                            line2 = lines[i+1].strip()
                            if line1 and line1 == line2:
                                for pattern in comment_patterns:
                                    if re.match(pattern, lines[i]):
                                        print(f"{file_path}:{i+1}: {line1}")
                                        break
                except Exception as e:
                    pass

if __name__ == "__main__":
    find_duplicate_comments('netbox_otnfaults')
