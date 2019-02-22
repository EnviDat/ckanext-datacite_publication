import sys
import traceback

import ckan.plugins.toolkit as toolkit
import ckan.authz as authz
import ckan.lib.mailer as mailer
from ckan.common import _
from ckan.common import config

import logging
log = logging.getLogger(__name__)

from doi_db_index import DataciteIndexDOI

@toolkit.side_effect_free
def datacite_publish_package(context, data_dict):
    '''Start the publication process for a dataset
       including the DOI request.
    :param id: the ID of the dataset
    :type id: string
    :returns: the package doi
    :rtype: string
    '''

    return(_publish(data_dict, context, type='package'))

@toolkit.side_effect_free
def datacite_publish_resource(context, data_dict):
    '''Start the publication process for a resource
       including the DOI request.
    :param id: the ID of the resource
    :type id: string
    :returns: the resource doi
    :rtype: string
    '''

    return(_publish(data_dict, context, type='resource'))

def _publish(data_dict, context, type='package'):

    try:
        id_or_name = data_dict['id']
    except KeyError:
        raise toolkit.ValidationError({'id': 'missing id'})
    
    dataset_dict = toolkit.get_action('package_show')(context, {'id': id_or_name})
    
    # Check authorization
    package_id = dataset_dict.get('package_id', dataset_dict.get('id', id_or_name))
    if not authz.is_authorized(
            'package_update', context,
            {'id': package_id}).get('success', False):
        raise toolkit.NotAuthorized({
                'permissions': ['Not authorized to publish the dataset.']})
    
    # get user
    ckan_user = _get_username_from_context(context)
    
    # check if dataset has a DOI already
    existing_doi = dataset_dict.get('doi')
    if existing_doi:
        return {'success': False, 'error': 'Dataset has already a DOI. Registering of custom DOI is currently not allowed'}

	# TODO: get package name and metadata
	
    # notify admin
    datacite_publication_mail_admin(ckan_user, dataset_dict)
    
    # mint doi mint_doi(self, ckan_id, ckan_user, prefix_id = None, suffix = None, entity='package')
    doi_index = DataciteIndexDOI()
    doi, error = doi_index.mint_doi( ckan_id=package_id, ckan_user=ckan_user, ckan_name=dataset_dict.get('name', "None"))
    
    if doi:
       # update dataset
       dataset_dict['doi'] = doi
       dataset_dict['private'] = False
       dataset_dict['publication_state'] = 'reserved'
       toolkit.get_action('package_update')(data_dict=dataset_dict)
       return {'success': True, 'error': None}
    else:
       return {'success': False, 'error': error}
        
    
    return

def _get_username_from_context(context):
    auth_user_obj = context.get('auth_user_obj', None)
    user_name = ''
    if auth_user_obj:
        user_name = auth_user_obj.as_dict().get('name', '')
    else:
        if authz.get_user_id_for_username(context.get('user'), allow_none=True):
            user_name = context.get('user', '')
    return user_name
    
# send email to admin on publication request
def datacite_publication_mail_admin(user_id, entity, entity_type='package'):

    try:
        log.debug('datacite_publication_mail_admin: Notifying request from "{0}" ({1})'.format(user_id, entity.get('name','')))

        # Get admin data
        admin_name = _('CKAN System Administrator')
        admin_email = config.get('email_to')
        if not admin_email:
            raise mailer.MailerException('Missing "email-to" in config')

        # Entity info
        site_url = config.get('ckan.site_url', 'ckan_url')
        entity_id = entity['id']
        entity_name = entity['name']
        if entity_type == 'package' :
            entity_url = '/'.join([site_url,'dataset', entity_id])
        else:
            entity_url = '/'.join([site_url,'resource', entity_id])
        
        # Get user information
        context = {}
        context['ignore_auth'] = True
        context['keep_email'] = True
        user = toolkit.get_action('user_show')(context, {'id': user_id})
        user_email = user['email']
        user_name = user.get('display_name', user['name'])

        body =  "Notifying publication request: \n"
        body += "\t - User: {0} ({1})\n".format(user_name, user_email)
        body += "\t - Entity: {0} ({1})\n".format(entity_name, entity_type)
        body += "\t - URL: {0} ".format(entity_url)
        subject = _('Publication Request {}').format(entity_name)

        # Send copy to admin
        mailer.mail_recipient(admin_name, admin_email, subject, body)
        
    except Exception as e:
        log.error(('datacite_publication_mail_admin: '
                     'Failed to send mail to admin from "{0}": {1}').format(user_id,e))

