#!/usr/bin/env python3
import sys
import difflib
import argparse
from pathlib import Path

def normalize_lines(lines):
    """빈 줄과 좌우 공백을 제거한 줄의 리스트를 반환합니다."""
    return [line.strip() for line in lines if line.strip()]

def fuzzy_find_block(source_lines, search_lines, threshold=0.8):
    """
    소스 코드에서 SEARCH 블록과 가장 유사한 지점을 동적으로 찾습니다.
    빈 줄과 들여쓰기를 무시(normalize)하여 비교합니다.
    """
    norm_search = normalize_lines(search_lines)
    if not norm_search:
        return -1, 0
    
    search_len = len(norm_search)
    
    valid_source_indices = []
    norm_source = []
    for i, line in enumerate(source_lines):
        if line.strip():
            norm_source.append(line.strip())
            valid_source_indices.append(i)
            
    if not norm_source:
        return -1, 0

    best_match_idx = -1
    best_length = 0
    best_ratio = 0
    
    # 윈도우 슬라이딩 (블록 크기에 약간의 변동 허용)
    for i in range(len(norm_source)):
        for size_diff in range(-2, 3):
            w_size = search_len + size_diff
            if w_size <= 0 or i + w_size > len(norm_source):
                continue
                
            window = norm_source[i:i+w_size]
            ratio = difflib.SequenceMatcher(None, window, norm_search).ratio()
            
            if ratio > best_ratio:
                best_ratio = ratio
                best_match_idx = valid_source_indices[i]
                end_idx = valid_source_indices[i + w_size - 1]
                best_length = end_idx - best_match_idx + 1
                
            if ratio == 1.0:
                break
        if best_ratio == 1.0:
            break
            
    if best_ratio >= threshold:
        return best_match_idx, best_length
    return -1, 0

def parse_patch(patch_content):
    """패치 내용에서 다중 SEARCH/REPLACE 블록을 파싱합니다."""
    blocks = []
    search_block = []
    replace_block = []
    state = "NONE"
    
    for line in patch_content.splitlines(keepends=True):
        if line.startswith("<<<<<<< SEARCH"):
            state = "SEARCH"
            search_block = []
            replace_block = []
            continue
        elif line.startswith("======="):
            if state == "SEARCH":
                state = "REPLACE"
            continue
        elif line.startswith(">>>>>>> REPLACE"):
            if state == "REPLACE":
                blocks.append({"search": search_block, "replace": replace_block})
            state = "NONE"
            continue
            
        if state == "SEARCH":
            search_block.append(line)
        elif state == "REPLACE":
            replace_block.append(line)
            
    return blocks

def apply_patch(file_path, patch_content):
    """
    SEARCH/REPLACE 블록들을 파싱하여 파일에 적용합니다.
    """
    path = Path(file_path)
    if not path.exists():
        return False, f"File not found: {file_path}"
    
    original_lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    lines = list(original_lines)
    
    blocks = parse_patch(patch_content)
    if not blocks:
        return False, "No valid SEARCH/REPLACE block found in patch."

    # 뒤에서부터 수정하면 인덱스 밀림 현상을 방지할 수 있지만,
    # 블록이 어떤 순서로 나타날지 모르므로 순차적으로 적용하되 안전하게 오프셋을 관리할 수 있음.
    # 단순화를 위해 블록별로 하나씩 적용하며 lines 배열 갱신.
    for i, block in enumerate(blocks):
        search_lines = block["search"]
        replace_lines = block["replace"]
        
        start_idx, length = fuzzy_find_block(lines, search_lines)
        if start_idx == -1:
            return False, f"Could not find a reliable match for SEARCH block #{i+1}."
            
        lines = lines[:start_idx] + replace_lines + lines[start_idx+length:]
    
    # 문법 검사 (Python 파일인 경우)
    if path.suffix == ".py":
        try:
            compile("".join(lines), str(path), 'exec')
        except SyntaxError as e:
            return False, f"Patch would result in SyntaxError: {e}"
            
    path.write_text("".join(lines), encoding="utf-8")
    return True, f"Successfully applied {len(blocks)} patch block(s)."

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True)
    parser.add_argument("--patch-file", required=True)
    args = parser.parse_args()
    
    patch_text = Path(args.patch_file).read_text(encoding="utf-8")
    success, message = apply_patch(args.file, patch_text)
    print(message)
    sys.exit(0 if success else 1)
