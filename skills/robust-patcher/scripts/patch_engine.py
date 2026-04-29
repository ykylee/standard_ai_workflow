#!/usr/bin/env python3
import sys
import difflib
import argparse
from pathlib import Path

def fuzzy_find_block(source_lines, search_lines, threshold=0.8):
    """
    소스 코드에서 SEARCH 블록과 가장 유사한 지점을 찾습니다.
    """
    search_text = "".join(search_lines).strip()
    if not search_text:
        return -1, 0
    
    best_match_idx = -1
    best_ratio = 0
    search_len = len(search_lines)
    
    # 윈도우 슬라이딩 방식으로 최적의 매칭 지점 탐색
    for i in range(len(source_lines) - search_len + 1):
        window = "".join(source_lines[i:i+search_len]).strip()
        ratio = difflib.SequenceMatcher(None, search_text, window).ratio()
        
        if ratio > best_ratio:
            best_ratio = ratio
            best_match_idx = i
            
        if ratio == 1.0: # 완전 일치 시 조기 종료
            break
            
    if best_ratio >= threshold:
        return best_match_idx, search_len
    return -1, 0

def apply_patch(file_path, patch_content):
    """
    SEARCH/REPLACE 블록을 파싱하여 파일에 적용합니다.
    """
    path = Path(file_path)
    if not path.exists():
        return False, f"File not found: {file_path}"
    
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    
    # 파싱 상태 변수
    search_block = []
    replace_block = []
    state = "NONE" # NONE, SEARCH, REPLACE
    
    # 간단한 파서 구현 (단일 블록 우선 지원)
    for line in patch_content.splitlines(keepends=True):
        if line.startswith("<<<<<<< SEARCH"):
            state = "SEARCH"
            continue
        elif line.startswith("======="):
            state = "REPLACE"
            continue
        elif line.startswith(">>>>>>> REPLACE"):
            break
        
        if state == "SEARCH":
            search_block.append(line)
        elif state == "REPLACE":
            replace_block.append(line)
            
    if not search_block:
        return False, "No SEARCH block found in patch."

    start_idx, length = fuzzy_find_block(lines, search_block)
    
    if start_idx == -1:
        return False, "Could not find a reliable match for the SEARCH block."
    
    # 실제 교체 수행
    new_lines = lines[:start_idx] + replace_block + lines[start_idx+length:]
    
    # 문법 검사 (Python 파일인 경우)
    if path.suffix == ".py":
        try:
            compile("".join(new_lines), str(path), 'exec')
        except SyntaxError as e:
            return False, f"Patch would result in SyntaxError: {e}"
            
    path.write_text("".join(new_lines), encoding="utf-8")
    return True, f"Successfully applied patch at line {start_idx + 1}."

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True)
    parser.add_argument("--patch-file", required=True)
    args = parser.parse_args()
    
    patch_text = Path(args.patch_file).read_text(encoding="utf-8")
    success, message = apply_patch(args.file, patch_text)
    print(message)
    sys.exit(0 if success else 1)
