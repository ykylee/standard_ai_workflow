"""Go hub release assets used by the standard release pipeline."""

from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path

HUB_GO = Path(__file__).resolve().parents[3] / "hub-go"
GO_TARGETS = (
    ("linux", "amd64"),
    ("linux", "arm64"),
    ("darwin", "amd64"),
    ("darwin", "arm64"),
    ("windows", "amd64"),
    ("windows", "arm64"),
)


def planned_go_release_assets(out_dir: Path, version: str) -> list[Path]:
    """Return expected Go runtime asset paths; 2.x stays Python-only."""
    try:
        major = int(version.split(".", 1)[0])
    except ValueError as exc:
        raise ValueError(f"invalid release version: {version}") from exc
    if major < 3:
        return []
    binaries = [
        out_dir / f"workflow-hub-{version}-{goos}-{goarch}{'.exe' if goos == 'windows' else ''}"
        for goos, goarch in GO_TARGETS
    ]
    return [*binaries, out_dir / "SHA256SUMS"]


def go_release_assets(out_dir: Path, version: str) -> list[Path]:
    """Return present Go runtime assets required by a 3.x release."""
    assets = planned_go_release_assets(out_dir, version)
    if not assets:
        return []
    missing = [path.name for path in assets if not path.is_file()]
    if missing:
        raise FileNotFoundError(
            "3.x release Go assets are missing; run `release-pipeline dist --apply`: "
            + ", ".join(missing)
        )
    expected = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in assets[:-1]}
    rows: dict[str, str] = {}
    for line in assets[-1].read_text(encoding="utf-8").splitlines():
        parts = line.split(maxsplit=1)
        if len(parts) != 2 or parts[1] in rows:
            raise ValueError("invalid Go SHA256SUMS format")
        rows[parts[1]] = parts[0]
    if rows != expected:
        raise ValueError("Go SHA256SUMS does not match the six release binaries")
    return assets


def build_go_release_assets(out_dir: Path, version: str, *, timeout: int = 180) -> dict[str, object]:
    """Cross-build the six supported targets and write a deterministic SHA256SUMS."""
    out_dir.mkdir(parents=True, exist_ok=True)
    built: list[Path] = []
    checksum_rows: list[str] = []
    env_base = os.environ.copy()
    env_base["GOTOOLCHAIN"] = "local"
    env_base["CGO_ENABLED"] = "0"
    for goos, goarch in GO_TARGETS:
        suffix = ".exe" if goos == "windows" else ""
        output = out_dir / f"workflow-hub-{version}-{goos}-{goarch}{suffix}"
        env = {**env_base, "GOOS": goos, "GOARCH": goarch}
        command = [
            "go", "build", "-trimpath", "-ldflags", f"-s -w -X main.version={version}",
            "-o", str(output), "./cmd/workflow-hub",
        ]
        proc = subprocess.run(
            command, cwd=str(HUB_GO), env=env, capture_output=True, text=True,
            timeout=timeout, encoding="utf-8", errors="replace",
        )
        if proc.returncode != 0 or not output.is_file():
            detail = (proc.stdout + proc.stderr).strip()[-1200:]
            raise RuntimeError(f"Go build failed for {goos}/{goarch}: {detail or 'binary missing'}")
        digest = hashlib.sha256(output.read_bytes()).hexdigest()
        checksum_rows.append(f"{digest}  {output.name}")
        built.append(output)
    sums = out_dir / "SHA256SUMS"
    sums.write_text("\n".join(checksum_rows) + "\n", encoding="utf-8", newline="\n")
    return {"built": [path.name for path in built], "checksums": sums.name}
