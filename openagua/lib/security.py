from hashlib import sha256
# from openagua.models import User
import random
import string


def generate_random_alphanumeric_key(k=8):
    x = ''.join(random.choices(string.ascii_letters + string.digits, k=k))
    return x


def hash_key(plaintext):
    return sha256(plaintext.encode()).hexdigest()


# def get_jwt(username, password):
#
#     User =