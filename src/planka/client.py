# Original aus dem Edit-Schritt
import os
import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("PLANKA_URL")
USERNAME = os.getenv("PLANKA_USERNAME")
PASSWORD = os.getenv("PLANKA_PASSWORD")

TOKEN_FILE = os.path.expanduser("~/.planka_token")

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
        url = f"{self.base_url}/api/access-tokens"
        payload = {"emailOrUsername": USERNAME, "password": PASSWORD}
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
