import json
import os
import boto3
import urllib.parse
import mimetypes

from ultralytics import YOLO
import supervision as sv
import cv2 as cv
import numpy as np
import matplotlib.pyplot as plt
import requests

# AWS clients
s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
# DynamoDB table name must be provided via environment
TABLE_NAME = os.environ['DDB_TABLE']
table = dynamodb.Table(TABLE_NAME)

# Path to the YOLO model
MODEL_PATH = './model.pt'

# ------------------- Image Prediction -------------------
# (unchanged original image_prediction)
def image_prediction(image_path, result_filename=None, save_dir="./image_prediction_results", confidence=0.5, model=MODEL_PATH):
    yolo = YOLO(model)
    class_dict = yolo.names
    img = cv.imread(image_path)
    if img is None:
        print("Couldn't load the image! Please check the image path.")
        return
    h, w = img.shape[:2]
    thickness = sv.calculate_optimal_line_thickness(resolution_wh=(w, h))
    text_scale = sv.calculate_optimal_text_scale(resolution_wh=(w, h))
    palette = sv.ColorPalette.from_matplotlib('magma', 10)
    box_annotator = sv.BoxAnnotator(thickness=thickness, color=palette)
    label_annotator = sv.LabelAnnotator(color=palette, text_scale=text_scale,
                                        text_thickness=thickness, text_position=sv.Position.TOP_LEFT)
    result = yolo(img)[0]
    detections = sv.Detections.from_ultralytics(result)
    if detections.class_id is not None:
        detections = detections[detections.confidence > confidence]
        labels = [f"{class_dict[int(cid)]} {conf*100:.2f}%" for cid, conf in zip(detections.class_id, detections.confidence)]
        box_annotator.annotate(img, detections=detections)
        label_annotator.annotate(img, detections=detections, labels=labels)
    if result_filename:
        os.makedirs(save_dir, exist_ok=True)
        save_path = os.path.join(save_dir, result_filename)
        try:
            cv.imwrite(save_path, img)
        except Exception as e:
            print(f"Error saving image: {e}")

# ------------------- Video Prediction -------------------
# (unchanged original video_prediction)
def video_prediction(video_path, result_filename=None, save_dir="./video_prediction_results", confidence=0.5, model=MODEL_PATH):
    try:
        video_info = sv.VideoInfo.from_video_path(video_path=video_path)
        w, h, fps = int(video_info.width), int(video_info.height), int(video_info.fps)
        thickness = sv.calculate_optimal_line_thickness(resolution_wh=video_info.resolution_wh)
        text_scale = sv.calculate_optimal_text_scale(resolution_wh=video_info.resolution_wh)
        box_annotator = sv.BoxAnnotator(thickness=thickness, color_lookup=sv.ColorLookup.TRACK)
        label_annotator = sv.LabelAnnotator(text_scale=text_scale, text_thickness=thickness,
                                            text_position=sv.Position.TOP_LEFT, color_lookup=sv.ColorLookup.TRACK)
        yolo = YOLO(model)
        tracker = sv.ByteTrack(frame_rate=fps)
        class_dict = yolo.names
        if result_filename:
            os.makedirs(save_dir, exist_ok=True)
            save_path = os.path.join(save_dir, result_filename)
            out = cv.VideoWriter(save_path, cv.VideoWriter_fourcc(*"XVID"), fps, (w, h))
        else:
            print("Result filename is required to save the video file.")
            return
        cap = cv.VideoCapture(video_path)
        if not cap.isOpened():
            raise RuntimeError("Couldn't open video file.")
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            result = yolo(frame)[0]
            detections = sv.Detections.from_ultralytics(result)
            detections = tracker.update_with_detections(detections=detections)
            if detections.confidence is not None:
                filtered = detections[detections.confidence > confidence]
                labels = [f"#{tid} {class_dict[int(cid)]} {conf*100:.2f}%" 
                          for tid, cid, conf in zip(filtered.tracker_id, filtered.class_id, filtered.confidence)]
                box_annotator.annotate(frame, detections=filtered)
                label_annotator.annotate(frame, detections=filtered, labels=labels)
            if result_filename:
                out.write(frame)
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        cap.release()
        if result_filename:
            out.release()

# ------------------- Tag Extraction -------------------
def detect_tags(image_path, confidence=0.5):
    yolo = YOLO(MODEL_PATH)
    class_dict = yolo.names
    img = cv.imread(image_path)
    if img is None:
        return [], {}
    result = yolo(img)[0]
    detections = sv.Detections.from_ultralytics(result)
    tags, counts = [], {}
    if detections.class_id is not None:
        filtered = detections[detections.confidence > confidence]
        for cid in filtered.class_id:
            label = class_dict[int(cid)]
            tags.append(label)
            counts[label] = counts.get(label, 0) + 1
    return tags, counts

# ------------------- Video Tag Extraction -------------------
def detect_video_tags(video_path, confidence=0.5):
    yolo = YOLO(MODEL_PATH)
    class_dict = yolo.names
    counts = {}
    tag_set = set()
    cap = cv.VideoCapture(video_path)
    if not cap.isOpened():
        return [], {}
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        result = yolo(frame)[0]
        detections = sv.Detections.from_ultralytics(result)
        if detections.class_id is not None:
            filtered = detections[detections.confidence > confidence]
            for cid in filtered.class_id:
                label = class_dict[int(cid)]
                tag_set.add(label)
                counts[label] = counts.get(label, 0) + 1
    cap.release()
    return list(tag_set), counts

# ------------------- Lambda Handler -------------------

def lambda_handler(event, context):
    record = event['Records'][0]
    bucket = record['s3']['bucket']['name']
    key = urllib.parse.unquote_plus(record['s3']['object']['key'])
    print(f"Triggered on s3://{bucket}/{key}")

    basename = os.path.basename(key)
    local_input = f"/tmp/{basename}"

    # Download file
    s3.download_file(bucket, key, local_input)

    mime, _ = mimetypes.guess_type(key)
    if not mime:
        return {'statusCode':400, 'body': json.dumps('Could not determine MIME type')}

    original_url = f"s3://{bucket}/{key}"
    # Prepare metadata
    tags, counts = [], {}
    annotated_url = None

    if mime.startswith('image/'):
        annotated_name = f"annotated_{basename}"
        local_annotated = f"/tmp/{annotated_name}"
        image_prediction(local_input, result_filename=annotated_name, save_dir='/tmp')
        s3.upload_file(local_annotated, bucket, f"results/{annotated_name}")
        annotated_url = f"s3://{bucket}/results/{annotated_name}"
        tags, counts = detect_tags(local_input)

    elif mime.startswith('video/'):
        annotated_name = f"annotated_{basename}"
        local_annotated = f"/tmp/{annotated_name}"
        video_prediction(local_input, result_filename=annotated_name, save_dir='/tmp')
        s3.upload_file(local_annotated, bucket, f"results/{annotated_name}")
        annotated_url = f"s3://{bucket}/results/{annotated_name}"
        tags, counts = detect_video_tags(local_input)

    elif mime.startswith('audio/'):
        # Audio tagging via BirdNET-Analyzer
        from birdnet_analyzer import analyze as analyze_audio
        # Output CSV table
        local_table = f"/tmp/{basename}.csv"
        os.makedirs(os.path.dirname(local_table), exist_ok=True)
        analyze_audio(input=local_input, output=local_table)
        # Parse CSV for tags and counts
        import csv
        with open(local_table, newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                species = row.get('common_name') or row.get('species')
                if not species:
                    continue
                tags.append(species)
                counts[species] = counts.get(species, 0) + 1
        # Upload CSV
        table_key = f"results/{basename}.csv"
        s3.upload_file(local_table, bucket, table_key)
        annotated_url = f"s3://{bucket}/{table_key}"

    else:
        return {'statusCode':400, 'body': json.dumps('Unsupported file type')}

    # Write to DynamoDB
    item = {
        'FileKey': key,
        'FileType': mime,
        'OriginalURL': original_url,
        'AnnotatedURL': annotated_url,
        'Tags': tags,
        'TagCounts': counts
    }
    table.put_item(Item=item)

    return {'statusCode':200, 'body': json.dumps(item)}
