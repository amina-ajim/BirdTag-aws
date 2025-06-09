import hmac
import hashlib
import base64
import boto3
from json_loader import load_config

# ─── Load Cognito config ────────────────────────────────────────────────────────
CONFIG = load_config()
CLIENT_ID     = CONFIG["client_id"]
CLIENT_SECRET = CONFIG["client_secret"]
AWS_REGION    = CONFIG["region"]
AWS_ACCESS_KEY = CONFIG.get("aws_access_key_id")
AWS_SECRET_KEY = CONFIG.get("aws_secret_access_key")
AWS_SESSION    = CONFIG.get("aws_session_token", None)

def get_secret_hash(username: str) -> str:
    """
    Cognito requires:
      SECRET_HASH = Base64( HMAC_SHA256(client_secret, username + client_id) )
    """
    msg    = username + CLIENT_ID
    digest = hmac.new(
        CLIENT_SECRET.encode("utf-8"),
        msg.encode("utf-8"),
        hashlib.sha256
    ).digest()
    return base64.b64encode(digest).decode()

def login(username: str, password: str):
    client = boto3.client(
        "cognito-idp",
        aws_access_key_id=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY,
        aws_session_token=AWS_SESSION,
        region_name=AWS_REGION,
    )

    response = client.initiate_auth(
        ClientId=CLIENT_ID,
        AuthFlow="USER_PASSWORD_AUTH",
        AuthParameters={
            "USERNAME":    username,
            "PASSWORD":    password,
            "SECRET_HASH": get_secret_hash(username),
        },
    )
    return response

if __name__ == "__main__":
    username = input("Enter username: ")
    password = input("Enter password: ")
    try:
        result = login(username, password)
        print("Login successful!")
        print(result)
    except Exception as e:
        print("Login failed:", e)