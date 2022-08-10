#SPDX-License-Identifier: MIT
"""
Augur library script for generating a config file
"""

import os
import click
import json
import logging
from pathlib import Path

# from augur.config import default_config, ENVVAR_PREFIX, CONFIG_HOME
# from augur.cli import initialize_logging
# from augur.logging import ROOT_AUGUR_DIRECTORY

from augur.application.db.models import Config
from augur.application.db.session import DatabaseSession
from augur.application.logs import AugurLogger
from augur.application.cli import test_connection, test_db_connection 

from augur.application.cli import test_connection, test_db_connection

ROOT_AUGUR_DIRECTORY = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

logger = AugurLogger("cli").get_logger()

ENVVAR_PREFIX = "AUGUR_"

@click.group('config', short_help='Generate an augur.config.json')
def cli():
    pass

@cli.command('init')
@click.option('--github_api_key', help="GitHub API key for data collection from the GitHub API", envvar=ENVVAR_PREFIX + 'GITHUB_API_KEY')
@click.option('--facade_repo_directory', help="Directory on the database server where Facade should clone repos", envvar=ENVVAR_PREFIX + 'FACADE_REPO_DIRECTORY')
@click.option('--gitlab_api_key', help="GitLab API key for data collection from the GitLab API", envvar=ENVVAR_PREFIX + 'GITLAB_API_KEY')
@test_connection
@test_db_connection
def init_config(github_api_key, facade_repo_directory, gitlab_api_key):

    with DatabaseSession(logger) as session:
        config = session.config

        keys = {}

        if github_api_key:
            keys["github_api_key"] = github_api_key
        if gitlab_api_key:
            keys["gitlab_api_key"] = gitlab_api_key

        default_config = config.default_config

        default_config["Keys"] = keys

        if facade_repo_directory:
            default_config["Facade"]["repo_directory"] = facade_repo_directory

        default_config["Logging"]["logs_directory"] = ROOT_AUGUR_DIRECTORY + "/logs/"

        config.load_config_from_dict(default_config)


@cli.command('load')
@click.option('--file', required=True)
@test_connection
@test_db_connection
def load_config(file):

    with DatabaseSession(logger) as session:
        config = session.config

        print("WARNING: This will override your current config")
        response = str(input("Would you like to continue: [y/N]: ")).lower()

        if response != "y" and response != "yes":
            print("Did not recieve yes or y exiting...")
            return

        file_data = config.load_config_file(file)

        config.clear()
        
        config.load_config_from_dict(file_data)
    
@cli.command('add-section')
@click.option('--section-name', required=True)
@click.option('--file', required=True)
@test_connection
@test_db_connection
def add_section(section_name, file):

    with DatabaseSession(logger) as session:
        config = session.config

        if config.is_section_in_config(section_name):

            print(f"Warning there is already a {section_name} section in the config and it will be replaced")
            response = str(input("Would you like to continue: [y/N]: ")).lower()

            if response != "y" and response != "yes":
                print("Did not recieve yes or y exiting...")
                return

        config.remove_section(section_name)
                
        with open(file, 'r') as f:
            section_data = json.load(f)

        config.add_section_from_json(section_name, section_data)


@cli.command('set')
@click.option('--section', required=True)
@click.option('--setting', required=True)
@click.option('--value', required=True)
@click.option('--data-type', required=True)
@test_connection
@test_db_connection
def config_set(section, setting, value, data_type):

    with DatabaseSession(logger) as session:
        config = session.config

        if data_type not in config.accepted_types:
            print(f"Error invalid type for config. Please use one of these types: {config.accepted_types}")
            return

        
        setting = {
            "section_name": section,
            "setting_name": setting, 
            "value": value,
            "type": data_type
        }

        config.add_or_update_settings([setting])

@cli.command('get')
@click.option('--section', required=True)
@click.option('--setting')
@test_connection
@test_db_connection
def config_get(section, setting):

    with DatabaseSession(logger) as session:
        config = session.config

        if setting:
            config_value = config.get_value(section_name=section, setting_name=setting)

            if config_value is not None:
                print(f"======================\n{setting}: {config_value}\n======================")
            else:
                print(f"Error unable to find '{setting}' in the '{section}' section of the config")
                
        else:
            section_data = config.get_section(section_name=section)
            
            if section_data:
                print(f"======================\n{section}\n====")
                section_data_keys = list(section_data.keys())
                for key in section_data_keys:
                    print(f"{key}: {section_data[key]}")

                print("======================")

            else:
                print(f"Error: {section} section not found in config")

@cli.command('clear')
@test_connection
@test_db_connection
def clear_config():

    with DatabaseSession(logger) as session:
        config = session.config

        if not config.empty():

            print("Warning this delete the current config")
            response = str(input("Would you like to continue: [y/N]: ")).lower()

            if response != "y" and response != "yes":
                print("Did not recieve yes or y exiting...")
                return

        config.clear()

        print("Config cleared")


