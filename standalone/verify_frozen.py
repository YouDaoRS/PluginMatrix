"""Run one real verifier path through an already-built standalone executable."""
from __future__ import annotations

import argparse
import json
import os
import re
import socket
import subprocess
import time
import urllib.request
from urllib.parse import urlsplit
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def request_json(url: str, cookie: str, token: str, payload: dict | None = None) -> dict:
    headers = {"Cookie": cookie}
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        parsed = urlsplit(url)
        headers.update({"Content-Type": "application/json", "X-PluginMatrix-Token": token,
                        "Origin": f"{parsed.scheme}://{parsed.netloc}"})
    with urllib.request.urlopen(urllib.request.Request(url, data=data, headers=headers), timeout=5) as response:
        return json.load(response)


def verify_web(executable: Path, java: str, evidence: Path, jdk_dir: Path | None = None) -> dict:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    base = f"http://127.0.0.1:{port}"
    process = subprocess.Popen(
        [executable, "web", "--no-browser", "--port", str(port), "--state-dir", str(evidence / "web-state"),
         "--cache-dir", str(ROOT / ".pluginmatrix" / "cache")],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        deadline = time.monotonic() + 15
        while True:
            try:
                request = urllib.request.Request(base + "/")
                with urllib.request.urlopen(request, timeout=1) as response:
                    page = response.read().decode("utf-8")
                    cookie = response.headers["Set-Cookie"].split(";", 1)[0]
                token = re.search(r'name="pluginmatrix-token" content="([a-f0-9]+)"', page).group(1)
                break
            except OSError:
                if process.poll() is not None or time.monotonic() >= deadline:
                    stdout, stderr = process.communicate(timeout=2)
                    raise RuntimeError(f"frozen Web UI did not start:\n{stdout}\n{stderr}")
                time.sleep(0.1)
        payload = {
            "mode": "single",
            "plugin": str(ROOT / "ci-fixtures" / "PluginMatrixSmoke.jar"),
            "dependencies": [],
            "environments": [{"server": {"type": "paper", "version": "1.20.1", "build": 196}, "java": java}],
            "options": {"timeout": 120, "stability_window": 2, "max_parallel": 1},
            "behavior": {"schema": 1, "timeout": 10, "checks": [
                {"id": "settle", "type": "wait", "seconds": 1, "timeout": 5}
            ]},
        }
        if jdk_dir:
            payload.pop("mode")
            payload.update(schema=2, profile={"id": "standard", "revision": 1})
            payload["options"]["jdk_dir"] = str(jdk_dir)
            payload["environments"][0]["java"] = {"managed": java.removeprefix("managed:")}
            payload = {"configuration": payload}
            normalized = request_json(base + "/api/config/normalize", cookie, token, payload)
            assert normalized["configuration"]["profile"]["revision"] == 1
            profiles = request_json(base + "/api/profiles", cookie, token)
            assert len(profiles["profiles"]) == 4
            analysis = request_json(base + "/api/guided/analyze", cookie, token,
                                    {"plugin": str(ROOT / "ci-fixtures" / "PluginMatrixSmoke.jar")})
            assert analysis["valid"]
        job = request_json(base + "/api/jobs", cookie, token, payload)
        deadline = time.monotonic() + 180
        while job["status"] in {"queued", "running", "cancelling"}:
            if time.monotonic() >= deadline:
                raise RuntimeError("frozen Web UI job exceeded its verification deadline")
            time.sleep(0.25)
            job = request_json(base + f"/api/jobs/{job['id']}?after={job['next_event']}", cookie, token)
        environment = job.get("summary", {}).get("environments", [{}])[0]
        if (job["status"] != "completed" or environment.get("runtime_verdict") != "PASS"
                or environment.get("behavior", {}).get("verdict") != "PASS"
                or environment.get("verification_passed") is not True):
            raise RuntimeError(f"frozen Web UI did not return the application PASS: {job!r}")
        labels = {item["label"] for item in job.get("artifacts", [])}
        expected = ({"Matrix JSON report", "Matrix HTML report", "Environment 1 JSON report",
                     "Environment 1 server.log", "Environment 1 behavior runtime probe"} if jdk_dir else
                    {"JSON report", "HTML report", "server.log", "behavior runtime probe"})
        if labels != expected:
            raise RuntimeError(f"frozen Web UI artifact allowlist is incomplete: {sorted(labels)!r}")
        if jdk_dir:
            restored = request_json(base + f"/api/jobs/{job['id']}/restore", cookie, token, {})
            assert restored["configuration"]["environments"][0]["java"] == {"managed": java.removeprefix("managed:")}
            assert restored["configuration"]["behavior"]["checks"][0]["id"] == "settle"
            for artifact in job["artifacts"]:
                request = urllib.request.Request(base + artifact["url"], headers={"Cookie": cookie})
                with urllib.request.urlopen(request, timeout=10) as response:
                    assert response.status == 200
        return {"job": job["id"], "runtime_verdict": "PASS", "behavior_verdict": "PASS",
                "verification_passed": True, "artifacts": sorted(labels)}
    finally:
        if process.poll() is None:
            process.terminate()
        process.communicate(timeout=10)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", required=True, type=Path)
    parser.add_argument("--java", required=True)
    args = parser.parse_args(argv)
    executable_name = "pluginmatrix.exe" if os.name == "nt" else "pluginmatrix"
    bundle = args.bundle
    if not (bundle / executable_name).is_file():
        matches = [path for path in bundle.glob("pluginmatrix-*") if path.is_dir() and (path / executable_name).is_file()]
        if len(matches) != 1:
            raise SystemExit(f"expected one standalone bundle under {bundle}, found {len(matches)}")
        bundle = matches[0]
    executable = bundle / executable_name
    evidence = ROOT / ".pluginmatrix" / "standalone-gate"
    evidence.mkdir(parents=True, exist_ok=True)
    jdk_dir = evidence / "managed-jdks"
    def invoke_json(*arguments, timeout=700):
        completed = subprocess.run([str(executable), *arguments, "--json"], cwd=ROOT,
                                   capture_output=True, text=True, timeout=timeout)
        if completed.returncode:
            raise RuntimeError(f"frozen guided command failed: {arguments[0:2]}\n{completed.stdout}\n{completed.stderr}")
        return json.loads(completed.stdout)
    before = {key: os.environ.get(key) for key in ("PATH", "JAVA_HOME", "JDK_HOME")}
    preview = invoke_json("jdk", "preview", "--major", "17")
    (evidence / "jdk-preview.json").write_text(json.dumps(preview, indent=2), encoding="utf-8")
    installed = invoke_json("jdk", "install", "--major", "17", "--id", preview["package"]["id"],
                            "--directory", str(jdk_dir))
    (evidence / "jdk-install.json").write_text(json.dumps(installed, indent=2), encoding="utf-8")
    assert installed["integrity"] == "verified"
    verified = invoke_json("jdk", "verify", "--id", installed["id"], "--directory", str(jdk_dir))
    assert verified["major"] == 17 and verified["integrity"] == "verified"
    managed_java = "managed:" + installed["id"]
    report = evidence / "result.json"
    html = evidence / "result.html"
    behavior = evidence / "behavior.json"
    behavior.parent.mkdir(parents=True, exist_ok=True)
    behavior.write_text(json.dumps({"schema": 1, "timeout": 10, "checks": [
        {"id": "settle", "type": "wait", "seconds": 1, "timeout": 5}
    ]}), encoding="utf-8")
    command = [
        str(executable), "test",
        "--plugin", str(ROOT / "ci-fixtures" / "PluginMatrixSmoke.jar"),
        "--server", "paper", "--minecraft", "1.20.1", "--build", "196", "--java", managed_java,
        "--jdk-dir", str(jdk_dir), "--profile", "quick",
        "--timeout", "120", "--stability-window", "2",
        "--work-dir", str(evidence / "runs"), "--cache-dir", str(ROOT / ".pluginmatrix" / "cache"),
        "--report", str(report), "--html", str(html),
        "--behavior", str(behavior),
    ]
    completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=240)
    if completed.returncode != 0:
        raise SystemExit(f"frozen runtime verification failed ({completed.returncode}):\n{completed.stdout}\n{completed.stderr}")
    result = json.loads(report.read_text(encoding="utf-8"))
    if (result.get("runtime_verdict") != "PASS" or result.get("behavior", {}).get("verdict") != "PASS"
            or result.get("verification_passed") is not True or not result.get("metadata", {}).get("runtime_probe")):
        raise SystemExit(f"frozen result lacks PASS/probe evidence: {result.get('result')!r}")
    if not html.is_file() or not Path(result.get("log_path", "")).is_file():
        raise SystemExit("frozen runtime did not preserve HTML report and server.log")
    web = verify_web(executable, managed_java, evidence, jdk_dir)
    deleted = invoke_json("jdk", "remove", "--id", installed["id"], "--directory", str(jdk_dir))
    assert deleted["deleted"]
    assert invoke_json("jdk", "list", "--directory", str(jdk_dir))["jdks"] == []
    assert before == {key: os.environ.get(key) for key in before}
    (evidence / "guided-summary.json").write_text(json.dumps({
        "jdk": installed, "deleted": deleted, "system_java_unchanged": True, "web": web,
        "runtime_verdict": result["runtime_verdict"], "behavior_verdict": result["behavior"]["verdict"]
    }, indent=2), encoding="utf-8")
    print(json.dumps({"runtime_verdict": result["runtime_verdict"], "behavior_verdict": result["behavior"]["verdict"],
                      "verification_passed": result["verification_passed"], "report": str(report), "html": str(html), "web": web}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
