from app.gateways.s3_gateway import S3Gateway


class S3Model:
    def __init__(self, bucket_name: str = "products-s3bucket-mich-v2", region: str = "us-east-2"):
        self.s3_gateway = S3Gateway(bucket_name=bucket_name, region=region)

    def extract_details(self, event):
        return self.s3_gateway.extract_s3_details(event)

    def read_csv_from_event(self, event):
        bucket, key = self.extract_details(event)
        return self.s3_gateway.read_csv(bucket, key)
