 import json
import boto3
from boto3.dynamodb.conditions import Key, Attr

# — your existing constants —
TAG_TABLE  = 'MediaTagIndex'
FILE_TABLE = 'MediaFiles'
BUCKET     = 'birdtaggroup153'
REGION     = 'us-east-1'

dynamo   = boto3.resource('dynamodb', region_name=REGION)
tag_tbl  = dynamo.Table(TAG_TABLE)
file_tbl = dynamo.Table(FILE_TABLE)

def handler(event, context):
    # 1) Parse incoming tags + optional counts
    #    Supports:
    #      GET  /?tag=crow
    #      GET  /?tag1=crow&count1=3&tag2=eagle
    #      POST {"tag":"crow"}
    #      POST {"tags":["crow","eagle"]}
    #      POST {"tags":[{"tag":"crow","count":2}, {"tag":"eagle"}]}
    reqs = []
    if event.get("httpMethod") == "GET":
        qs = event.get("queryStringParameters") or {}
        if "tag" in qs:
            reqs = [(qs["tag"], 1)]
        else:
            i = 1
            while f"tag{i}" in qs:
                tag   = qs[f"tag{i}"]
                count = int(qs.get(f"count{i}", 1))
                reqs.append((tag, count))
                i += 1

    else:
        body = json.loads(event.get("body") or "{}")
        if "tag" in body:
            reqs = [(body["tag"], 1)]
        elif "tags" in body:
            # handle list of strings
            if isinstance(body["tags"], list) and all(isinstance(t, str) for t in body["tags"]):
                reqs = [(t, 1) for t in body["tags"]]
            # handle list of {tag, count}
            else:
                for item in body["tags"]:
                    tag   = item["tag"]
                    count = int(item.get("count", 1))
                    reqs.append((tag, count))

    if not reqs:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "You must supply at least one tag"})
        }

    # 2) For each (tag, min_count) do a fast query on the GSI, then filter by count ≥ min_count
    sets = []
    for tag, minc in reqs:
        resp = tag_tbl.query(
            KeyConditionExpression=Key("tag").eq(tag),
            FilterExpression       = Attr("count").gte(minc),
            ProjectionExpression   = "file_id"
        )
        sets.append({item["file_id"] for item in resp["Items"]})

    # 3) Intersect all sets to enforce AND semantics
    valid_ids = set.intersection(*sets) if sets else set()

    # 4) Batch‐get metadata & build S3 URLs
    links = []
    if valid_ids:
        keys = [{"file_id": fid} for fid in valid_ids]
        resp = file_tbl.batch_get_item(
            RequestItems={ FILE_TABLE: {"Keys": keys} }
        )["Responses"][FILE_TABLE]

        for item in resp:
            media_type = item["mediaType"]
            # use thumbnail for images, fullKey for audio/video
            key = item["thumbKey"] if media_type == "image" else item["fullKey"]
            url = f"https://{BUCKET}.s3.{REGION}.amazonaws.com/{key}"
            links.append(url)

    # 5) Return
    return {
        "statusCode": 200,
        "headers": { "Content-Type": "application/json" },
        "body": json.dumps({ "links": links })
    }