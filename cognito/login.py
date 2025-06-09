import boto3
from json_loader import load_config

config = load_config()

def login(username, password):
    client = boto3.client(
        'cognito-idp',
        aws_access_key_id=config['aws_access_key_id'],
        aws_secret_access_key=config['aws_secret_access_key'],
        region_name=config['region']
    )

    response = client.initiate_auth(
        ClientId=config['client_id'],
        AuthFlow='USER_PASSWORD_AUTH',
        AuthParameters={
            'USERNAME': username,
            'PASSWORD': password
        }
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