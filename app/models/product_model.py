import json
from decimal import Decimal
from datetime import datetime

from app.models.dynamodb_model import DynamoDBModelBase
from app.gateways.dynamodb_gateway import DynamoDBGateway
from app.gateways.s3_gateway import S3Gateway


class ProductModel(DynamoDBModelBase):
    DYNAMODB_TABLE_NAME = "ProductsTable_mich"
    REQUIRED_KEYS = ["product_id", "name", "price", "brand_name", "quantity"]

    def __init__(self, data: dict):
        self.data = data
        self.validate()

    def validate(self):
        if not all(key in self.data for key in self.REQUIRED_KEYS):
            raise ValueError("Missing required keys in product data")


class InventoryModel(DynamoDBModelBase):
    DYNAMODB_TABLE_NAME = "ProductInventory_mich"
    REQUIRED_KEYS = ["product_id", "quantity"]

    def __init__(self, data: dict):
        self.data = data
        self.validate()

    def validate(self):
        if not all(key in self.data for key in self.REQUIRED_KEYS):
            raise ValueError("Missing required keys in inventory data")


class ProductManager:
    def __init__(self):
        self.s3_gateway = S3Gateway("products-s3bucket-mich-v2")

    def _current_time_str(self):
        return datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")

    def create_product(self, product_data):
        product = ProductModel(product_data)
        product.data["created_at"] = self._current_time_str()
        product.save()
        return {"message": "Product created successfully", "item": product.data}

    def update_product(self, product_id, product_data):
        product = ProductModel(product_data)
        product.data["updated_at"] = self._current_time_str()
        product.save()
        return {"message": "Product updated successfully", "item": product.data}

    def delete_product(self, product_id, product_data):
        DynamoDBGateway.delete_item(ProductModel.DYNAMODB_TABLE_NAME, {"product_id": product_id})
        return {"message": "Product deleted successfully", "item": product_data}

    def get_product(self, product_id):
        try:
            product = DynamoDBGateway.get_item_by_primary_key(
                ProductModel.DYNAMODB_TABLE_NAME,
                {"product_id": product_id}
            )
            if not product:
                return {"error": "Product not found"}

            base_quantity = Decimal(product.get("quantity", 0))
            inventory_items = DynamoDBGateway.query_by_partition_key(
                InventoryModel.DYNAMODB_TABLE_NAME,
                "product_id",
                product_id
            )
            inventory_quantity = sum(Decimal(item.get("quantity", 0)) for item in inventory_items)
            product["total_quantity"] = base_quantity + inventory_quantity

            return product
        except Exception as e:
            print(f"Error fetching product with inventory: {e}")
            return {"error": "Internal server error"}

    def get_all_products(self):
        try:
            products = DynamoDBGateway.scan_all(ProductModel.DYNAMODB_TABLE_NAME)
            return {
                "message": "Products retrieved successfully!",
                "items": products,
                "pagination": {
                    "total_items": len(products)
                }
            }
        except Exception as e:
            print(f"Error fetching all products: {e}")
            return {"error": "Internal server error"}

    def add_inventory(self, product_id, inventory_data):
        inventory = InventoryModel(inventory_data)
        inventory.data["created_at"] = self._current_time_str()
        inventory.save()
        return {"message": "Inventory added successfully", "item": inventory.data}

    def batch_create_products(self, event):
        bucket, key = self.s3_gateway.extract_s3_details(event)
        rows = self.s3_gateway.read_csv(bucket, key)
        for row in rows:
            try:
                product = ProductModel(row)
                product.data["created_at"] = self._current_time_str()
                product.save()
            except ValueError as ve:
                print(f"Skipping row due to validation error: {ve}")

    def batch_delete_products(self, event):
        bucket, key = self.s3_gateway.extract_s3_details(event)
        rows = self.s3_gateway.read_csv(bucket, key)
        for row in rows:
            product_id = row.get("product_id")
            if product_id:
                DynamoDBGateway.delete_item(ProductModel.DYNAMODB_TABLE_NAME, {"product_id": product_id})
            else:
                print(f"Skipping row without 'product_id': {row}")

    def receive_message_from_sqs(self, event):
        results = []

        for record in event.get("Records", []):
            try:
                message_body = json.loads(record["body"])
                action = message_body.get("action")
                data = message_body.get("data")
                product_id = data.get("product_id")

                if action == "create":
                    result = self.create_product(data)
                elif action == "update":
                    result = self.update_product(product_id, data)
                elif action == "delete":
                    result = self.delete_product(product_id, data)
                elif action == "add_inventory":
                    result = self.add_inventory(product_id, data)
                else:
                    result = {"error": f"Unsupported action '{action}'"}

                results.append({"record": record, "result": result})
            except Exception as e:
                print(f"Error processing SQS message: {e}")
                results.append({"record": record, "error": str(e)})

        return {"message": "SQS messages processed", "results": results}
