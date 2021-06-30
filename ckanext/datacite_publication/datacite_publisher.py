import collections
import json
import requests
import traceback
from requests.auth import HTTPBasicAuth
import base64

from ckantoolkit import config
import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
from ckan.lib.helpers import url_for


from ckanext.package_converter.model.record import Record, XMLRecord
from ckanext.package_converter.model.metadata_format import MetadataFormats

import logging

log = logging.getLogger(__name__)


class DatacitePublisher(plugins.SingletonPlugin):

    def __init__(self):
        self.datacite_url = config.get('datacite_publication.datacite_url', '')
        self.account_name = config.get('datacite_publication.account_name', '')
        self.account_password = config.get('datacite_publication.account_password', '')
        self.url_prefix = config.get('datacite_publication.url_prefix', '')

    def publish(self, doi, pkg=None, context={}, *args, **kwargs):

        update_doi = kwargs.get('update', False)

        # dataset data
        package_id = pkg['id']
        url = config.get('ckan.site_url', '') + '/dataset/' + pkg.get('name', pkg['id'])

        if self.url_prefix:
            url = self.url_prefix + pkg.get('name', pkg['id'])

        if update_doi:
            log.debug("*** Updating id = {0}, url = {1}".format(package_id, url))
        else:
            log.debug("Publishing id = {0}, url = {1}".format(package_id, url))

        # get converted package
        metadata_format = 'datacite'

        try:
            converted_package = toolkit.get_action(
                'package_export')(
                context,
                {'id': package_id, 'format': metadata_format}
            )
        except toolkit.ObjectNotFound:
            return None, 'Dataset not found'

        xml = converted_package.replace('\n', '').replace('\t', '')

        # Validate        
        try:
            converted_record = XMLRecord.from_record(
                Record(MetadataFormats().get_metadata_formats(metadata_format)[0], xml))
            validation_result = converted_record.validate()
            log.debug("Validation result: {0}".format(validation_result))
        except Exception as e:
            log.error("Converted Validation FAILED, exception: {0}".format(e))
            traceback.print_exc()
            validation_result = False

        if not validation_result:
            return None, 'Dataset XML validation failed'

        # encode 64
        xml_bytes = xml
        if isinstance(xml, str):
            xml_bytes = xml.encode('utf-8')
        xml_encoded = base64.b64encode(xml_bytes)

        # prepare JSON
        headers = {"Content-Type": "application/vnd.api+json"}
        auth = HTTPBasicAuth(self.account_name, self.account_password)

        data = collections.OrderedDict()
        data['id'] = doi
        data['type'] = 'dois'
        data['attributes'] = collections.OrderedDict()
        # TODO check for update if this state is correct
        if update_doi:
            data['attributes']['event'] = ""
        else:
            data['attributes']['event'] = "publish"
        data['attributes']['doi'] = doi
        data['attributes']['url'] = url
        data['attributes']['xml'] = xml_encoded.decode()
        args = {'data': data}

        args_json = json.dumps(args)
        # log.debug(args_json)

        datacite_url_endpoint = self.datacite_url
        if update_doi:
            datacite_url_endpoint = self.datacite_url + '/' + doi
        log.debug(" REST request send to URL: {0}".format(datacite_url_endpoint))

        if update_doi:
            r = requests.put(datacite_url_endpoint, headers=headers, auth=auth, data=args_json)
        else:
            r = requests.post(datacite_url_endpoint, headers=headers, auth=auth, data=args_json)

        # print(r.status_code)
        # print(r.json())

        if r.status_code == 201 or r.status_code == 200:
            published_doi = r.json().get('data').get('id')
            return published_doi, None
        else:
            if update_doi:
                return None, 'Error updating to DataCite: HTTP Code: {0}, error: {1}'.format(r.status_code, r.json())
            else:
                return None, 'Error publishing to DataCite: HTTP Code: {0}, error: {1}'.format(r.status_code, r.json())

    def publish_resource(self, doi, resource=None, package={}, context={}, *args, **kwargs):

        # resource data
        id = resource.get('id')

        # dataset data
        package_id = package.get('name', package['id'])
        url = config.get('ckan.site_url', '') + url_for('dataset_resource.read', id=package_id, resource_id=id)
        log.debug("Resource original url is = {0}".format(url))

        if self.url_prefix:
            url = self.url_prefix + package_id

        log.debug("Publishing id = {0}, url = {1}".format(id, url))

        # get converted package
        metadata_format = 'datacite'

        try:
            converted_resource = toolkit.get_action(
                'resource_export')(
                context,
                {'id': id, 'format': metadata_format}
            )
        except toolkit.ObjectNotFound:
            return None, 'Resource not found'

        xml = converted_resource.replace('\n', '').replace('\t', '')

        # Validate
        try:
            converted_record = XMLRecord.from_record(
                Record(MetadataFormats().get_metadata_formats(metadata_format)[0], xml))
            validation_result = converted_record.validate()
            log.debug("Validation result: {0}".format(validation_result))
        except Exception as e:
            log.error("Converted Validation FAILED, exception: {0}".format(e))
            traceback.print_exc()
            validation_result = False

        if not validation_result:
            return None, 'Dataset XML validation failed'

        # encode 64
        xml_bytes = xml
        if isinstance(xml, str):
            xml_bytes = xml.encode('utf-8')
        xml_encoded = base64.b64encode(xml_bytes)

        # prepare JSON
        headers = {"Content-Type": "application/vnd.api+json"}
        auth = HTTPBasicAuth(self.account_name, self.account_password)

        data = collections.OrderedDict()
        data['id'] = doi
        data['type'] = 'dois'
        data['attributes'] = collections.OrderedDict()
        data['attributes']['event'] = "publish"
        data['attributes']['doi'] = doi
        data['attributes']['url'] = url
        data['attributes']['xml'] = xml_encoded.decode()
        args = {'data': data}

        args_json = json.dumps(args)
        # log.debug(args_json)

        datacite_url_endpoint = self.datacite_url
        log.debug(" REST request send to URL: {0}".format(datacite_url_endpoint))

        r = requests.post(datacite_url_endpoint, headers=headers, auth=auth, data=args_json)

        print(r.status_code)
        print(r.json())

        if r.status_code == 201 or r.status_code == 200:
            published_doi = r.json().get('data').get('id')
            return published_doi, None
        else:
            return None, 'Error publishing to DataCite: HTTP Code: {0}, error: {1}'.format(r.status_code, r.json())

    def __repr__(self):
        return str(self)

    def __str__(self):
        return str(self).encode('utf-8')

    def __unicode__(self):
        return u'DatacitePublisher: datacite_url=\'{0}\' '.format(self.datacite_url)
