def safe_decimal(val, divisor=1):
    """安全转换小数并按指定除数缩放。

    Args:
        val: 待转换的原始值，支持数字、数字字符串或空值。
        divisor: 缩放除数，默认不缩放。

    Returns:
        float | None: 转换成功时返回保留三位小数的结果；输入为空或非法时返回 ``None``。
    """
    if val == "-" or val is None or val == "":
        return None
    try:
        return round(float(val) / divisor, 3)
    except ValueError:
        return None


def safe_int(val):
    """安全转换整数值。

    Args:
        val: 待转换的原始值，支持数字、数字字符串或空值。

    Returns:
        int | None: 转换成功时返回整数；输入为空或非法时返回 ``None``。
    """
    if val == "-" or val is None or val == "":
        return None
    try:
        return int(val)
    except ValueError:
        return None
