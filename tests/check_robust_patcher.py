#!/usr/bin/env python3
import os
import sys
import tempfile
import subprocess
from pathlib import Path

# 패치 엔진의 경로 설정
SCRIPT_DIR = Path(__file__).resolve().parent
PATCH_ENGINE = SCRIPT_DIR.parent / "skills" / "robust-patcher" / "scripts" / "patch_engine.py"

def run_patch(target_file, patch_content):
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as patch_file:
        patch_file.write(patch_content)
        patch_path = patch_file.name

    try:
        result = subprocess.run(
            [sys.executable, str(PATCH_ENGINE), "--file", str(target_file), "--patch-file", patch_path],
            capture_output=True,
            text=True
        )
        return result.returncode == 0, result.stdout + result.stderr
    finally:
        os.remove(patch_path)

def test_exact_match():
    print("Running test_exact_match...")
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write("def hello():\n    print('world')\n")
        target_path = f.name
        
    patch = """<<<<<<< SEARCH
def hello():
    print('world')
=======
def hello():
    print('universe')
>>>>>>> REPLACE"""

    try:
        success, out = run_patch(target_path, patch)
        assert success, f"Exact match failed: {out}"
        content = Path(target_path).read_text()
        assert "universe" in content
        print("  - OK")
    finally:
        os.remove(target_path)

def test_fuzzy_match():
    print("Running test_fuzzy_match...")
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write("def calc():\n    a = 1\n    \n    b = 2\n    return a + b\n")
        target_path = f.name
        
    # 패치에 들여쓰기가 다르고, 빈 줄이 빠져 있음
    patch = """<<<<<<< SEARCH
def calc():
  a = 1
  b = 2
  return a + b
=======
def calc():
    a = 10
    b = 20
    return a + b
>>>>>>> REPLACE"""

    try:
        success, out = run_patch(target_path, patch)
        assert success, f"Fuzzy match failed: {out}"
        content = Path(target_path).read_text()
        assert "a = 10" in content
        assert "b = 20" in content
        print("  - OK")
    finally:
        os.remove(target_path)

def test_multi_block():
    print("Running test_multi_block...")
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write("def one():\n    return 1\n\ndef two():\n    return 2\n")
        target_path = f.name
        
    patch = """<<<<<<< SEARCH
def one():
    return 1
=======
def one():
    return 10
>>>>>>> REPLACE
<<<<<<< SEARCH
def two():
    return 2
=======
def two():
    return 20
>>>>>>> REPLACE"""

    try:
        success, out = run_patch(target_path, patch)
        assert success, f"Multi block failed: {out}"
        content = Path(target_path).read_text()
        assert "return 10" in content
        assert "return 20" in content
        print("  - OK")
    finally:
        os.remove(target_path)

def test_syntax_error():
    print("Running test_syntax_error...")
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write("def valid():\n    pass\n")
        target_path = f.name
        
    # 문법 오류 유발 (콜론 빠짐)
    patch = """<<<<<<< SEARCH
def valid():
    pass
=======
def valid()
    return True
>>>>>>> REPLACE"""

    try:
        success, out = run_patch(target_path, patch)
        assert not success, "Syntax error test should have failed."
        assert "SyntaxError" in out
        content = Path(target_path).read_text()
        assert "pass" in content # 원본 유지 확인
        print("  - OK")
    finally:
        os.remove(target_path)

if __name__ == "__main__":
    print("Starting robust-patcher tests...\n")
    test_exact_match()
    test_fuzzy_match()
    test_multi_block()
    test_syntax_error()
    print("\nAll tests passed successfully!")
