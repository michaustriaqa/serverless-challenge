# from shared.gateways.dynamodb_gateway import DynamoDBGateway
# from shared.gateways.s3_gateway import S3Gateway
# from app.utils.common import validate_required_keys
# from boto3.dynamodb.conditions import Key  # Import Key for query expressions
# import string
# import random
# import csv
# import traceback
# import time
# import urllib
# from decimal import Decimal
# from datetime import datetime
# import json
# import boto3

# class ProductModel:
#     TABLE_NAME = "ProductsTable_mich"
#     REGION = "us-east-2"
#     S3_BUCKET_NAME = "products-s3bucket-mich-v2"

#     dynamodb = boto3.resource("dynamodb", region_name=REGION)
#     table = dynamodb.Table(TABLE_NAME)

#     class DecimalEncoder(json.JSONEncoder):
#         """
#         Custom JSON encoder to handle Decimal objects returned by DynamoDB.
#         Converts Decimal to string for JSON serialization.
#         """
#         def default(self, obj):
#             if isinstance(obj, Decimal):
#                 return str(obj)
#             return super(ProductModel.DecimalEncoder, self).default(obj)

#     @staticmethod
#     def generate_code(prefix, string_length):
#         letters = string.ascii_uppercase
#         return prefix + ''.join(random.choice(letters) for i in range(string_length))

#     @staticmethod
#     def create_product(event):
#         """
#         Creates a new product in the DynamoDB table and sends a message to the SQS queue.
#         :param event: The event containing the product data.
#         :return: A success message with the created product.
#         """
#         body = json.loads(event["body"], parse_float=Decimal)

#         # Insert the product into the DynamoDB table
#         ProductModel.table.put_item(Item=body)
#         print(f"Product inserted into DynamoDB: {body}")

#         # Send a message to the SQS queue
#         queue_name = 'products-queue-mich-sqs-v2'
#         sqs_response = ProductModel.send_message_to_sqs(queue_name, body)
#         print(f"Message sent to SQS: {sqs_response}")

#         return {"message": "Product created successfully", "item": body}

#     @staticmethod
#     def get_product(product_id):
#         """
#         Fetch a single product by its ID, including quantity, added stocks, and total stocks.
#         """
#         product_table = ProductModel.dynamodb.Table(ProductModel.TABLE_NAME)
#         inventory_table = ProductModel.dynamodb.Table("ProductInventory_mich")

#         try:
#             # Fetch product details from the product table
#             response = product_table.get_item(Key={"product_id": product_id})
#             item = response.get("Item")

#             if not item:
#                 return {"error": "Product not found"}

#             # Get the product's quantity from the product table
#             quantity = int(item.get("quantity", 0))  # Ensure it's an integer

#             # Sum inventory for this product from the inventory table
#             inventory_response = inventory_table.query(
#                 KeyConditionExpression=Key("product_id").eq(product_id)
#             )
#             inventory_items = inventory_response.get("Items", [])
#             added_stocks = sum(int(i.get("quantity", 0)) for i in inventory_items)  # Ensure integers

#             # Calculate total stocks (quantity + added_stocks)
#             total_stocks = quantity + added_stocks

#             # Add stock information to the product details
#             item["quantity"] = quantity
#             item["added_stocks"] = added_stocks
#             item["total_stocks"] = total_stocks

#             return item

#         except Exception as e:
#             print(f"Error fetching product: {e}")
#             raise

#     @staticmethod
#     def get_all_products(limit=10, offset=0):
#         """
#         Fetch all products with pagination support.
#         :param limit: Number of items to fetch.
#         :param offset: Number of items to skip.
#         :return: A dictionary containing the paginated products.
#         """
#         try:
#             # Scan the table to retrieve all items
#             response = ProductModel.table.scan()
#             items = response.get('Items', [])  # Extract the items from the response

#             # Apply pagination by slicing the items list based on offset and limit
#             paginated_items = items[offset:offset + limit]

#             # Return the paginated items along with metadata for pagination
#             return {
#                 "message": "Products retrieved successfully!",
#                 "items": paginated_items,
#                 "pagination": {
#                     "limit": limit,  # Number of items returned per page
#                     "offset": offset,  # Starting index of the current page
#                     "total_items": len(items)  # Total number of items in the table
#                 }
#             }
#         except Exception as e:
#             # Log and raise any exceptions that occur during the operation
#             print(f"Error in get_all_products: {e}")
#             raise

#     @staticmethod
#     def delete_product(product_id):
#         ProductModel.table.delete_item(Key={"product_id": product_id})
#         return {"message": f"Product '{product_id}' deleted"}

#     @staticmethod
#     def update_product(product_id, updates):
#         update_expr = "SET "
#         expr_attr_values = {}
#         expr_attr_names = {}

#         for key, value in updates.items():
#             update_expr += f"#{key} = :{key}, "
#             expr_attr_names[f"#{key}"] = key
#             expr_attr_values[f":{key}"] = value

#         update_expr = update_expr.rstrip(", ")

#         ProductModel.table.update_item(
#             Key={"product_id": product_id},
#             UpdateExpression=update_expr,
#             ExpressionAttributeNames=expr_attr_names,
#             ExpressionAttributeValues=expr_attr_values
#         )
#         return {"message": f"Product '{product_id}' updated", "item": updates}

#     @staticmethod
#     def batch_create_products(event):
#         bucket, key = S3Gateway.extract_s3_details(event)
#         rows = S3Gateway.read_csv(bucket, key)
#         for row in rows:
#             if validate_required_keys(row, ["product_id", "product_name", "price", "quantity"]):
#                 ProductModel.table.put_item(Item=row)

#     @staticmethod
#     def batch_delete_products(event):
#         bucket, key = S3Gateway.extract_s3_details(event)
#         rows = S3Gateway.read_csv(bucket, key)
#         for row in rows:
#             if validate_required_keys(row, ["product_id"]):
#                 ProductModel.table.delete_item(Key={"product_id": row["product_id"]})

#     @staticmethod
#     def add_stocks_to_product(product_id, quantity, remarks=""):
#         inventory_table = ProductModel.dynamodb.Table("ProductInventory_mich")
#         now = datetime.utcnow().isoformat()
#         item = {
#             "product_id": product_id,
#             "datetime": now,
#             "quantity": Decimal(str(quantity)),
#             "remarks": remarks
#         }
#         inventory_table.put_item(Item=item)
#         return {"message": "Stock added successfully", "item": item}

#     @staticmethod
#     def receive_message_from_sqs(event):
#         fieldnames = ["product_id", "product_name", "brand_name", "price", "quantity"]
#         file_randomized_prefix = ProductModel.generate_code("pycon_", 8)
#         file_name = f'/tmp/product_created_{file_randomized_prefix}.csv'
#         object_name = f'product_created_{file_randomized_prefix}.csv'

#         with open(file_name, 'w', newline='') as f:
#             writer = csv.DictWriter(f, fieldnames=fieldnames)
#             writer.writeheader()
#             for payload in event["Records"]:
#                 json_payload = json.loads(payload["body"])
#                 writer.writerow(json_payload)

#         s3_client = boto3.client('s3', region_name=ProductModel.REGION)
#         s3_client.upload_file(file_name, ProductModel.S3_BUCKET_NAME, object_name)
#         return {"message": "Messages processed successfully"}

#     @staticmethod
#     def send_message_to_sqs(queue_name, message_body):
#         """
#         Sends a message to the specified SQS queue.
#         :param queue_name: Name of the SQS queue.
#         :param message_body: The message body to send.
#         :return: Response from the SQS send_message operation.
#         """
#         try:
#             sqs = boto3.resource('sqs', region_name=ProductModel.REGION)
#             queue = sqs.get_queue_by_name(QueueName=queue_name)
#             response = queue.send_message(MessageBody=json.dumps(message_body, cls=ProductModel.DecimalEncoder))
#             return response
#         except Exception as e:
#             print(f"Error sending message to SQS: {e}")
#             raise