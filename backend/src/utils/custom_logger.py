"""
#############################################################################
### Custom logger file
###
### @file custom_logger.py
### @author Sebastian Russo
### @date 2025
#############################################################################

This module initializes a custom logger to handle log messages for the other modules.
"""

#Native imports
import os
import logging
import sys
import datetime

#Other files imports
from src.core_specs.configuration.config_loader import config_loader

#Map config string levels to logging module levels
LOG_LEVELS = {
    "critical": logging.CRITICAL,
    "error": logging.ERROR,
    "warning": logging.WARNING,
    "info": logging.INFO,
    "debug": logging.DEBUG,
    "notset": logging.NOTSET
}

#Get log level string from config_loader and convert to logging level, default to INFO if not found
log_level_str = config_loader["logging"].get("logging_level", "info").lower()
log_level = LOG_LEVELS.get(log_level_str, logging.INFO)

"""Log basic configuration"""
log_handler = logging.getLogger(config_loader["logging"]["log_file_name"])
log_handler.setLevel(log_level)

"""Logger formatter"""
log_format = logging.Formatter(
    fmt="%(asctime)s %(msecs)03dZ | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

"""File handler (File accessible only when it runs locally)"""
#Create folder
log_directory = config_loader["logging"]["dir_name"]
os.makedirs(log_directory,exist_ok=True)

#Create log file
log_file = os.path.join(
                    log_directory, 
                    datetime.datetime.now().strftime(
                        f"{config_loader["logging"]["log_file_name"]}_%Y-%m-%dT%H-%M-%S.log"))
file_handler = logging.FileHandler(log_file)
file_handler.setFormatter(log_format)

"""Console handler for Render logs"""
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(log_format)

#Final log handler
if not log_handler.hasHandlers():
    log_handler.addHandler(file_handler)
    log_handler.addHandler(console_handler)

log_handler.info("REST API Template server starting")
log_handler.warning(f"Current working directory: {os.getcwd()}, Logs are written to '{log_file}'")

#Example usage
"""
from src.utils.custom_logger import log_handler

log_handler.debug("Debug message")
log_handler.info("Info message")
log_handler.warning("Warning message")
log_handler.error("Error message")
log_handler.critical("Critical message")
"""
