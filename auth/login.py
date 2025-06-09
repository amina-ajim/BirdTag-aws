import boto3
from json_loader import load_config

config = load_config()

def login_user(username, password):
    client = boto3.client(
        'cognito-idp',
        aws_access_key_id=config['aws_access_key_id'],
        aws_secret_access_key=config['aws_secret_access_key'],
        region_name=config['region']
    )

    try:
        response = client.initiate_auth(
            ClientId=config['client_id'],
            AuthFlow='USER_PASSWORD_AUTH',
            AuthParameters={
                'USERNAME': username,
                'PASSWORD': password
            }
        )
        return {
            "message": "Login successful!",
            "id_token": response["AuthenticationResult"]["IdToken"],
            "access_token": response["AuthenticationResult"]["AccessToken"]
        }
    except Exception as e:
        return {"error": str(e)}
