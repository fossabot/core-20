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
""" Vault Configuration managing tests module """
import pytest


@pytest.mark.django_db
def test_module_configuration_api(api_client):
    conf = api_client.config.get_module_config()
    assert conf is not None


@pytest.mark.django_db
def test_module_configuration_lapi(lapi_client):
    conf = lapi_client.config.get_module_config()
    assert conf is not None


@pytest.mark.django_db
def test_module_configuration_dashboards(dashboards_client):
    conf = dashboards_client.config.get_module_config()
    assert conf is not None
