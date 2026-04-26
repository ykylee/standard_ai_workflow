def infer_project_context(args: argparse.Namespace, paths: Paths) -> dict[str, object]:
    # Basic exploration for both "new" and "existing" modes
    docs_dirs = sorted(
        {
            name
            for name in ("docs", "doc", "wiki", "handbook")
            if (paths.target_root / name).exists()
        }
    )
    test_dirs = sorted(
        {
            name
            for name in ("tests", "test", "spec", "__tests__")
            if (paths.target_root / name).exists()
        }
    )
    source_dirs = sorted(
        {
            name
            for name in ("src", "app", "apps", "services", "packages", "lib")
            if (paths.target_root / name).exists()
        }
    )

    stack_labels: list[str] = []
    if (paths.target_root / "package.json").exists():
        stack_labels.append("node")
    if (paths.target_root / "pyproject.toml").exists() or (paths.target_root / "requirements.txt").exists():
        stack_labels.append("python")
    if (paths.target_root / "Cargo.toml").exists():
        stack_labels.append("rust")
    if (paths.target_root / "go.mod").exists():
        stack_labels.append("go")
    if (paths.target_root / "Gemfile").exists():
        stack_labels.append("ruby")
    primary_stack = stack_labels[0] if stack_labels else "unknown"

    package_scripts = detect_package_scripts(paths.target_root)

    # Resolve paths: prefer CLI args if provided, then inferred, then defaults
    if args.doc_home and args.doc_home != "README.md":
        doc_home = args.doc_home
    elif docs_dirs and (paths.target_root / docs_dirs[0] / "README.md").exists():
        doc_home = f"{docs_dirs[0]}/README.md"
    else:
        doc_home = "README.md"

    # Resolve operations_dir
    if args.adoption_mode == "existing" and docs_dirs:
        operations_dir = f"{docs_dirs[0]}/operations/"
    else:
        operations_dir = args.operations_dir

    backlog_dir = f"{operations_dir.rstrip('/')}/backlog/"
    session_doc_path = f"{operations_dir.rstrip('/')}/session_handoff.md"
    environment_dir = f"{operations_dir.rstrip('/')}/environments/"

    # Initial commands from args
    install_command = args.install_command
    run_command = args.run_command
    quick_test_command = args.quick_test_command
    isolated_test_command = args.isolated_test_command
    smoke_check_command = args.smoke_check_command

    # Refine commands based on stack
    if primary_stack == "node":
        if not install_command: install_command = "npm install"
        if not run_command: run_command = guess_run_command(paths.target_root, package_scripts)
        if not quick_test_command:
            quick_test_command = "npm test" if "test" in package_scripts else ("npm run lint" if "lint" in package_scripts else "TODO: 빠른 테스트 명령 입력")
        if not isolated_test_command:
            isolated_test_command = "npm run test:unit" if "test:unit" in package_scripts else ("npm run test:ci" if "test:ci" in package_scripts else "TODO: 격리 테스트 명령 입력")
        if not smoke_check_command:
            smoke_check_command = "npm run test:smoke" if "test:smoke" in package_scripts else "TODO: 실행 확인 명령 입력"
    elif primary_stack == "python":
        if not install_command: 
            install_command = "pip install -r requirements.txt" if (paths.target_root / "requirements.txt").exists() else "pip install ."
        if not run_command: run_command = guess_run_command(paths.target_root, {})
        if not quick_test_command:
            quick_test_command = "pytest" if test_dirs else "TODO: 빠른 테스트 명령 입력"
        if not isolated_test_command:
            isolated_test_command = "pytest tests/unit" if (paths.target_root / "tests/unit").exists() else "TODO: 격리 테스트 명령 입력"
    elif primary_stack == "rust":
        if not install_command: install_command = "cargo fetch"
        if not run_command: run_command = "cargo run"
        if not quick_test_command: quick_test_command = "cargo test"
        if not isolated_test_command: isolated_test_command = "cargo test --lib"
    elif primary_stack == "go":
        if not install_command: install_command = "go mod download"
        if not run_command: run_command = "go run ./..."
        if not quick_test_command: quick_test_command = "go test ./..."
        if not isolated_test_command: isolated_test_command = "go test ./... -run TestSmoke"

    # Fallback for all stacks
    install_command = install_command or "TODO: 설치 명령 입력"
    run_command = run_command or "TODO: 로컬 실행 명령 입력"
    quick_test_command = quick_test_command or "TODO: 빠른 테스트 명령 입력"
    isolated_test_command = isolated_test_command or "TODO: 격리 테스트 명령 입력"
    smoke_check_command = smoke_check_command or "TODO: 실행 확인 명령 입력"

    top_level_entries = sorted(
        path.name for path in paths.target_root.iterdir() if path.name != args.kit_dir
    )

    if args.adoption_mode == "new":
        return {
            "top_level_entries": top_level_entries,
            "source_dirs": source_dirs,
            "docs_dirs": docs_dirs,
            "test_dirs": test_dirs,
            "stack_labels": stack_labels,
            "primary_stack": primary_stack,
            "package_scripts": package_scripts,
            "existing_docs_detected": bool(docs_dirs),
            "has_existing_tests": bool(test_dirs),
            "doc_home": doc_home,
            "operations_dir": operations_dir,
            "backlog_dir": backlog_dir,
            "session_doc_path": session_doc_path,
            "environment_dir": environment_dir,
            "install_command": install_command,
            "run_command": run_command,
            "quick_test_command": quick_test_command,
            "isolated_test_command": isolated_test_command,
            "smoke_check_command": smoke_check_command,
            "analysis_summary": [
                "신규 프로젝트 모드이지만 기본 구조 분석을 통해 명령어를 추론했다.",
                "필요한 경우 생성된 profile 문서에서 명령어를 추가로 보정할 수 있다.",
            ],
        }

    # "existing" mode additional info
    files = iter_repo_files(paths.target_root)
    rel_files = [path.relative_to(paths.target_root).as_posix() for path in files]
    
    analysis_summary = [
        f"상위 디렉터리 기준으로 `{', '.join(top_level_entries[:10])}` 구조를 확인했다." if top_level_entries else "상위 디렉터리 항목이 거의 비어 있다.",
        f"추정 기본 스택은 `{primary_stack}` 이며 감지된 스택 라벨은 `{', '.join(stack_labels) or '없음'}` 이다.",
        f"문서 디렉터리는 `{', '.join(docs_dirs) or '없음'}`, 테스트 디렉터리는 `{', '.join(test_dirs) or '없음'}` 으로 감지됐다.",
        f"package script 는 `{', '.join(sorted(package_scripts)[:8]) or '없음'}` 으로 확인됐다.",
    ]

    return {
        "top_level_entries": top_level_entries,
        "source_dirs": source_dirs,
        "docs_dirs": docs_dirs,
        "test_dirs": test_dirs,
        "stack_labels": stack_labels,
        "primary_stack": primary_stack,
        "package_scripts": package_scripts,
        "existing_docs_detected": bool(docs_dirs),
        "has_existing_tests": bool(test_dirs),
        "doc_home": doc_home,
        "operations_dir": operations_dir,
        "backlog_dir": backlog_dir,
        "session_doc_path": session_doc_path,
        "environment_dir": environment_dir,
        "install_command": install_command,
        "run_command": run_command,
        "quick_test_command": quick_test_command,
        "isolated_test_command": isolated_test_command,
        "smoke_check_command": smoke_check_command,
        "analysis_summary": analysis_summary,
        "sample_paths": rel_files[:20],
    }
