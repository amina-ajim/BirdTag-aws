import json

def load_config():
    with open('Client_ID.json') as file:
        return json.load(file)

