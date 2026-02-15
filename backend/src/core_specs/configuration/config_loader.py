"""
#############################################################################
### Configuration loader file
###
### @file config_loader.py
### @author Sebastian Russo
### @date 2025
#############################################################################

This module loads configuration data from a JSON file.
It reads the file, parses JSON, and instantiates variables
for other modules to access essential settings.
"""
#Native imports
import json
import sys

"""METHOD-----------------------------------------------------------"""
def read_data_from_config_json(file_path: str, exit_on_error: bool = True) -> dict:
    """
    Reads data from a JSON configuration file.

    Parameters:
        file_path (str): Path to the JSON config file.
        exit_on_error (bool): Whether to exit on error or return None.

    Returns:
        dict: Parsed JSON configuration data.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            config_data = json.load(file)
        return config_data
    except FileNotFoundError:
        print(f"ERROR: Config file not found: {file_path}")
        if exit_on_error:
            sys.exit(1)
        else:
            return None
    except json.JSONDecodeError:
        print(f"ERROR: Failed to parse JSON config file: {file_path}")
        if exit_on_error:
            sys.exit(1)
        else:
            return None

"""VARIABLES-----------------------------------------------------------"""
#Path to your config JSON file
CONFIG_FILE_PATH = "src/core_specs/configuration/config_file.json" #Put file beside this one

#Load the entire configuration data, the one to be used
config_loader = read_data_from_config_json(CONFIG_FILE_PATH, exit_on_error=True)
