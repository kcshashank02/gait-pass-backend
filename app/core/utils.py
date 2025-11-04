from bson import Decimal128
from decimal import Decimal
from typing import Any

def convert_decimals_to_bson(obj: Any) -> Any:
    """
    Recursively convert Python Decimal objects to BSON Decimal128
    for MongoDB compatibility
    """
    if isinstance(obj, dict):
        return {k: convert_decimals_to_bson(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_decimals_to_bson(item) for item in obj]
    elif isinstance(obj, Decimal):
        return Decimal128(str(obj))
    else:
        return obj
