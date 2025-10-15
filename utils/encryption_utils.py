import binascii
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from Crypto.Random import get_random_bytes
import base64
import hashlib
import random
import string


def get_key_and_iv(password, salt, key_length=32, iv_length=16):
    d = d_i = b""
    while len(d) < key_length + iv_length:
        d_i = hashlib.md5(d_i + password.encode('utf-8') + salt).digest()
        d += d_i
    return d[:key_length], d[key_length:key_length + iv_length]


def encrypt(data, password):
    salt = get_random_bytes(8)
    key, iv = get_key_and_iv(password, salt)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    encrypted_data = cipher.encrypt(pad(data.encode('utf-8'), AES.block_size))
    return base64.b64encode(salt + encrypted_data).decode('utf-8')


def decrypt(encrypted_data, password):
    try:
        encrypted_data = base64.b64decode(
            encrypted_data + '==')
        salt = encrypted_data[:8]
        key, iv = get_key_and_iv(password, salt)
        cipher = AES.new(key, AES.MODE_CBC, iv)
        decrypted_data = unpad(cipher.decrypt(encrypted_data[8:]), AES.block_size)
        return decrypted_data.decode('utf-8')
    except (ValueError, KeyError, binascii.Error) as e:
        print(f"Error decrypting data: {e}")
        return None


def read_password_from_file(filepath="data/secret.key"):
    with open(filepath, "r") as file:
        return file.read().strip()


def generate_random_password(length=12):
    characters = string.ascii_letters + string.digits + string.punctuation
    password = ''.join(random.choice(characters) for i in range(length))
    return password
