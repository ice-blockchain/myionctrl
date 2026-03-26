import base64
import json
import re
import subprocess
try:
    # Python 3.9+
    from importlib.resources import files, as_file
except ImportError:
    # Python < 3.9
    from importlib_resources import files, as_file


def str2b64(s):
    b = s.encode("utf-8")
    b64 = base64.b64encode(b)
    b64 = b64.decode("utf-8")
    return b64
# end define


def b642str(b64):
    b64 = b64.encode("utf-8")
    b = base64.b64decode(b64)
    s = b.decode("utf-8")
    return s
# end define


def dict2b64(d):
    s = json.dumps(d)
    b64 = str2b64(s)
    return b64
# end define


def b642dict(b64):
    s = b642str(b64)
    d = json.loads(s)
    return d
# end define


def hex2b64(input):  # TODO: remove duplicates
    hexBytes = bytes.fromhex(input)
    b64Bytes = base64.b64encode(hexBytes)
    b64String = b64Bytes.decode()
    return b64String
# end define


def b642hex(input):
    b64Bytes = input.encode()
    hexBytes = base64.b64decode(b64Bytes)
    hexString = hexBytes.hex()
    return hexString
# end define


def xhex2hex(x):
    try:
        b = x[1:]
        h = b.lower()
        return h
    except Exception:
        return None
#end define

def hex2base64(h):  # TODO: remove duplicates
    b = bytes.fromhex(h)
    b64 = base64.b64encode(b)
    s = b64.decode("utf-8")
    return s
#end define


def str2bool(str):
    if str == "true":
        return True
    return False
# end define


def ng2g(ng):
    if ng is None:
        return
    return int(ng)/10**9
#end define


def parse_db_stats(path: str):
    with open(path) as f:
        lines = f.readlines()
    result = {}
    for line in lines:
        s = line.strip().split(maxsplit=1)
        items = re.findall(r"(\S+)\s:\s(\S+)", s[1])
        if len(items) == 1:
            item = items[0]
            if float(item[1]) > 0:
                result[s[0]] = float(item[1])
        else:
            if any(float(v) > 0 for k, v in items):
                result[s[0]] = {}
                result[s[0]] = {k: float(v) for k, v in items}
    return result
# end define

def get_hostname():
    return subprocess.run(["hostname"], stdout=subprocess.PIPE).stdout.decode().strip()

def hex_shard_to_int(shard_id_str: str) -> dict:
    try:
        wc, shard_hex = shard_id_str.split(':')
        wc = int(wc)
        shard = int(shard_hex, 16)
        if shard >= 2 ** 63:
            shard -= 2 ** 64
        return {"workchain": wc, "shard": shard}
    except (ValueError, IndexError):
        raise Exception(f'Invalid shard ID "{shard_id_str}"')

def signed_int_to_hex64(value):
    if value < 0:
        value = (1 << 64) + value
    return f"{value:016X}"


_MASK64 = (1 << 64) - 1


def _to_unsigned64(v: int) -> int:
    return v & _MASK64


def _lower_bit64(u: int) -> int:
    if u == 0:
        return 0
    return u & ((-u) & _MASK64)


def _bits_negate64(u: int) -> int:
    return ~u + 1


def shard_prefix_len(shard_id: int):
    def _count_trailing_zeroes64(value: int) -> int:
        u = value & _MASK64
        if u == 0:
            return 64
        return ((u & -u).bit_length()) - 1
    return 63 - _count_trailing_zeroes64(_to_unsigned64(shard_id))


def shard_prefix(shard_id: int, length_: int):

    def _to_signed64(v: int) -> int:
        return v - (1 << 64) if v >= (1 << 63) else v

    if not (0 <= length_ <= 63):
        raise ValueError("length must be between 0 and 63 inclusive")
    u = _to_unsigned64(shard_id)
    x = _lower_bit64(u)
    y = 1 << (63 - length_)
    if y < x:
        raise ValueError("requested prefix length is longer (more specific) than current shard id")
    mask_non_lower = (~(y - 1)) & _MASK64  # equals -y mod 2^64; clears bits below y
    res_u = (u & mask_non_lower) | y
    return _to_signed64(res_u)


def shard_contains(parent: int, child: int) -> bool:
    parent = _to_unsigned64(parent)
    child = _to_unsigned64(child)
    x = _lower_bit64(parent)
    mask = (_bits_negate64(x) << 1) & _MASK64
    return not ((parent ^ child) & mask)


def shard_is_ancestor(parent: int, child: int) -> bool:
    up = _to_unsigned64(parent)
    uc = _to_unsigned64(child)
    x = _lower_bit64(up)
    y = _lower_bit64(uc)
    mask = (_bits_negate64(x) << 1) & _MASK64
    return x >= y and not ((up ^ uc) & mask)


def get_package_resource_path(package: str, resource: str):
    ref = files(package) / resource
    return as_file(ref)
