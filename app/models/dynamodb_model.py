from app.gateways.dynamodb_gateway import DynamoDBGateway


class DynamoDBModelBase:
    DYNAMODB_TABLE_NAME = None

    def __init__(self, key, data):
        self.key = key
        self.data = data
        self.exists = data.get("exists", False)

    def save(self):
        if not self.DYNAMODB_TABLE_NAME:
            raise ValueError("DYNAMODB_TABLE_NAME must be defined in the subclass")
        DynamoDBGateway.create_item(
            table_name=self.DYNAMODB_TABLE_NAME,
            payload=self.data
        )

    @classmethod
    def find(cls, primary_key):
        if not cls.DYNAMODB_TABLE_NAME:
            raise ValueError("DYNAMODB_TABLE_NAME must be defined in the subclass")
        item = DynamoDBGateway.get_item_by_primary_key(
            table_name=cls.DYNAMODB_TABLE_NAME,
            primary_key=primary_key
        )
        if item:
            item["exists"] = True
            return cls(primary_key, item)
        return None
