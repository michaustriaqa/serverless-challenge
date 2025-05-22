from app.models.product_model import ProductModel
from app.utils.logging_utils import log_event

def create_one_product(event, context):
    log_event(event)
    body = ProductModel.create_product(event)
    return {"statusCode": 200, "body": body}

def get_one_product(event, context):
    log_event(event)
    product_id = event["pathParameters"]["product_id"]
    body = ProductModel.get_product(product_id)
    return {"statusCode": 200, "body": body}

def batch_create_products(event, context):
    log_event(event)
    ProductModel.batch_create_products(event)
    return {"statusCode": 200, "body": "Batch creation completed successfully"}

def batch_delete_products(event, context):
    log_event(event)
    ProductModel.batch_delete_products(event)
    return {"statusCode": 200, "body": "Batch deletion completed successfully"}