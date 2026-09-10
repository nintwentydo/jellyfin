#!/usr/bin/env python3
"""Verify a native candidate image using disposable SQLite configuration."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import subprocess
import tempfile
import time
import urllib.request
import uuid


def docker(*arguments):
    result = subprocess.run(["docker", *arguments], capture_output=True, text=True, timeout=180)
    if result.returncode:
        raise RuntimeError(f"Docker {arguments[0]} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image")
    parser.add_argument("architecture", choices=("amd64", "arm64"))
    args = parser.parse_args()
    machine = {"amd64": "x86_64", "arm64": "aarch64"}[args.architecture]
    assert os.uname().sysname == "Linux" and os.uname().machine == machine, "Use a native Linux runner"
    inspected = json.loads(docker("image", "inspect", args.image))[0]
    assert inspected["Os"] == "linux" and inspected["Architecture"] == args.architecture
    server = Path(__file__).resolve().parent / "server"
    expected = {str(path.relative_to(server)): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in server.rglob("*") if path.is_file()}
    assert "jellyfin" in expected and "Jellyfin.Server.Implementations.dll" in expected
    container = "jf-core-smoke-" + uuid.uuid4().hex[:12]
    password = secrets.token_urlsafe(24)
    token = ""
    base = ""

    def base_url():
        binding = json.loads(docker("inspect", container))[0]["NetworkSettings"]["Ports"]["8096/tcp"][0]
        assert binding["HostIp"] == "127.0.0.1"
        return "http://127.0.0.1:" + binding["HostPort"]

    def api(method, path, body=None):
        authorization = 'MediaBrowser Client="Docker smoke", Device="CI", DeviceId="docker-smoke", Version="1.0"'
        if token:
            authorization += ', Token="' + token + '"'
        request = urllib.request.Request(base + path, method=method,
            data=json.dumps(body).encode() if body is not None else None,
            headers={"Authorization": authorization, "Content-Type": "application/json"})
        with urllib.request.urlopen(request, timeout=10) as response:
            payload = response.read()
            return json.loads(payload) if payload else None

    def wait_for_api(method, path, body=None):
        deadline = time.monotonic() + 180
        while True:
            try:
                return api(method, path, body)
            except OSError as error:
                if time.monotonic() >= deadline or docker("inspect", "--format", "{{.State.Running}}", container) != "true":
                    status = getattr(error, "code", type(error).__name__)
                    raise RuntimeError(f"Jellyfin did not become ready ({method} {path}: {status})") from None
                time.sleep(2)

    with tempfile.TemporaryDirectory(prefix=container) as temporary:
        directory = Path(temporary)
        for child in ("config", "cache"):
            (directory / child).mkdir()
        try:
            docker("run", "--detach", "--name", container,
                   "--user", f"{os.getuid()}:{os.getgid()}", "--publish", "127.0.0.1::8096",
                   "--volume", f"{directory}/config:/config", "--volume", f"{directory}/cache:/cache", args.image)
            base = base_url()
            # The temporary setup server exposes public info before the real API is ready.
            wait_for_api("GET", "/Startup/User")
            info = api("GET", "/System/Info/Public")
            assert info["Version"] == "12.0.0" and info["StartupWizardCompleted"] is False
            api("POST", "/Startup/User", {"Name": "docker-smoke", "Password": password})
            credentials = {"Username": "docker-smoke", "Pw": password}
            login = api("POST", "/Users/AuthenticateByName", credentials)
            token = login["AccessToken"]
            user_id = login["User"]["Id"]
            api("POST", "/Startup/Configuration", {"ServerName": "Docker smoke", "UICulture": "en-GB",
                "MetadataCountryCode": "AU", "PreferredMetadataLanguage": "en"})
            api("POST", "/Startup/Complete")
            with urllib.request.urlopen(base + "/web/index.html", timeout=10) as response:
                assert response.status == 200 and b"<html" in response.read().lower()
            output = docker("exec", container, "sh", "-c",
                "cd /jellyfin && find . -path ./jellyfin-web -prune -o -type f -exec sha256sum {} +")
            actual = {name.removeprefix("./"): digest for digest, name in
                      (line.split(maxsplit=1) for line in output.splitlines())}
            assert actual == expected, "Server files differ from the compiled payload"
            assert docker("exec", container, "uname", "-m") == machine
            assert docker("exec", container, "/usr/lib/jellyfin-ffmpeg/ffmpeg", "-version").startswith("ffmpeg version")
            docker("restart", container)
            base = base_url()
            token = ""
            login = wait_for_api("POST", "/Users/AuthenticateByName", credentials)
            token = login["AccessToken"]
            assert login["User"]["Id"] == user_id and api("GET", "/Users/Me")["Id"] == user_id
            assert api("GET", "/System/Info/Public")["StartupWizardCompleted"] is True
            print(json.dumps({"status": "passed", "architecture": args.architecture,
                "jellyfinVersion": info["Version"], "serverFilesVerified": len(expected),
                "authenticatedUserPersistedAfterRestart": True}))
        except Exception:
            logs = subprocess.run(["docker", "logs", "--tail", "80", container], capture_output=True, text=True, timeout=15)
            output = logs.stdout + logs.stderr
            for secret in (password, token):
                if secret:
                    output = output.replace(secret, "[redacted]")
            print(output)
            raise
        finally:
            subprocess.run(["docker", "rm", "--force", "--volumes", container],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)


if __name__ == "__main__":
    main()
