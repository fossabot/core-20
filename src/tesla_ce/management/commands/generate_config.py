#  Copyright (c) 2020 Xavier Baró
#
#      This program is free software: you can redistribute it and/or modify
#      it under the terms of the GNU Affero General Public License as
#      published by the Free Software Foundation, either version 3 of the
#      License, or (at your option) any later version.
#
#      This program is distributed in the hope that it will be useful,
#      but WITHOUT ANY WARRANTY; without even the implied warranty of
#      MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#      GNU Affero General Public License for more details.
#
#      You should have received a copy of the GNU Affero General Public License
#      along with this program.  If not, see <https://www.gnu.org/licenses/>.
""" DJango command to generate the configuration file for TeSLA system """
import os

from django.core.management.base import CommandError

from tesla_ce.client import Client
from ..base import TeslaConfigCommand

BASE_TESLA_CONF_PATH = '/etc/tesla'
BASE_TESLA_CONF_FILE = 'tesla-ce.cfg'


class Command(TeslaConfigCommand):
    """ Command to generate configuration file from template """
    help = 'Generates a configuration file to be used on the initial setup of the TeSLA CE system'
    requires_system_checks = False

    def add_arguments(self, parser):
        """
            Define custom arguments for this command

            :param parser: Input command parser instance
        """
        parser.add_argument(
            '--override',
            action='store_true',
            help='Override existing configuration file',
        )
        parser.add_argument(
            '--local',
            action='store_true',
            help='Create the configuration file in current directory',
        )
        parser.add_argument(
            '--with-services',
            action='store_true',
            help='Include external services data',
        )
        parser.add_argument(
            'domain',
            help='Base domain where TeSLA will be accessible',
        )

    @staticmethod
    def get_client(config_file=None, options=None):
        """
            Create an instance of the client
            :param config_file: Path to the configuration file
            :param options: Provided options to the command
            :return: Instance of client
        """
        return Client

    def get_configuration_file(self):
        """
            Obtain the configuration file to be used
            :return:
        """
        config_file = super().get_configuration_file()

        # If there is no configuration file, try to create one on system folder
        if config_file is None:
            try:
                if not os.path.exists(BASE_TESLA_CONF_PATH):
                    os.makedirs(BASE_TESLA_CONF_PATH)
                with open('{}/{}'.format(BASE_TESLA_CONF_PATH, BASE_TESLA_CONF_FILE), 'w'):
                    config_file = '{}/{}'.format(BASE_TESLA_CONF_PATH, BASE_TESLA_CONF_FILE)
                os.remove(config_file)
            except PermissionError:
                # Create the file in the current folder
                config_file = BASE_TESLA_CONF_FILE

        return config_file

    def check_configuration_file(self):
        """
            Check if the defined configuration file exists
        """
        # Get the file to be checked
        config_file = self.get_configuration_file()

        # Avoid unintentionally override
        if config_file is not None and not self._options['override'] and os.path.exists(config_file):
            self.stdout.write(
                self.style.ERROR('File {} already exists. Use --override option.'.format(config_file))
            )
            raise CommandError('Configuration file already exists')

    def custom_handle(self):
        """
            Custom actions for this command
        """
        # Generate configuration file
        domain = self._options['domain']
        deploy_external_services = self._options['with_services']
        self.client.generate_configuration(self._conf_file, domain, deploy_external_services)

        # Change permissions to the file
        os.chmod(self._conf_file, 0o600)

        self.stdout.write(self.style.SUCCESS('Configuration file created at {}'.format(self._conf_file)))
