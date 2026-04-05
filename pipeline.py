"""End-to-end orchestration script from document upload to Remotion render."""

from __future__ import annotations

import argparse
import json
import logging
import subprocess
import uuid
from pathlib import Path

import requests

DEFAULT_API_URL = "http://127.0.0.1:8001"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for input file path and generation settings."""

    parser = argparse.ArgumentParser(description="Document to whiteboard pipeline runner")
    parser.add_argument("--input", required=True, help="Path to source PDF/DOCX/TXT document")
    parser.add_argument("--max-scenes", type=int, default=12, help="Maximum number of scenes")
    parser.add_argument(
        "--run-id",
        default="",
        help="Optional run identifier used for render props and output artifact paths",
    )
    parser.add_argument(
        "--api-url",
        default=DEFAULT_API_URL,
        help="Base URL for backend API",
    )
    return parser.parse_args()


def upload_document(api_url: str, input_path: Path) -> dict:
    """Upload the source document and return extracted text metadata."""

    try:
        with input_path.open("rb") as handle:
            response = requests.post(
                f"{api_url}/upload",
                files={"file": (input_path.name, handle, "application/octet-stream")},
                timeout=180,
            )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        logger.exception("Upload request failed")
        raise RuntimeError(f"Upload endpoint failed: {exc}") from exc


def generate_render_props(api_url: str, extracted_text: str, max_scenes: int) -> dict:
    """Request scene generation and receive render props JSON payload."""

    payload = {
        "extracted_text": extracted_text,
        "max_scenes": max_scenes,
    }
    try:
        response = requests.post(f"{api_url}/generate", json=payload, timeout=900)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        logger.exception("Generate request failed")
        raise RuntimeError(f"Generate endpoint failed: {exc}") from exc


def write_render_props(project_root: Path, render_props: dict, run_id: str) -> Path:
    """Write run-scoped render props in renderer/runs and renderer/public/runs."""

    renderer_root = project_root / "renderer"
    renderer_runs = renderer_root / "runs" / run_id
    renderer_public_runs = renderer_root / "public" / "runs" / run_id
    renderer_runs.mkdir(parents=True, exist_ok=True)
    renderer_public_runs.mkdir(parents=True, exist_ok=True)

    run_props_path = renderer_runs / "render_props.json"
    public_props_path = renderer_public_runs / "render_props.json"

    serialized = json.dumps(render_props, indent=2)
    run_props_path.write_text(serialized, encoding="utf-8")
    public_props_path.write_text(serialized, encoding="utf-8")
    return run_props_path


def run_remotion_render(project_root: Path, props_path: Path, output_rel_path: str) -> None:
    """Execute Remotion render command using a run-scoped props file."""

    renderer_root = project_root / "renderer"
    try:
        props_arg = str(props_path.relative_to(renderer_root))
    except ValueError:
        props_arg = str(props_path)

    command = [
        "npx",
        "remotion",
        "render",
        "src/Root.tsx",
        "Whiteboard",
        f"--props={props_arg}",
        output_rel_path,
    ]
    try:
        subprocess.run(command, cwd=renderer_root, check=True)
    except subprocess.CalledProcessError as exc:
        logger.exception("Remotion render failed")
        raise RuntimeError(f"Remotion render command failed: {exc}") from exc


def main() -> None:
    """Run the full upload, generation, and video render orchestration."""

    args = parse_args()
    input_path = Path(args.input).expanduser().resolve()
    if not input_path.exists() or not input_path.is_file():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    project_root = Path(__file__).resolve().parent
    run_id = args.run_id.strip() or uuid.uuid4().hex
    output_rel_path = f"runs/{run_id}.mp4"

    print("[1/4] Uploading document and extracting text...")
    upload_result = upload_document(args.api_url, input_path)
    extracted_text = upload_result.get("extracted_text", "")
    chunk_count = upload_result.get("chunk_count", 0)
    print(f"      Extracted text received. Chunks: {chunk_count}")

    print("[2/4] Generating scene choreography via backend...")
    render_props = generate_render_props(args.api_url, extracted_text, args.max_scenes)
    scene_count = len(render_props.get("scenes", []))
    print(f"      Generation complete. Scenes: {scene_count}")

    print("[3/4] Writing run-scoped render props...")
    props_path = write_render_props(project_root, render_props, run_id=run_id)
    print(f"      Render props written to {props_path}")

    print("[4/4] Running Remotion render...")
    run_remotion_render(project_root, props_path=props_path, output_rel_path=output_rel_path)
    print(f"      Render complete: renderer/{output_rel_path}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        logger.exception("Pipeline execution failed")
        raise SystemExit(1) from exc
