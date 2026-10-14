"""Run from an activated Python venv after pip install -r requirements.txt and npm ci."""

import argparse
import os
import secrets
import subprocess
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--setup", action="store_true", help="Migrate the isolated demo DB; no customer DB touched"
    )
    args = parser.parse_args()
    state = ROOT / ".local-demo"
    state.mkdir(exist_ok=True)
    secret = state / "secret"
    if not secret.exists():
        secret.write_text(secrets.token_urlsafe(48))
        secret.chmod(0o600)
    env = {
        **os.environ,
        "DJANGO_SETTINGS_MODULE": "onlineshop.demo_settings",
        "DJANGO_SECRET_KEY": secret.read_text().strip(),
    }
    if args.setup:
        subprocess.run([sys.executable, "manage.py", "migrate", "--noinput"], cwd=ROOT, env=env, check=True)
        print("Demo database ready. Run createsuperuser with --settings=onlineshop.demo_settings if needed.")
        return
    stop = threading.Event()

    def maintenance():
        while not stop.wait(60):
            for command in ("expire_orders", "reconcile_payments"):
                subprocess.run([sys.executable, "manage.py", command], cwd=ROOT, env=env, check=False)

    # Next dev and Django without autoreload: memory coordination/cache have one process.
    frontend_env = {
        **os.environ,
        "APP_ORIGIN": "http://127.0.0.1:3000",
        "DJANGO_ORIGIN": "http://127.0.0.1:8000",
        "BFF_COOKIE_SECRET": secret.read_text().strip(),
        "BFF_COORDINATION": "memory",
        "BFF_REDIS_URL": "",
        "LOCAL_DEMO": "1",
        "NODE_ENV": "development",
    }
    children = []
    try:
        children.append(
            subprocess.Popen(
                [sys.executable, "manage.py", "runserver", "127.0.0.1:8000", "--noreload", "--nothreading"],
                cwd=ROOT,
                env=env,
            )
        )
        children.append(
            subprocess.Popen(
                ["npm.cmd" if os.name == "nt" else "npm", "run", "dev"],
                cwd=ROOT / "frontend",
                env=frontend_env,
            )
        )
        threading.Thread(target=maintenance, daemon=True).start()
        print("LOCAL DEMO: http://127.0.0.1:3000 — no real SMS or bank charges. Ctrl+C stops both servers.")
        while not stop.wait(1):
            if any(child.poll() is not None for child in children):
                raise RuntimeError("A demo server stopped; inspect its output above.")
    except KeyboardInterrupt:
        pass
    finally:
        stop.set()
        for child in children:
            if child.poll() is None:
                child.terminate()
        for child in children:
            try:
                child.wait(timeout=10)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()


if __name__ == "__main__":
    main()
