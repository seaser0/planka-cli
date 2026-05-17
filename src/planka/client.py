import os
import subprocess
import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("PLANKA_URL")
USERNAME = os.getenv("PLANKA_USERNAME")

TOKEN_FILE = os.path.expanduser(os.getenv("PLANKA_TOKEN_FILE", "~/.planka_token"))


def _resolve_password():
    """Resolve password from one of three sources (in priority order):
    1. PLANKA_PASSWORD env var (direct, e.g. .env file)
    2. PLANKA_PASSWORD_FILE — read password from a file
    3. PLANKA_PASSWORD_CMD — execute shell command, capture stdout
    """
    pw = os.getenv("PLANKA_PASSWORD")
    if pw:
        return pw
    pw_file = os.getenv("PLANKA_PASSWORD_FILE")
    if pw_file:
        with open(os.path.expanduser(pw_file)) as f:
            return f.read().strip()
    pw_cmd = os.getenv("PLANKA_PASSWORD_CMD")
    if pw_cmd:
        result = subprocess.run(pw_cmd, shell=True, check=True,
                                capture_output=True, text=True)
        return result.stdout.strip()
    return None


class PlankaClient:
    def __init__(self):
        self.base_url = BASE_URL
        self.token = self._load_token()

    def _headers(self):
        return {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}

    def _load_token(self):
        if os.path.exists(TOKEN_FILE):
            with open(TOKEN_FILE) as f:
                return f.read().strip()
        return None

    def _save_token(self, token):
        with open(TOKEN_FILE, "w") as f:
            f.write(token)

    def login(self):
        password = _resolve_password()
        if not password:
            raise SystemExit(
                "No password source configured. Set one of:\n"
                "  PLANKA_PASSWORD=<pw>\n"
                "  PLANKA_PASSWORD_FILE=<path>\n"
                "  PLANKA_PASSWORD_CMD=<shell command that prints pw>"
            )
        url = f"{self.base_url}/api/access-tokens"
        payload = {"emailOrUsername": USERNAME, "password": password}
        r = requests.post(url, json=payload)
        r.raise_for_status()
        token = r.json()["item"]
        self._save_token(token)
        self.token = token

    def _check(self, r):
        if r.status_code == 401:
            self.login()
            return None
        r.raise_for_status()
        return r

    def get(self, endpoint):
        r = requests.get(f"{self.base_url}{endpoint}", headers=self._headers())
        if self._check(r) is None:
            r = requests.get(f"{self.base_url}{endpoint}", headers=self._headers())
            r.raise_for_status()
        return r.json()

    def post(self, endpoint, data):
        r = requests.post(f"{self.base_url}{endpoint}", headers=self._headers(), json=data)
        if self._check(r) is None:
            r = requests.post(f"{self.base_url}{endpoint}", headers=self._headers(), json=data)
            r.raise_for_status()
        return r.json()

    def patch(self, endpoint, data):
        r = requests.patch(f"{self.base_url}{endpoint}", headers=self._headers(), json=data)
        if self._check(r) is None:
            r = requests.patch(f"{self.base_url}{endpoint}", headers=self._headers(), json=data)
            r.raise_for_status()
        return r.json()

    def delete(self, endpoint):
        r = requests.delete(f"{self.base_url}{endpoint}", headers=self._headers())
        if self._check(r) is None:
            r = requests.delete(f"{self.base_url}{endpoint}", headers=self._headers())
            r.raise_for_status()
        return r.json()
