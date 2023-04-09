def string_is_float(string: str, recect_negative: bool = False) -> bool:
    """Returns True if string can be converted to float"""
    try:
        decimal = float(string)
    except ValueError:
        return False
    if recect_negative and decimal < 0:
        return False
    return True
