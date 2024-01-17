import boto3
import dotenv
import os
import requests


dotenv.load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

API_URL = os.getenv("API_URL")

ID_TOKEN = os.getenv("ACCESS_TOKEN")
if not ID_TOKEN:
    email = os.getenv("EMAIL")
    pwd = os.getenv("PASSWORD")

    resp = requests.get(f"{API_URL}/access_info")
    resp.raise_for_status()
    access_info = resp.json()["cognito"]
    cognito_client = boto3.client("cognito-idp", region_name=access_info["region"])
    ID_TOKEN = cognito_client.initiate_auth(
        AuthFlow="USER_PASSWORD_AUTH",
        AuthParameters={"USERNAME": email, "PASSWORD": pwd},
        ClientId=access_info["client_id"],
    )["AuthenticationResult"]["IdToken"]

DEVICE = os.getenv("DEVICE")
ENVIRONMENT = os.getenv("ENVIRONMENT")
