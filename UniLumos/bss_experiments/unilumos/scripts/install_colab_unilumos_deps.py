#!/usr/bin/env python
"""Install UniLumos Colab dependencies.

This keeps the official requirements path for normal Colab GPUs. For Blackwell
GPUs such as RTX PRO 6000, use the PyTorch CUDA 12.8 wheels so CUDA kernels are
built for the newer architecture.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path


TASK_ROOT = Path(__file__).resolve().parents[3]
CODE_ROOT = TASK_ROOT / "UniLumos"
DEFAULT_REQUIREMENTS = CODE_ROOT / "requirements.txt"
PYTORCH_CU128_INDEX = "https://download.pytorch.org/whl/cu128"
TORCH_PACKAGE_NAMES = {"torch", "torchvision", "torchaudio"}
TORCH_CU128_PACKAGES = [
    "torch==2.7.0+cu128",
    "torchvision==0.22.0+cu128",
    "torchaudio==2.7.0+cu128",
]


def run(cmd: list[str]) -> None:
    print("$", " ".join(str(part) for part in cmd), flush=True)
    subprocess.check_call(cmd)


def gpu_names() -> list[str]:
    try:
        proc = subprocess.run(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
            check=True,
            capture_output=True,
            text=True,
        )
    except Exception:
        return []
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def looks_like_blackwell(names: list[str]) -> bool:
    haystack = " ".join(names).lower()
    return "blackwell" in haystack or "rtx pro 6000" in haystack or "sm_120" in haystack


def package_name(requirement_line: str) -> str:
    stripped = requirement_line.strip()
    for sep in ("==", ">=", "<=", "~=", "!=", ">", "<"):
        if sep in stripped:
            return stripped.split(sep, 1)[0].strip().lower()
    return stripped.split("[", 1)[0].strip().lower()


def write_requirements_without_torch(requirements: Path) -> Path:
    source_lines = requirements.read_text(encoding="utf-8").splitlines()
    kept: list[str] = []
    skipped: list[str] = []
    for line in source_lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            kept.append(line)
            continue
        if package_name(stripped) in TORCH_PACKAGE_NAMES:
            skipped.append(stripped)
            continue
        kept.append(line)

    target = Path(tempfile.gettempdir()) / "unilumos_requirements_no_torch.txt"
    target.write_text("\n".join(kept).rstrip() + "\n", encoding="utf-8")
    if skipped:
        print("Filtered torch packages from requirements:", ", ".join(skipped), flush=True)
    return target


def install_requirements(requirements: Path) -> None:
    run([sys.executable, "-m", "pip", "install", "--no-cache-dir", "-r", str(requirements)])


def install_cu128_torch_stack() -> None:
    run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--no-cache-dir",
            "--upgrade",
            "--force-reinstall",
            *TORCH_CU128_PACKAGES,
            "--index-url",
            PYTORCH_CU128_INDEX,
        ]
    )


def verify_torch() -> None:
    code = """
import torch
print("torch", torch.__version__)
print("torch_cuda", torch.version.cuda)
print("cuda_available", torch.cuda.is_available())
if torch.cuda.is_available():
    print("device", torch.cuda.get_device_name(0))
    print("capability", torch.cuda.get_device_capability(0))
    x = torch.ones((1,), device="cuda")
    torch.cuda.synchronize()
    print("cuda_tensor_ok", float(x.item()))
"""
    run([sys.executable, "-c", code])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--requirements", type=Path, default=DEFAULT_REQUIREMENTS)
    parser.add_argument(
        "--torch-mode",
        choices=("auto", "requirements", "cu128"),
        default="auto",
        help="auto uses cu128 only for detected Blackwell / RTX PRO 6000 GPUs.",
    )
    parser.add_argument("--skip-verify", action="store_true")
    args = parser.parse_args()

    names = gpu_names()
    print("Detected GPUs:", names or "none", flush=True)
    torch_mode = args.torch_mode
    if torch_mode == "auto":
        torch_mode = "cu128" if looks_like_blackwell(names) else "requirements"
    print("Torch install mode:", torch_mode, flush=True)

    if torch_mode == "cu128":
        filtered_requirements = write_requirements_without_torch(args.requirements)
        install_cu128_torch_stack()
        install_requirements(filtered_requirements)
    else:
        install_requirements(args.requirements)

    if not args.skip_verify:
        verify_torch()


if __name__ == "__main__":
    main()
