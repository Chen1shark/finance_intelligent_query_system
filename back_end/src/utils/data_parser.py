def safe_decimal(val, divisor=1):
    """安全转换小数并按指定除数缩放，处理空值和异常"""
    if val == "-" or val is None or val == "":
        return None
    try:
        return round(float(val) / divisor, 3)
    except ValueError:
        return None


def safe_int(val):
    """安全转换整数，处理空值和异常"""
    if val == "-" or val is None or val == "":
        return None
    try:
        return int(val)
    except ValueError:
        return None
