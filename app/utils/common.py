def validate_required_keys(row, required_keys):
    """
    Validates that all required keys exist in the given row dictionary.
    Returns True if all keys are present, False otherwise.
    """
    return all(key in row for key in required_keys)
