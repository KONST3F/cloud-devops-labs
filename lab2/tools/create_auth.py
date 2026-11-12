from pathlib import Path
import subprocess

root = Path(__file__).resolve().parent.parent
settings = dict(line.split("=", 1) for line in (root / ".env").read_text(encoding="utf-8").splitlines() if "=" in line)
password = settings["ADMIN_PASSWORD"]
result = subprocess.run(["openssl", "passwd", "-apr1", "-stdin"], input=(password + "\n").encode("ascii"), capture_output=True, check=True)
(root / "auth" / "htpasswd").write_bytes(b"student:" + result.stdout.strip() + b"\n")
(root / "auth" / "curl.conf").write_text('user = "student:' + password + '"\n', encoding="ascii")
