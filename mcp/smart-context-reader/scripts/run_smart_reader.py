#!/usr/bin/env python3
import ast
import sys
import argparse
from pathlib import Path

def extract_symbols(file_path, symbol_names):
    """
    Python 파일에서 특정 함수나 클래스의 코드 블록을 추출합니다.
    """
    path = Path(file_path)
    if not path.exists() or path.suffix != ".py":
        return f"Error: Only Python files are supported. File: {file_path}"
    
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    lines = source.splitlines()
    
    found_content = []
    
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)):
            if node.name in symbol_names or not symbol_names:
                # 노드의 시작과 끝 줄 번호를 사용하여 텍스트 추출
                start = node.lineno - 1
                end = node.end_lineno
                content = "\n".join(lines[start:end])
                found_content.append(f"--- Symbol: {node.name} ({type(node).__name__}) ---\n{content}\n")
                
    if not found_content:
        return f"No matching symbols found for: {', '.join(symbol_names)}"
        
    return "\n".join(found_content)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True)
    parser.add_argument("--symbols", nargs="*", help="List of function or class names to extract")
    args = parser.parse_args()
    
    result = extract_symbols(args.file, args.symbols)
    print(result)
