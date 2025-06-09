import boto3
from json_loader import load_config
from fastapi.responses import RedirectResponse

config = load_config()

def confirm_signup(email, code):
    client = boto3.client(
        'cognito-idp',
        aws_access_key_id=config["aws_access_key_id"],
        aws_secret_access_key=config["aws_secret_access_key"],
        aws_session_token=config.get('aws_session_token'),
        region_name=config["region"]
    )

    try:
        response = client.confirm_sign_up(
            ClientId=config["client_id"],
            Username=email,
            ConfirmationCode=code
        )
        return RedirectResponse(url="/login-page", status_code=303)
    except Exception as e:
        return {"error": str(e)}
