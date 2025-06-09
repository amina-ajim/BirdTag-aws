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
    Compute the Base64-encoded HMAC-SHA256 of (username + client_id) using client_secret.
    """
    msg    = username + CLIENT_ID
    digest = hmac.new(
        CLIENT_SECRET.encode("utf-8"),
        msg.encode("utf-8"),
        hashlib.sha256
    ).digest()
    return base64.b64encode(digest).decode()

# ─── Build the Cognito client ──────────────────────────────────────────────────
client = boto3.client(
    "cognito-idp",
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY,
    aws_session_token=AWS_SESSION,
    region_name=AWS_REGION
)

def confirm_user():
    email = input("Enter email (used during signup): ")
    code  = input("Enter the 6-digit confirmation code from your email: ")

    try:
        response = client.confirm_sign_up(
            ClientId=CLIENT_ID,
            SecretHash=get_secret_hash(email),
            Username=email,
            ConfirmationCode=code
        )
        print("User confirmed successfully!")
    except Exception as e:
        print("Error confirming user:", e)

if __name__ == "__main__":
    confirm_user()