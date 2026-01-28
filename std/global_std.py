import math

def get_length(value):
    if isinstance(value, tuple) and len(value) == 3:
        value = value[0]

    if isinstance(value, (str, list, tuple, dict)):
        return len(value)

    if isinstance(value, int):
        return value.bit_length()

    if isinstance(value, float):
        if value == 0.0:
            return 1

        integer_part = int(math.floor(abs(value)))
        fractional_part = abs(value) - integer_part

        length = integer_part.bit_length()

        frac_bits = 0
        while fractional_part != 0 and frac_bits < 52:
            fractional_part *= 2
            bit = int(fractional_part)
            fractional_part -= bit
            frac_bits += 1

        return length + frac_bits

    raise TypeError(f"Cannot get length of type '{type(value).__name__}'")

def castto(value, ttype):
    if isinstance(value, tuple) and len(value) == 3:
        value = value[0]

    try:
        if ttype == "int":
            return int(value)
        elif ttype == "str":
            return str(value)
        elif ttype == "float":
            return float(value)
        elif ttype == "long":
            return int(value)
        elif ttype == "double":
            return float(value)
        elif ttype == "bool":
            if value in (None, False, 0, 0.0, "", [], (), {}):
                return False
            return True
        elif ttype == "list":
            if isinstance(value, str):
                return list(value)
            elif isinstance(value, (list, tuple)):
                return list(value)
            else:
                return [value]
        elif ttype == "tuple":
            if isinstance(value, list):
                return tuple(value)
            elif isinstance(value, tuple):
                return value
            else:
                return (value,)
        elif ttype == "map":
            if isinstance(value, dict):
                return value
            elif isinstance(value, (list, tuple)):
                try:
                    return dict(value)
                except Exception as e:
                    raise Exception(f"orerrCannot cast list/tuple to map: invalid format ({e})")
            elif isinstance(value, str):
                raise Exception("orerrCasting string to map not supported")
            else:
                raise Exception(f"orerrCannot cast type {type(value).__name__} to map")
        else:
            raise Exception(f"orerrUnsupported cast target type '{ttype}'")
    except Exception as e:
        msg = str(e)
        if msg.startswith("orerr"):
            cleaned_msg = msg[len("orerr"):].rstrip()
            raise Exception(cleaned_msg)
        else:
            raise Exception(f"Cannot cast {value} to {ttype}")

def base(value, current_base, target_base):
    digits = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz+/"
    value = str(value).strip()

    prefixes = {
        "0x": 16, "0X": 16,
        "0b": 2,  "0B": 2,
        "0o": 8,  "0O": 8
    }

    for prefix, base_match in prefixes.items():
        if value.startswith(prefix):
            if current_base != base_match:
                raise ValueError(
                    f"Prefix '{prefix}' implies base {base_match}, "
                    f"but current_base={current_base}"
                )
            value = value[len(prefix):]
            break

    dec = 0
    for char in value:
        if char not in digits:
            raise ValueError(f"Invalid digit: {char}")

        d = digits.index(char)
        if d >= current_base:
            raise ValueError(
                f"Digit '{char}' invalid for base {current_base}"
            )

        dec = dec * current_base + d

    if dec == 0:
        return 0 if target_base <= 10 else "0"

    result = []
    while dec > 0:
        result.append(digits[dec % target_base])
        dec //= target_base

    result_str = "".join(reversed(result))

    if result_str.isdigit():
        return int(result_str)
    return result_str

functions = [("length", lambda x: get_length(x), "function", False),
             ("cast", lambda v,t: castto(v,t), "function", False),
             ("tobase", lambda v,c,t: base(v,c,t), "function", False),
]