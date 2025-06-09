import boto3
from json_loader import load_config

config = load_config()

def signup(username, password, email, family_name, given_name):
    client = boto3.client(
        'cognito-idp',
        aws_access_key_id=config['aws_access_key_id'],
        aws_secret_access_key=config['aws_secret_access_key'],
        aws_session_token=config['aws_session_token'],  # Optional, if using temporary credentials
        region_name=config['region']
    )

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
    return response

if __name__ == "__main__":
    username = input("Enter username: ")
    password = input("Enter password: ")
    email = input("Enter email: ")
    family_name = input("Enter family name: ")
    given_name = input("Enter given name: ")
    try:
        result = signup(username, password, email, family_name, given_name)
        print("Signup successful! Please check your email for a verification code.")
        print(result)
    except Exception as e:
        print("Signup failed:", e)

