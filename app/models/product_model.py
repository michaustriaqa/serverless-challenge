from shared.gateways.dynamodb_gateway import DynamoDBGateway
from shared.gateways.s3_gateway import S3Gateway
from app.utils.common import validate_required_keys

class ProductModel:
    TABLE_NAME = "ProductsTable_mich"

    @staticmethod
    def create_product(event):
        body = event["body"]
        DynamoDBGateway.put_item(ProductModel.TABLE_NAME, body)
        return {"message": "Product created successfully", "item": body}

    @staticmethod
    def get_product(product_id):
        product = DynamoDBGateway.get_item(ProductModel.TABLE_NAME, {"product_id": product_id})
        if not product:
            return {"error": "Product not found"}
        return product

    @staticmethod
    def batch_create_products(event):
        bucket, key = S3Gateway.extract_s3_details(event)
        rows = S3Gateway.read_csv(bucket, key)
        for row in rows:
            if validate_required_keys(row, ["product_id", "product_name", "price", "quantity"]):
                DynamoDBGateway.put_item(ProductModel.TABLE_NAME, row)

    @staticmethod
    def batch_delete_products(event):
        bucket, key = S3Gateway.extract_s3_details(event)
        rows = S3Gateway.read_csv(bucket, key)
        for row in rows:
            if validate_required_keys(row, ["product_id"]):
                DynamoDBGateway.delete_item(ProductModel.TABLE_NAME, {"product_id": row["product_id"]})