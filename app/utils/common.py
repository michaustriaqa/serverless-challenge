def validate_required_keys(row, required_keys):
    return all(key in row for key in required_keys)