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
AWS_SESSION    = CONFIG.get("aws_session_token")

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

def signup(username: str, password: str, email: str, family_name: str, given_name: str):
    client = boto3.client(
        "cognito-idp",
        aws_access_key_id=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY,
        aws_session_token=AWS_SESSION,
        region_name=AWS_REGION,
    )

    response = client.sign_up(
        ClientId=CLIENT_ID,
        SecretHash=get_secret_hash(username),
        Username=username,
        Password=password,
        UserAttributes=[
            {"Name": "email",        "Value": email},
            {"Name": "family_name",  "Value": family_name},
            {"Name": "given_name",   "Value": given_name},
        ],
    )
    return response

if __name__ == "__main__":
    username    = input("Enter username: ")
    password    = input("Enter password: ")
    email       = input("Enter email: ")
    family_name = input("Enter family name: ")
    given_name  = input("Enter given name: ")
    try:
        result = signup(username, password, email, family_name, given_name)
        print("Signup successful! Please check your email for a verification code.")
        print(result)
    except Exception as e:
        print("Signup failed:", e)