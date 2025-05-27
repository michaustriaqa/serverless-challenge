import itertools
import boto3
from boto3.dynamodb.conditions import Key


class DynamoDBGateway:
    @classmethod
    def create_item(cls, table_name, payload):
        dynamodb = boto3.resource("dynamodb")
        table = dynamodb.Table(table_name)
        result = table.put_item(Item=payload)
        print("PutItem Result:", result)
        return result

    @classmethod
    def get_item_by_primary_key(cls, table_name, primary_key):
        print(f"Fetching item from {table_name} with key: {primary_key}")
        dynamodb = boto3.resource("dynamodb")
        table = dynamodb.Table(table_name)
        response = table.get_item(Key=primary_key)
        print("GetItem Response:", response)
        return response.get("Item")

    @classmethod
    def scan_all(cls, table_name):
        dynamodb = boto3.resource("dynamodb")
        table = dynamodb.Table(table_name)
        response = table.scan()
        print("Scan Response:", response)
        return response.get("Items", [])

    @classmethod
    def delete_item(cls, table_name, key):
        dynamodb = boto3.resource("dynamodb")
        table = dynamodb.Table(table_name)
        response = table.delete_item(Key=key)
        print("DeleteItem Response:", response)
        return response

    @classmethod
    def update_item(cls, table_name, key, update_expression, expression_values, expression_names=None):
        dynamodb = boto3.resource("dynamodb")
        table = dynamodb.Table(table_name)
        params = {
            "Key": key,
            "UpdateExpression": update_expression,
            "ExpressionAttributeValues": expression_values
        }
        if expression_names:
            params["ExpressionAttributeNames"] = expression_names
        result = table.update_item(**params)
        print("UpdateItem Response:", result)
        return result

    @classmethod
    def batch_upsert(cls, table_name, items, primary_keys):
        dynamodb = boto3.resource("dynamodb")
        table = dynamodb.Table(table_name)
        for chunk in cls._grouper(items, 100):
            batch = list(filter(None, chunk))
            with table.batch_writer(overwrite_by_pkeys=primary_keys) as writer:
                for item in batch:
                    writer.put_item(Item=item)

    @staticmethod
    def _grouper(iterable, n, fillvalue=None):
        args = [iter(iterable)] * n
        return itertools.zip_longest(*args, fillvalue=fillvalue)
