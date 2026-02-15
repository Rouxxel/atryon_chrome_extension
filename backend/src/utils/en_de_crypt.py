"""
#############################################################################
### RSA Encrypt/Decrypt Singleton
###
### @file en_de_crypt.py
### @Sebastian Russo
### @date: 2025
#############################################################################

This utility provides methods to encrypt and decrypt strings
"""

#Native imports
import os
import json
from base64 import b64encode, b64decode

#Third-party imports
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding

#Other files imports
from src.utils.custom_logger import log_handler

"""VARIABLES-----------------------------------------------------------"""
#Get api key from environment
E_PRIVATE_KEY = os.getenv("E_PRIVATE_KEY")
E_PRIVATE_PASSWORD = os.getenv("E_PRIVATE_PASSWORD")
E_PUBLIC_KEY = os.getenv("E_PUBLIC_KEY")

#Check just in case
if not E_PRIVATE_KEY:
    raise RuntimeError("E_PRIVATE_KEY environment variable is not set.")
if not E_PRIVATE_PASSWORD:
    raise RuntimeError("E_PRIVATE_PASSWORD environment variable is not set.")
if not E_PUBLIC_KEY:
    raise RuntimeError("E_PUBLIC_KEY environment variable is not set.")

"""LOADER METHODS -----------------------------------------------------"""
#Load the private key once
try:
    _private_key = serialization.load_pem_private_key(
        E_PRIVATE_KEY.encode(),
        password=E_PRIVATE_PASSWORD.encode()
    )
    log_handler.info("Private key loaded successfully.")
except Exception as e:
    log_handler.error(f"Failed to load private key: {e}")
    raise

#Load the public key once
try:
    _public_key = serialization.load_pem_public_key(
        E_PUBLIC_KEY.encode()
    )
    log_handler.info("Public key loaded successfully.")
except Exception as e:
    log_handler.error(f"Failed to load public key: {e}")
    raise

"""SINGLETON METHODS -----------------------------------------------------"""
def encrypt_in(message) -> str:
    """
    Encrypt any data (str, int, float, bool, dict, list, etc.) using the loaded public key.
    Non-string data will be converted to string automatically.
    Returns Base64 encoded encrypted data.
    """
    #Convert dict/list/etc to JSON string
    if isinstance(message, (dict, list)):
        message = json.dumps(message)
    else:
        message = str(message)
    
    encrypted = _public_key.encrypt(
        message.encode(),
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
    log_handler.debug("Encryption successful")
    return b64encode(encrypted).decode()


def decrypt_out(token: str, dtype: str = "str"):
    """
    Decrypt a Base64 encoded string using the loaded private key.
    
    Parameters:
        token (str): Base64 encoded encrypted data.
        dtype (str): specify the original type ("str", "int", "float", "bool", "dict", "list")
    
    Returns:
        The decrypted data in the specified type.
    
    Raises:
        ValueError: if an unsupported dtype is provided.
    """
    decrypted_str = _private_key.decrypt(
        b64decode(token),
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    ).decode()

    #Mapping of dtype to conversion function
    type_map = {
        "str": str,
        "int": int,
        "float": float,
        "bool": lambda x: x.lower() in ("true", "1"),
        "dict": json.loads,
        "list": json.loads
    }

    if dtype not in type_map:
        log_handler.debug("Decryption unsuccessful")
        raise ValueError(
            f"Unsupported dtype '{dtype}'. Supported types: {list(type_map.keys())}"
        )

    convert_func = type_map[dtype]
    log_handler.debug("Decryption successful")
    return convert_func(decrypted_str)
