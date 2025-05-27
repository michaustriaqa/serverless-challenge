from app.models.product_model import ProductManager
from app.utils.logging_utils import log_event
import json
import traceback
from decimal import Decimal


class DecimalEncoder(json.JSONEncoder):
    """Helper class to convert Decimal to float for JSON serialization."""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)


product_manager = ProductManager()


def hello(event, context):
    log_event(event)
    return {
        "statusCode": 200,
        "body": json.dumps({"message": "Hello World! This is Michelle's first serverless challenge."})
    }


def create_one_product(event, context):
    log_event(event)
    try:
        product_data = json.loads(event["body"])
        result = product_manager.create_product(product_data)
        return {"statusCode": 200, "body": json.dumps(result, cls=DecimalEncoder)}
    except Exception as e:
        print(f"Error during product creation: {e}")
        traceback.print_exc()
        return {"statusCode": 500, "body": json.dumps({"error": "Failed to create product"})}


def get_one_product(event, context):
    log_event(event)
    product_id = event["pathParameters"]["product_id"]
    try:
        body = product_manager.get_product(product_id)
        status = 404 if "error" in body else 200
        return {"statusCode": status, "body": json.dumps(body, cls=DecimalEncoder)}
    except Exception as e:
        print(f"Error in get_one_product: {e}")
        return {"statusCode": 500, "body": json.dumps({"error": "Internal server error"})}


def get_all_products(event, context):
    log_event(event)
    query_params = event.get("queryStringParameters", {}) or {}
    limit = int(query_params.get("limit", 10))
    page = int(query_params.get("page", 1))
    offset = (page - 1) * limit

    try:
        body = product_manager.get_all_products(limit=limit, offset=offset)
        return {"statusCode": 200, "body": json.dumps(body, cls=DecimalEncoder)}
    except Exception as e:
        print(f"Error in get_all_products: {e}")
        return {"statusCode": 500, "body": json.dumps({"error": "Internal server error"})}


def delete_one_product(event, context):
    log_event(event)
    product_id = event["pathParameters"]["product_id"]
    try:
        # Optional: include body if you want to log what was deleted
        body = json.loads(event.get("body", "{}"))
        result = product_manager.delete_product(product_id, body)
        return {"statusCode": 200, "body": json.dumps(result, cls=DecimalEncoder)}
    except Exception as e:
        print(f"Error in delete_one_product: {e}")
        return {"statusCode": 500, "body": json.dumps({"error": "Failed to delete product"})}


def update_one_product(event, context):
    log_event(event)
    product_id = event["pathParameters"]["product_id"]
    try:
        updates = json.loads(event["body"])
        body = product_manager.update_product(product_id, updates)
        return {"statusCode": 200, "body": json.dumps(body, cls=DecimalEncoder)}
    except Exception as e:
        print(f"Error in update_one_product: {e}")
        return {"statusCode": 500, "body": json.dumps({"error": "Failed to update product"})}


def batch_create_products(event, context):
    log_event(event)
    try:
        product_manager.batch_create_products(event)
        return {"statusCode": 200, "body": json.dumps({"message": "Batch creation completed successfully"})}
    except Exception as e:
        print(f"Error in batch_create_products: {e}")
        return {"statusCode": 500, "body": json.dumps({"error": "Batch creation failed"})}


def batch_delete_products(event, context):
    log_event(event)
    try:
        product_manager.batch_delete_products(event)
        return {"statusCode": 200, "body": json.dumps({"message": "Batch deletion completed successfully"})}
    except Exception as e:
        print(f"Error in batch_delete_products: {e}")
        return {"statusCode": 500, "body": json.dumps({"error": "Batch deletion failed"})}


def add_stocks_to_product(event, context):
    log_event(event)
    product_id = event["pathParameters"]["product_id"]
    try:
        body = json.loads(event["body"])
        result = product_manager.add_inventory(product_id, body)
        return {"statusCode": 200, "body": json.dumps(result, cls=DecimalEncoder)}
    except Exception as e:
        print(f"Error in add_stocks_to_product: {e}")
        return {"statusCode": 500, "body": json.dumps({"error": "Failed to add inventory"})}


def receive_message_from_sqs(event, context):
    log_event(event)
    # Optional: if you decide to add SQS handling in ProductManager
    try:
        result = product_manager.receive_message_from_sqs(event)
        return {"statusCode": 200, "body": json.dumps(result, cls=DecimalEncoder)}
    except Exception as e:
        print(f"Error in receive_message_from_sqs: {e}")
        return {"statusCode": 500, "body": json.dumps({"error": "SQS processing failed"})}
