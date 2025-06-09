import boto3
from fastapi.responses import RedirectResponse
from json_loader import load_config

config = load_config()

def signup_user(username, password, email, family_name, given_name):
    client = boto3.client(
        'cognito-idp',
        aws_access_key_id=config['aws_access_key_id'],
        aws_secret_access_key=config['aws_secret_access_key'],
        aws_session_token=config.get('aws_session_token'),  # Optional
        region_name=config['region']
    )

    try:
        response = client.sign_up(
            ClientId=config['client_id'],
            Username=username,
            Password=password,
            UserAttributes=[
                {'Name': 'email', 'Value': email},
                {'Name': 'family_name', 'Value': family_name},
                {'Name': 'given_name', 'Value': given_name},
            ]
        )
        return RedirectResponse(url="/confirm-page", status_code=303)
    except Exception as e:
        return {"error": str(e)}
