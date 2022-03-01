"""
This module contains one class - ParamsHandler,
which contains APIs for configuration parameter
parsing.
"""
import yaml
import os


class ParamsHandler:
    """
    This class contains all the APIs required for fetching
    the values of all the configuration parameters.
    """

    @staticmethod
    def generate_config_hashmap(filepath: str) -> dict:
        """
        Function to generate hashmap
        Args:
            filepath (str): Path for the config file.
        Rerturns:
            dict: Hashmap for config file as a dictionary.
        """
        with open(filepath, 'r') as configfd:
            config_hashmap = yaml.load(configfd, Loader=yaml.SafeLoader)
        return config_hashmap

    def __init__(self, filepath: str):
        """
        Parsing the config file.
        """
        self.config_hashmap = generate_config_hashmap(filepath)
        self.run_config = self.config_hashmap['RUN']
        self.env_config = self.config_hashmap['ENV_DATA']
        self.dep_config = self.config_hashmap['DEPLOYMENT']

    def get_config_hashmap(self) -> dict:
        """
        Returns the config hashmap which is parsed from
        the config file
        """
        return self.config_hashmap