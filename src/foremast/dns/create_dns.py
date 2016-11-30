#   Foremast - Pipeline Tooling
#
#   Copyright 2016 Gogo, LLC
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

"""Module to create dynamically generated DNS record in route53"""
import logging

from ..consts import DOMAIN
from ..utils import find_elb, get_details, get_dns_zone_ids, get_properties, update_dns_zone_record


class SpinnakerDns:
    """Manipulate and create generated DNS record in Route53.

    Args:
        app (str): application name for DNS record
        env (str): Environment/Account for DNS record creation
        region (str): AWS Region for DNS record
        elb_subnet (str): Wether the DNS record is in a public or private zone
        prop_path (str): Path to the generated property files

    Returns:
        str: FQDN of application
    """

    def __init__(self, app=None, env=None, region=None, elb_subnet=None, prop_path=None):
        self.log = logging.getLogger(__name__)

        self.domain = DOMAIN
        self.env = env
        self.region = region
        self.elb_subnet = elb_subnet

        self.generated = get_details(app, env=self.env, region=self.region)
        self.app_name = self.generated.app_name()

        self.properties = get_properties(properties_file=prop_path, env=self.env)
        self.dns_ttl = self.properties['dns']['ttl']
        self.header = {'content-type': 'application/json'}

    def create_elb_dns(self, hasregion=False):
        """Create dns entries in route53.

        Args:
            hasregion (bool): The DNS entry should have region on it
        Returns:
            Auto-generated DNS name for the Elastic Load Balancer.
        """
        if hasregion:
            dns_elb = self.generated.dns()['elb_region']
        else:
            dns_elb = self.generated.dns()['elb']

        dns_elb_aws = find_elb(name=self.app_name,
                               env=self.env,
                               region=self.region)

        zone_ids = get_dns_zone_ids(env=self.env, facing=self.elb_subnet)

        self.log.info('Updating Application URL: %s', dns_elb)

        dns_kwargs = {
            'dns_name': dns_elb,
            'dns_name_aws': dns_elb_aws,
            'dns_ttl': self.dns_ttl,
        }

        for zone_id in zone_ids:
            self.log.debug('zone_id: %s', zone_id)
            update_dns_zone_record(self.env, zone_id, **dns_kwargs)

        return dns_elb

    def create_failover_dns(self):
        """Create dns entries in route53 for multiregion failover setupts

        Returns:
            Auto-generated DNS name.
        """
        dns_record = self.generated.dns()['no_region']
        zone_ids = get_dns_zone_ids(env=self.env, facing=self.elb_subnet)

        #put together list of expected ELB records
        elb_records = []
        regions = self.properties['app']['regions']
        for region in regions:
            gen = get_details(app, env=self.env, region=region)
            elb_records.append(gen.dns()['elb_region'])

        self.log.info('Updating Application URL: %s', dns_elb)

        dns_kwargs = {
            'dns_name': dns_record,
            'elb_records': elb_records,
            'dns_ttl': self.dns_ttl,
        }

        for zone_id in zone_ids:
            self.log.debug('zone_id: %s', zone_id)
            update_dns_zone_record(self.env, zone_id, failover_record=True, **dns_kwargs)

        return dns_record
