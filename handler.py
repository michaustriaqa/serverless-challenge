import string
import random
import csv
import traceback
import time
import urllib
from decimal import Decimal
from datetime import datetime
import json
import boto3
import codecs

# Configuration
TABLE_NAME = "ProductsTable_mich"
REGION = "us-east-2"
S3_BUCKET_NAME = "products-s3bucket-mich-v2"

# DynamoDB resource
dynamodb = boto3.resource("dynamodb", region_name=REGION)
table = dynamodb.Table(TABLE_NAME)

# Handle Decimal encoding for DynamoDB numbers
class DecimalEncoder(json.JSONEncoder):
    """
    Custom JSON encoder to handle Decimal objects returned by DynamoDB.
    Converts Decimal to string for JSON serialization.
    """
    def default(self, obj):
        if isinstance(obj, Decimal):
            return str(obj)
        return super(DecimalEncoder, self).default(obj)

# Generate a random code with a given prefix
def generate_code(prefix, string_length):
    """
    Generate a random code with a given prefix and string length.
    :param prefix: The prefix for the generated code.
    :param string_length: The length of the random string to append to the prefix.
    :return: A string with the prefix followed by a random uppercase string.
    """
    letters = string.ascii_uppercase
    return prefix + ''.join(random.choice(letters) for i in range(string_length))

# Hello handler
def hello(event, context):
    """
    Lambda function to return a simple greeting message.
    """
    print("EVENT:", event)

    body = {
        "message": "Hello World! This is Michelle's first serverless challenge.",
    }

    return {"statusCode": 200, "body": json.dumps(body)}

# Get all products
def get_all_products(event, context):
    """
    Lambda function to retrieve all products from the DynamoDB table.
    """
    print("EVENT:", event)

    try:
        response = table.scan()
        items = response.get('Items', [])

        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Products retrieved successfully!", "items": items}, cls=DecimalEncoder)
        }

    except dynamodb.meta.client.exceptions.ResourceNotFoundException as e:
        print(f"Error: {e}")
        return {"statusCode": 404, "body": json.dumps({"error": "Table not found"})}
    except Exception as e:
        print(f"Unhandled exception: {e}")
        traceback.print_exc()
        return {"statusCode": 500, "body": json.dumps({"error": "Internal server error"})}

# Create one product
def create_one_product(event, context):
    """
    Lambda function to create a new product in the DynamoDB table, send a message to SQS, and log the event in CloudWatch.
    """
    print("EVENT:", event)

    try:
        # Parse the request body to get product data
        body = json.loads(event["body"], parse_float=Decimal)

        # Insert the product into the DynamoDB table
        table.put_item(Item=body)
        print(f"Product inserted into DynamoDB: {body}")

        # Initialize SQS resource and get the queue
        sqs = boto3.resource('sqs', region_name=REGION)
        queue = sqs.get_queue_by_name(QueueName='products-queue-mich-sqs-v2')
        print(f"Queue URL: {queue.url}")

        # Send a message to the SQS queue
        sqs_response = queue.send_message(MessageBody=json.dumps(body, cls=DecimalEncoder))
        print(f"Message sent to SQS: {sqs_response}")

        # Initialize CloudWatch Logs client
        logs_client = boto3.client('logs', region_name=REGION)
        LOG_GROUP = "ProductsEventLogGroup_mich"
        LOG_STREAM = "ProductEventStream"

        # Create log stream if it doesn't exist
        try:
            logs_client.create_log_stream(logGroupName=LOG_GROUP, logStreamName=LOG_STREAM)
        except logs_client.exceptions.ResourceAlreadyExistsException:
            pass

        # Push event log to CloudWatch
        log_event = {
            "event": "product_created",
            "pid": body.get("product_id"),
            "data": body
        }

        logs_client.put_log_events(
            logGroupName=LOG_GROUP,
            logStreamName=LOG_STREAM,
            logEvents=[
                {
                    'timestamp': int(time.time() * 1000),
                    'message': json.dumps(log_event, cls=DecimalEncoder)
                }
            ]
        )
        print("Product creation event logged in CloudWatch.")

        # Return success response
        return {"statusCode": 200, "body": json.dumps({"message": "Product is created.", "item": body}, cls=DecimalEncoder)}

    except Exception as e:
        print(f"Error during product creation: {e}")
        traceback.print_exc()
        return {"statusCode": 500, "body": json.dumps({"error": "Failed to create product"})}

# Get one product by ID
def get_one_product(event, context):
    """
    Lambda function to retrieve a single product by its ID, including quantity, added stocks, and total stocks.
    """
    print("EVENT:", event)

    product_id = event["pathParameters"]["product_id"]

    dynamodb = boto3.resource("dynamodb", region_name="us-east-2")
    product_table = dynamodb.Table("ProductsTable_mich")
    inventory_table = dynamodb.Table("ProductInventory_mich")

    try:
        # Fetch product details from the product table
        response = product_table.get_item(Key={"product_id": product_id})
        item = response.get("Item")

        if not item:
            return {"statusCode": 404, "body": json.dumps({"error": "Product not found"})}

        # Get the product's quantity from the product table
        quantity = int(item.get("quantity", 0))  # Ensure it's an integer

        # Sum inventory for this product from the inventory table
        inventory_response = inventory_table.query(
            KeyConditionExpression=boto3.dynamodb.conditions.Key("product_id").eq(product_id)
        )
        inventory_items = inventory_response.get("Items", [])
        added_stocks = sum(int(i.get("quantity", 0)) for i in inventory_items)  # Ensure integers

        # Calculate total stocks (quantity + added_stocks)
        total_stocks = quantity + added_stocks

        # Add stock information to the product details
        item["quantity"] = quantity
        item["added_stocks"] = added_stocks
        item["total_stocks"] = total_stocks

        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Product is created.", "item": item}, cls=DecimalEncoder)
        }

    except Exception as e:
        print("Error:", e)
        traceback.print_exc()
        return {"statusCode": 500, "body": json.dumps({"error": "Failed to get product"})}

# Delete one product by ID
def delete_one_product(event, context):
    """
    Lambda function to delete a product by its ID from the DynamoDB table.
    """
    print("EVENT:", event)

    product_id = event["pathParameters"]["product_id"]

    try:
        table.delete_item(Key={"product_id": product_id})

        return {"statusCode": 200, "body": json.dumps({"message": f"Product '{product_id}' deleted"})}

    except Exception as e:
        print(f"Error: {e}")
        return {"statusCode": 500, "body": json.dumps({"error": "Failed to delete product"})}

# Update one product by ID
def update_one_product(event, context):
    """
    Lambda function to update a product's details by its ID in the DynamoDB table.
    """
    print("EVENT:", event)

    product_id = event["pathParameters"]["product_id"]
    updates = json.loads(event["body"], parse_float=Decimal)

    update_expr = "SET "
    expr_attr_values = {}
    expr_attr_names = {}

    for key, value in updates.items():
        update_expr += f"#{key} = :{key}, "
        expr_attr_names[f"#{key}"] = key
        expr_attr_values[f":{key}"] = value

    update_expr = update_expr.rstrip(", ")

    try:
        table.update_item(
            Key={"product_id": product_id},
            UpdateExpression=update_expr,
            ExpressionAttributeNames=expr_attr_names,
            ExpressionAttributeValues=expr_attr_values
        )

        return {"statusCode": 200, "body": json.dumps({"message": f"Product '{product_id}' updated", "item": updates}, cls=DecimalEncoder)}

    except Exception as e:
        print(f"Error: {e}")
        return {"statusCode": 500, "body": json.dumps({"error": "Failed to update product"})}

def batch_create_products(event, context):
    """
    Lambda function to process a CSV file uploaded to S3, parse its contents, 
    and insert the data into a DynamoDB table.
    """
    print("File uploaded trigger")
    print("Event:", event)  # Log the event for debugging

    try:
        # Extract file location from event payload
        print("Extract file location from event payload")
        bucket = event['Records'][0]['s3']['bucket']['name']
        key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'])
        file_name = key.split("/")[-1]  # Extract only the file name
        local_filename = f'/tmp/{file_name}'  # Save the file in /tmp
        s3_client = boto3.client('s3', region_name='us-east-2')

        print(f"Downloading file from S3: bucket={bucket}, key={key}")
        s3_client.download_file(bucket, key, local_filename)
        print(f"File downloaded to {local_filename}")

        # Read and process the CSV file
        print("Reading CSV file and processing rows...")
        required_keys = ["product_id", "product_name", "brand_name", "price", "quantity"]
        table_name = "ProductsTable_mich"  # Change this to your DynamoDB table name
        dynamodb = boto3.resource('dynamodb', region_name='us-east-2')
        table = dynamodb.Table(table_name)

        with open(local_filename, 'r') as f:
            csv_reader = csv.DictReader(f)
            for row in csv_reader:
                # Validate that all required keys are present
                if not all(key in row for key in required_keys):
                    print(f"Skipping row due to missing keys: {row}")
                    continue

                # Insert the row into the DynamoDB table
                table.put_item(Item=row)
                print(f"Inserted row into DynamoDB: {row}")

        print("All rows processed successfully!")
        return {"statusCode": 200, "body": json.dumps({"message": "Batch creation completed successfully"})}

    except Exception as e:
        print(f"Error processing batch creation: {e}")
        traceback.print_exc()
        return {"statusCode": 500, "body": json.dumps({"error": "Failed to process batch creation"})}
        

def batch_delete_products(event, context):
    """
    Lambda function to process a CSV file uploaded to S3, parse its contents,
    and delete products with matching product_ids from the DynamoDB table.
    """
    print("File uploaded trigger")
    print("Event:", event)  # Log the event for debugging

    try:
        # Extract file location from event payload
        print("Extract file location from event payload")
        bucket = event['Records'][0]['s3']['bucket']['name']
        key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'])
        file_name = key.split("/")[-1]  # Extract only the file name
        local_filename = f'/tmp/{file_name}'  # Save the file in /tmp
        s3_client = boto3.client('s3', region_name='us-east-2')

        print(f"Downloading file from S3: bucket={bucket}, key={key}")
        s3_client.download_file(bucket, key, local_filename)
        print(f"File downloaded to {local_filename}")

        # Read and process the CSV file
        print("Reading CSV file and processing rows...")
        required_keys = ["product_id"]
        table_name = "ProductsTable_mich"  # Change this to your DynamoDB table name
        dynamodb = boto3.resource('dynamodb', region_name='us-east-2')
        table = dynamodb.Table(table_name)

        with open(local_filename, 'r') as f:
            csv_reader = csv.DictReader(f)
            for row in csv_reader:
                # Validate that the required key is present
                if not all(key in row for key in required_keys):
                    print(f"Skipping row due to missing keys: {row}")
                    continue

                product_id = row["product_id"]

                try:
                    # Attempt to delete the item from the DynamoDB table
                    response = table.delete_item(
                        Key={"product_id": product_id},
                        ConditionExpression="attribute_exists(product_id)"  # Only delete if the item exists
                    )
                    print(f"Deleted product_id: {product_id}")
                except table.meta.client.exceptions.ConditionalCheckFailedException:
                    # Skip if the product_id does not exist
                    print(f"Product_id {product_id} does not exist. Skipping.")

        print("All rows processed successfully!")
        return {"statusCode": 200, "body": json.dumps({"message": "Batch deletion completed successfully"})}

    except Exception as e:
        print(f"Error processing batch deletion: {e}")
        traceback.print_exc()
        return {"statusCode": 500, "body": json.dumps({"error": "Failed to process batch deletion"})}

def add_stocks_to_product(event, context):
    """
    Lambda function to add stock to a product in the inventory table.
    :param event: The event data passed to the Lambda function.
    :param context: The runtime information of the Lambda function.
    :return: A JSON response confirming the stock addition or an error message.
    """
    print("EVENT:", event)

    # Configuration
    table_name = "ProductInventory_mich"
    dynamodb = boto3.resource('dynamodb', region_name=REGION)
    table = dynamodb.Table(table_name)

    # Extract product_id from path parameters
    product_id = event["pathParameters"].get("product_id")
    if not product_id:
        return {"statusCode": 400, "body": json.dumps({"error": "Missing product_id in path parameters"})}

    # Parse the request body
    try:
        body = json.loads(event["body"])
        quantity = body.get("quantity")
        if quantity is None or not isinstance(quantity, (int, float)):
            return {"statusCode": 400, "body": json.dumps({"error": "Invalid or missing 'quantity' in request body"})}
        remarks = body.get("remarks", "")
    except Exception as e:
        print(f"Error parsing request body: {e}")
        return {"statusCode": 400, "body": json.dumps({"error": "Invalid request body"})}

    # Generate a timestamp for the stock addition
    now = datetime.utcnow().isoformat()

    # Create the stock item
    item = {
        "product_id": product_id,
        "datetime": now,
        "quantity": Decimal(str(quantity)),  # Ensure quantity is stored as Decimal
        "remarks": remarks
    }

    try:
        # Insert the stock item into the DynamoDB table
        table.put_item(Item=item)
        print(f"Stock added successfully: {item}")
        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Stock added successfully", "item": item}, cls=DecimalEncoder)
        }
    except Exception as e:
        print(f"Error adding stock: {e}")
        traceback.print_exc()
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Failed to add stock"})
        }

# Receive message from SQS
def receive_message_from_sqs(event, context):
    """
    Lambda function to process SQS messages, write them to a CSV file, and upload the file to an S3 bucket.
    """
    print("File uploaded trigger")
    print(event)

    # Define the CSV field names
    fieldnames = ["product_id", "product_name", "brand_name", "price", "quantity"]

    # Generate a randomized file prefix and file name
    file_randomized_prefix = generate_code("pycon_", 8)
    file_name = f'/tmp/product_created_{file_randomized_prefix}.csv'
    object_name = f'product_created_{file_randomized_prefix}.csv'

    try:
        # Write the SQS message payloads to a CSV file
        with open(file_name, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()  # Write the CSV header
            for payload in event["Records"]:
                json_payload = json.loads(payload["body"])
                writer.writerow(json_payload)

        # Upload the CSV file to the S3 bucket
        s3_client = boto3.client('s3', region_name=REGION)
        s3_client.upload_file(file_name, S3_BUCKET_NAME, object_name)
        print(f"File uploaded to S3: {S3_BUCKET_NAME}/{object_name}")

        print("All done!")
        return {"statusCode": 200, "body": "Messages processed successfully"}

    except Exception as e:
        print(f"Error processing SQS messages: {e}")
        traceback.print_exc()
        return {"statusCode": 500, "body": json.dumps({"error": "Failed to process SQS messages"})}