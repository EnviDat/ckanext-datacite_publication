import sys
import traceback
import ckan.plugins.toolkit as toolkit
import ckan.authz as authz

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
    
    # mint doi mint_doi(self, ckan_id, ckan_user, prefix_id = None, suffix = None, entity='package')
    doi_index = DataciteIndexDOI()
    doi, error = doi_index.mint_doi( ckan_id=package_id, ckan_user=ckan_user, ckan_name=dataset_dict.get('name', "None"))
    
    if doi:
       # update dataset
       dataset_dict['doi'] = doi
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
    
