from __future__ import annotations

import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def request(url: str, payload: dict | None = None) -> dict:
    if payload is None:
        with urllib.request.urlopen(url, timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    proc = subprocess.Popen([sys.executable, "server.py"], cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        base = "http://127.0.0.1:8784"
        for _ in range(30):
            try:
                urllib.request.urlopen(base, timeout=2).read()
                break
            except Exception:
                time.sleep(0.2)
        sample = request(base + "/api/sample")
        assert len(sample["disputes"]) >= 20
        parsed = request(base + "/api/parse-text", {"text": (ROOT / "samples" / "pasted_dispute_examples.txt").read_text(encoding="utf-8")})
        assert parsed["dispute"]["amount"] > 0
        report = request(base + "/api/analyze", {"disputes": sample["disputes"] + [parsed["dispute"]], "scenario": {"deadline_buffer_days": 2}})
        assert report["summary"]["dispute_count"] >= 21
        assert "markdown_report" in report
        assert Path(report["saved_outputs"]["markdown"]).exists()
        print("Smoke test passed: app starts, sample loads, text parser works, report saved.")
        return 0
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == "__main__":
    raise SystemExit(main())

