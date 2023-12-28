import dotenv
import os
import requests


dotenv.load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

API_URL = os.getenv("API_URL")

ID_TOKEN = os.getenv("ACCESS_TOKEN")
if not ID_TOKEN:
    email = os.getenv("EMAIL")
    pwd = os.getenv("PASSWORD")
    try:
        resp = requests.post(f"{API_URL}/token", json={"email": email, "password": pwd})
        resp.raise_for_status()
    except:
        requests.post(f"{API_URL}/user", json={"email": email, "password": pwd, "groups": ["users"]})
        resp = requests.post(f"{API_URL}/token", json={"email": email, "password": pwd})
    ID_TOKEN = resp.json()["id_token"]

DEVICE = os.getenv("DEVICE")
ENVIRONMENT = os.getenv("ENVIRONMENT")
