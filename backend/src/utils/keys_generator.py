"""
#############################################################################
### Asymmetric key generator
###
### @file keys_generator.py
### @Sebastian Russo
### @date: 2025
#############################################################################

This script generates a public and private key to be used for asymmetrical keys
encryption, must be ran only once and the generated private key must never
be shared anywhere.
The parameters used can be tinkered as desired
"""

#Third-party imports
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

#Other files imports
from src.utils.custom_logger import log_handler

#Generate private key
private_key = rsa.generate_private_key(
    public_exponent=65537, #Can be changed
    key_size=2048 #Can be modified
)
#Generate public key from private key
public_key = private_key.public_key()

#Export keys as PEM
private_pem = private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.TraditionalOpenSSL,  #PKCS#1
    encryption_algorithm=serialization.BestAvailableEncryption(b"PASSWORD_HERE") #Can be without password
)
with open("private_key.pem", "wb") as f:
    f.write(private_pem)

public_pem = public_key.public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo
)
with open("public_key.pem", "wb") as f:
    f.write(public_pem)

log_handler.info("✅ Keys generated successfully!")
log_handler.info("Private key saved as private_key.pem")
log_handler.info("Public key saved as public_key.pem")
