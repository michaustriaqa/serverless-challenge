import boto3

class DynamoDBGateway:
    @staticmethod
    def get_table(table_name):
        dynamodb = boto3.resource("dynamodb", region_name="us-east-2")
        return dynamodb.Table(table_name)

    @staticmethod
    def put_item(table_name, item):
        try:
            table = DynamoDBGateway.get_table(table_name)
            table.put_item(Item=item)
        except Exception as e:
            raise RuntimeError(f"Failed to put item in table {table_name}: {e}")

    @staticmethod
    def get_item(table_name, key):
        try:
            table = DynamoDBGateway.get_table(table_name)
            response = table.get_item(Key=key)
            return response.get("Item")
        except Exception as e:
            raise RuntimeError(f"Failed to get item from table {table_name}: {e}")

    @staticmethod
    def delete_item(table_name, key):
        try:
            table = DynamoDBGateway.get_table(table_name)
            table.delete_item(Key=key)
        except Exception as e:
            raise RuntimeError(f"Failed to delete item from table {table_name}: {e}")