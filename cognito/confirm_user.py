import boto3
from json_loader import load_config

config = load_config()

client = boto3.client(
    'cognito-idp',
    aws_access_key_id=config["aws_access_key_id"],
    aws_secret_access_key=config["aws_secret_access_key"],
    aws_session_token=config["aws_session_token"],
    region_name=config["region"]
)

def confirm_user():
    email = input("Enter email (used during signup): ")
    code = input("Enter the 6-digit confirmation code from your email: ")
    try:
        response = client.confirm_sign_up(
            ClientId=config["client_id"],
            Username=email,
            ConfirmationCode=code
        )
        print("✅ User confirmed successfully!")
    except Exception as e:
        print("❌ Error confirming user:", e)

if __name__ == "__main__":
    confirm_user()
