import boto3
import csv
import urllib.parse
import os

class S3Gateway:
    @staticmethod
    def extract_s3_details(event):
        try:
            bucket = event["Records"][0]["s3"]["bucket"]["name"]
            key = urllib.parse.unquote_plus(event["Records"][0]["s3"]["object"]["key"])
            return bucket, key
        except (KeyError, IndexError) as e:
            raise ValueError("Invalid S3 event structure") from e

    @staticmethod
    def read_csv(bucket, key):
        s3 = boto3.client("s3", region_name="us-east-2")
        local_filename = os.path.join("/tmp", os.path.basename(key))
        try:
            s3.download_file(bucket, key, local_filename)
            with open(local_filename, "r") as f:
                return list(csv.DictReader(f))
        except Exception as e:
            raise RuntimeError(f"Failed to read CSV from S3: {e}")