import ckan.plugins.toolkit as toolkit
import ckan.model as model
import ckan.lib.base as base
import ckan.lib.helpers as h

render = base.render

from logging import getLogger

log = getLogger(__name__)

class DatacitePublicationController(toolkit.BaseController):

    def publish_package(self, package_id):
        '''Start publication process for a dataset.
        '''
        context = {
            'model': model,
            'session': model.Session,
            'user': toolkit.c.user,
        }

        try:
            result = toolkit.get_action(
                'datacite_publish_package')(
                context,
                {'id': package_id}
            )
        except toolkit.ObjectNotFound:
            toolkit.abort(404, 'Dataset not found')
        except toolkit.NotAuthorized:
            toolkit.abort(403, 'Not authorized')

        if result.get('success', True):
            h.flash_notice('DOI successfully reserved. Your publication request will be approved by an EnviDat admin as soon as possible.')
        else:
            error_message = 'Error publishing dataset: \n' + result.get('error', 'Internal Exception, please contact the portal admin.')
            h.flash_error(error_message)
            #toolkit.abort(500, error_message)
        return toolkit.redirect_to(controller='package', action='read',
                            id=package_id)
   
    def approve_publication_package(self, package_id):
        '''Approve publication process for a dataset by the admin.
        '''
        context = {
            'model': model,
            'session': model.Session,
            'user': toolkit.c.user,
        }

        log.debug("controller: approve_publication_package: {0}".format(package_id))
        
        try:
            result = toolkit.get_action(
                'approve_publication_package')(
                context,
                {'id': package_id}
            )
        except toolkit.ObjectNotFound:
            toolkit.abort(404, 'Dataset not found')
        except toolkit.NotAuthorized:
            toolkit.abort(403, 'Not authorized')
        except toolkit.ValidationError:
            toolkit.abort(400, 'Validation error')

        if result.get('success', True):
            h.flash_notice('DOI publication approved.')
        else:
            error_message = 'Error approving dataset publication: \n' + result.get('error', 'Internal Exception, please contact the portal admin.')
            h.flash_error(error_message)
            #toolkit.abort(500, error_message)
        return toolkit.redirect_to(controller='package', action='read',
                            id=package_id)
    
    def manual_finish_publication_package(self, package_id):
        '''Finish manually the publication process for a dataset by the admin.
        '''
        context = {
            'model': model,
            'session': model.Session,
            'user': toolkit.c.user,
        }

        log.debug("controller: manual_finish_publication_package: {0}".format(package_id))
        
        try:
            result = toolkit.get_action(
                'manual_finish_publication_package')(
                context,
                {'id': package_id}
            )
        except toolkit.ObjectNotFound:
            toolkit.abort(404, 'Dataset not found')
        except toolkit.NotAuthorized:
            toolkit.abort(403, 'Not authorized')
        except toolkit.ValidationError:
            toolkit.abort(400, 'Validation error')

        if result.get('success', True):
            h.flash_notice('DOI publication finished.')
        else:
            error_message = 'Error finishing dataset publication: \n' + result.get('error', 'Internal Exception, please contact the portal admin.')
            h.flash_error(error_message)
            #toolkit.abort(500, error_message)
        return toolkit.redirect_to(controller='package', action='read',
                            id=package_id)
    
    
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
