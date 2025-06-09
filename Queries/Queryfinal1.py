 import os, json
import boto3
from boto3.dynamodb.conditions import Key, Attr

# Environment variables set by your SAM template
TAG_TABLE  = 'MediaTagIndex'
FILE_TABLE = 'MediaFiles'
BUCKET     = 'birdtaggroup153'
REGION     = 'us-east-1'

dynamo   = boto3.resource('dynamodb')
tag_tbl  = dynamo.Table('MediaTagIndex')
file_tbl = dynamo.Table('MediaFiles')

def handler(event, context):
    # 1. Parse incoming tags+counts (GET or POST JSON)
    if event.get('httpMethod') == 'GET':
        qs = event.get('queryStringParameters') or {}
        reqs, i = [], 1
        while f"tag{i}" in qs:
            reqs.append((qs[f"tag{i}"], int(qs.get(f"count{i}",1))))
            i += 1
    else:
        body = event.get('body', {})
        reqs = [(t['tag'], int(t['count'])) for t in body.get('tags',[])]
    if not reqs:
        return {"statusCode":400,"body":json.dumps({"error":"no tags provided"})}

    # 2. For each tag, query MediaTagIndex for fileIds with count ≥ requested
    sets = []
    for tag, minc in reqs:
        resp = tag_tbl.scan(
            FilterExpression=Attr('tag').eq(tag) & Attr('count').gte(minc),
            ProjectionExpression='file_id'
        )
        sets.append({item['file_id'] for item in resp['Items']})

    # 3. Intersect all sets to enforce logical AND
    valid_ids = set.intersection(*sets) if sets else set()

    # 4. Batch‐get metadata & build S3 URLs
    links = []
    if valid_ids:
        keys = [{'file_id': {'S': fid}} for fid in valid_ids]
        resp = boto3.client('dynamodb').batch_get_item(
            RequestItems={ file_tbl.name: {'Keys': keys} }
        )['Responses'][file_tbl.name]
        for item in resp:
            typ = item['mediaType']['S']
            key = item['thumbKey']['S'] if typ == 'image' else item['fullKey']['S']
            url = f"https://{BUCKET}.s3.{REGION}.amazonaws.com/{key}"
            links.append(url)


    # 5. Return the list of URLs
    print("EVENT >>>", event)
    print("REQS >>>", reqs)
    print("SETS >>>", sets)
    print("VALID_IDS >>>", valid_ids)

    return {
      "statusCode":200,
      "headers":{"Content-Type":"application/json"},
      "body": json.dumps({"links":links})
    }