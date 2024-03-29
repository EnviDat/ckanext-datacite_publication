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

    def get_doi_identifiers(self, doi):
        datacite_url_endpoint = self.datacite_url + '/' + doi
        ids = []

        try:
            r = requests.get(datacite_url_endpoint)
            if r.status_code == 200:
                data = json.loads(r.content)
                alternate_ids = data.get('data').get('attributes').get('alternateIdentifiers')
                log.debug("alternateIdentifiers: {0}".format(alternate_ids))
                for alt_id in alternate_ids:
                    if alt_id.get('alternateIdentifierType') == 'URL':
                        url = alt_id.get('alternateIdentifier')
                        ids += [url.rsplit('/')[-1]]
                log.debug("Found published ids = [{0}] at {1}".format(', '.join(ids), datacite_url_endpoint))
                return ids
        except Exception as e:
            log.error("get_doi_identifiers FAILED, exception: {0}".format(e))

        return []

    def publish(self, doi, pkg=None, context={}, *args, **kwargs):

        update_doi = kwargs.get('update', False)

        # dataset data
        package_id = pkg['id']
        url = config.get('ckan.site_url', '') + '/dataset/' + pkg.get('name', pkg['id'])

        if self.url_prefix:
            url = self.url_prefix + pkg.get('name', pkg['id'])

        if update_doi:
            log.debug("*** Updating id = {0}, url = {1}".format(package_id, url))
            # check published data match
            published_ids = self.get_doi_identifiers(doi)
            if published_ids and package_id not in published_ids and pkg.get('name') not in published_ids:
                return None, 'Dataset id ({0}, {1}) do not match published ids: [{2}]'.format(package_id,
                                                                                              pkg.get('name'),
                                                                                              ', '.join(published_ids))
        else:
            log.debug(f"Publishing id = {package_id}, url = {url}")

        # get converted package
        metadata_format = 'datacite'

        try:
            converted_package = toolkit.get_action(
                'package_export')(
                context,
                {'id': package_id, 'format': metadata_format}
            )
        except toolkit.ObjectNotFound:
            log.debug("Failed exporting package metadata, dataset not found")
            return None, 'Dataset not found'

        xml = converted_package.replace('\n', '').replace('\t', '')
        log.debug(f"Package XML generated {xml}")

        # Validate        
        try:
            converted_record = XMLRecord.from_record(
                Record(MetadataFormats().get_metadata_formats(metadata_format)[0], xml))
            validation_result = converted_record.validate()
            log.debug(f"Validation successful: {validation_result}")
        except Exception as e:
            log.error(f"Converted Validation FAILED, exception: {e}")
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
        data['id'] = doi.strip()
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
        log.debug(f"Args JSON for datacite {args_json}")

        datacite_url_endpoint = self.datacite_url
        if update_doi:
            datacite_url_endpoint = self.datacite_url + '/' + doi
        log.debug(f"REST request send to URL: {datacite_url_endpoint}")

        if update_doi:
            r = requests.put(datacite_url_endpoint, headers=headers, auth=auth, data=args_json)
        else:
            r = requests.post(datacite_url_endpoint, headers=headers, auth=auth, data=args_json)

        if r.status_code == 201 or r.status_code == 200:
            published_doi = r.json().get('data').get('id')
            return published_doi, None
        else:
            if update_doi:
                msg = f"Error updating DataCite: HTTP Code: {r.status_code}, error: {r.json()}"
                log.debug(msg)
                return None, msg
            else:
                msg = f"Error publishing to DataCite: HTTP Code: {r.status_code}, error: {r.json()}"
                log.debug(msg)
                return None, msg

    def publish_resource(self, doi, resource=None, package={}, context={}, *args, **kwargs):

        # resource data
        id = resource.get('id')

        # update
        update_doi = kwargs.get('update', False)

        # dataset data
        package_id = package.get('name', package['id'])
        url = config.get('ckan.site_url', '') + url_for('dataset_resource.read', id=package_id, resource_id=id)
        log.debug("Resource original url is = {0}".format(url))

        if self.url_prefix:
            url = self.url_prefix + package_id

        if update_doi:
            log.debug("Updating resource id = {0}, url = {1}".format(id, url))
            # check published data match
            published_ids = self.get_doi_identifiers(doi)
            if id not in published_ids:
                return None, 'Resource id ({0}) do not match published ids: [{1}]'.format(id, ', '.join(published_ids))
        else:
            log.debug("Publishing resource id = {0}, url = {1}".format(id, url))

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
                return None, 'Error updating resource in DataCite: HTTP Code: {0}, error: {1}'.format(r.status_code, r.json())
            else:
                return None, 'Error publishing resource to DataCite: HTTP Code: {0}, error: {1}'.format(r.status_code, r.json())


    def __repr__(self):
        return str(self)

    def __str__(self):
        return str(self).encode('utf-8')

    def __unicode__(self):
        return u'DatacitePublisher: datacite_url=\'{0}\' '.format(self.datacite_url)
