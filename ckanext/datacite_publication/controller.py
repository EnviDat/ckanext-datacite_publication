import ckan.plugins.toolkit as toolkit
import ckan.model as model

from logging import getLogger

log = getLogger(__name__)

class DatacitePublicationController(toolkit.BaseController):

    def publish_package(self, package_id):
        '''Start publication process for a dataset.
        '''
        log.debug(" ******** PUBLISH PACKAGE ********* ")
        context = {
            'model': model,
            'session': model.Session,
            'user': toolkit.c.user,
        }
        r = toolkit.response
        r.content_disposition = 'attachment; filename=' + package_id + '_DOI.txt'

        try:
            published_package = toolkit.get_action(
                'datacite_publish_package')(
                context,
                {'id': package_id}
            )
        except toolkit.ObjectNotFound:
            toolkit.abort(404, 'Dataset not found')
        except toolkit.NotAuthorized:
            toolkit.abort(403, 'Not authorized')

        return published_package

    def publish_resource(self, resource_id):
        '''Start publication process for a resource.
        '''

        context = {
            'model': model,
            'session': model.Session,
            'user': toolkit.c.user,
        }
        r = toolkit.response
        r.content_disposition = 'attachment; filename=' + resource_id + '_DOI.txt'

        try:
            published_resource = toolkit.get_action(
                'datacite_publish_resource')(
                context,
                {'id': resource_id}
            )
        except toolkit.ObjectNotFound:
            toolkit.abort(404, 'Dataset not found')
        except toolkit.NotAuthorized:
            toolkit.abort(403, 'Not authorized')

        return published_resource
