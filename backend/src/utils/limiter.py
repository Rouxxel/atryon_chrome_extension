"""
#############################################################################
### Limiter element file
###
### @file limiter.py
### @Sebastian Russo
### @date: 2025
#############################################################################

This module contains the element to limit the number of requests per minute to
the endpoints in the server
"""

#Third party libraries
from slowapi import Limiter
from slowapi.util import get_remote_address

#Shared rate limiter instance
limiter = Limiter(key_func=get_remote_address)
