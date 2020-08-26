import sys
import traceback
import json

import ckan.plugins.toolkit as toolkit
import ckan.authz as authz
import ckan.lib.mailer as mailer
from ckan.common import _
from ckan.common import config
import importlib

import ckanext.datacite_publication.helpers as helpers

from ckanext.datacite_publication.datacite_publisher import DatacitePublisher

import logging
log = logging.getLogger(__name__)

DEAFULT_MINTER = 'ckanext.datacite_publication.minter.DatacitePublicationMinter'

REQUEST_MESSAGE = 'Datacite publication REQUESTED'
APPROVAL_MESSAGE = 'Datacite publication APPROVED'
FINISH_MESSAGE = 'Datacite publication FINISHED'

@toolkit.side_effect_free
def datacite_make_public_package(context, data_dict):
    '''Makes the dataset public (without a DOI request)
    :param id: the ID of the dataset
    :type id: string
    :returns: the package id
    :rtype: string
    '''
    log.debug("logic: datacite_make_public_package: {0}".format(data_dict.get('id')))
    return(_make_public(data_dict, context, type='package'))

@toolkit.side_effect_free
def datacite_publish_package(context, data_dict):
    '''Start the publication process for a dataset
       including the DOI request.
    :param id: the ID of the dataset
    :type id: string
    :returns: the package doi
    :rtype: string
    '''
    log.debug("logic: datacite_publish_package: {0}".format(data_dict.get('id')))
    return(_publish(data_dict, context, type='package'))

@toolkit.side_effect_free
def datacite_approve_publication_package(context, data_dict):
    '''Approve the publication process for a dataset
       by a portal admin.
    :param id: the ID of the dataset
    :type id: string
    :returns: the package doi
    :rtype: string
    '''
    log.debug("logic: datacite_approve_publication_package: {0}".format(data_dict.get('id')))
    return(_approve(data_dict, context, type='package'))

@toolkit.side_effect_free
def datacite_manual_finish_publication_package(context, data_dict):
    '''Finish manually the publication process for a dataset
       by a portal admin.
    :param id: the ID of the dataset
    :type id: string
    :returns: the package doi
    :rtype: string
    '''
    log.debug("logic: datacite_manual_finish_publication_package: {0}".format(data_dict.get('id')))
    return(_finish_manually(data_dict, context, type='package'))

@toolkit.side_effect_free
def datacite_finish_publication_package(context, data_dict):
    '''Finish the publication process for a dataset
       sending it to datacite API
       by a portal admin.
    :param id: the ID of the dataset
    :type id: string
    :returns: the package doi
    :rtype: string
    '''
    log.debug("logic: datacite_finish_publication_package: {0}".format(data_dict.get('id')))
    return(_publish_to_datacite(data_dict, context, type='package'))

@toolkit.side_effect_free
def datacite_update_publication_package(context, data_dict):
    '''Update the metadata for a dataset
       sending it to datacite API
       by a portal admin.
    :param id: the ID of the dataset
    :type id: string
    :returns: the package doi
    :rtype: string
    '''
    log.debug("logic: datacite_update_publication_package: {0}".format(data_dict.get('id')))
    return(_update_in_datacite(data_dict, context, type='package'))

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
    

def _make_public(data_dict, context, type='package'):

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
    
    # Check state
    if dataset_dict.get('publication_state', False):
        return {'success': False, 'error': 'Dataset publication state is not empty'}        
    
    # set as public
    dataset_dict['private'] = False
    toolkit.get_action('package_update')(context=context, data_dict=dataset_dict)

    log.info("success making public package {0}".format(package_id))
    return {'success': True, 'error': None}

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
        if helpers.datacite_publication_is_admin(ckan_user):
            return _publish_custom_by_admin(dataset_dict, package_id, ckan_user, context, type)
        else:
            return {'success': False, 'error': 'Dataset has already a DOI. Registering of custom DOI is currently not allowed'}

    # Check state
    if dataset_dict.get('publication_state', False):
        return {'success': False, 'error': 'Dataset publication state should be empty to request a new DOI'}        

    # mint doi mint_doi(self, ckan_id, ckan_user, prefix_id = None, suffix = None, entity='package')
    minter_name = config.get('datacite_publication.minter', DEAFULT_MINTER)
    package_name, class_name = minter_name.rsplit('.', 1)
    module = importlib.import_module(package_name)
    minter_class = getattr(module, class_name)
    minter = minter_class()
    
    prefix = config.get('datacite_publication.doi_prefix', '10.xxxxx')    

    doi, error = minter.mint(prefix, pkg = dataset_dict, user = ckan_user)
    
    log.debug("minter got doi={0}, error={1}".format(doi, error))
    
    if doi:
       # update dataset
       dataset_dict['doi'] = doi
       dataset_dict['private'] = False
       # TODO: check what is the proper state once workflow is complete
       #dataset_dict['publication_state'] = 'reserved'
       dataset_dict['publication_state'] = 'pub_pending'
       context['message'] = REQUEST_MESSAGE + " for dataset {0}".format(package_id)
       toolkit.get_action('package_update')(context=context, data_dict=dataset_dict)
       
       # notify admin and user
       datacite_publication_requested_mail(ckan_user, dataset_dict)
       
       log.info("success minting DOI for package {0}, doi {1}".format(package_id, doi))
       return {'success': True, 'error': None}
    else:
       log.error("error minting DOI for package {0}, error{1}".format(package_id, error))
       return {'success': False, 'error': error}
    
    return {'success': False, 'error': 'Internal error'}

def _publish_custom_by_admin(dataset_dict, package_id, ckan_user, context, type='package'):
    custom_doi = dataset_dict['doi']
    custom_prefix = custom_doi.split('/')[0].strip()
    try:
        custom_suffix = custom_doi.split('/')[1].strip()
    except:
        return {'success': False, 'error': 'Custom suffix not allowed'}  
          
    allowed_prefixes = config.get('datacite_publication.custom_prefix', '').split(' ')
    
    if custom_prefix not in allowed_prefixes:
        return {'success': False, 'error': 'Custom prefix not allowed'}
    
    log.info("publishing CUSTOM DOI by an Admin {0}, allowed: {1}".format(custom_doi, allowed_prefixes))
    
    # mint doi mint_doi(self, ckan_id, ckan_user, prefix_id = None, suffix = None, entity='package')
    minter_name = config.get('datacite_publication.minter', DEAFULT_MINTER)
    package_name, class_name = minter_name.rsplit('.', 1)
    module = importlib.import_module(package_name)
    minter_class = getattr(module, class_name)
    minter = minter_class()
    
    doi, error = minter.mint(custom_prefix, pkg = dataset_dict, user = ckan_user, suffix = custom_suffix)
    
    log.debug("minter got doi={0}, error={1}".format(doi, error))
    
    if doi:
       # update dataset
       dataset_dict['doi'] = doi
       dataset_dict['private'] = False
       # TODO: check what is the proper state once workflow is complete
       #dataset_dict['publication_state'] = 'reserved'
       dataset_dict['publication_state'] = 'pub_pending'
       context['message'] = REQUEST_MESSAGE + " for dataset {0}".format(package_id)
       toolkit.get_action('package_update')(context=context, data_dict=dataset_dict)
       
       # notify admin and user
       datacite_publication_requested_mail(ckan_user, dataset_dict)
       
       log.info("success minting DOI for package {0}, doi {1}".format(package_id, doi))
       return {'success': True, 'error': None}
    else:
       log.error("error minting DOI for package {0}, error{1}".format(package_id, error))
       return {'success': False, 'error': error.split('DETAIL')[0]}
    
    return {'success': False, 'error': 'Internal error'}
    
def _approve(data_dict, context, type='package'):
    
    log.debug('_approve: Approving "{0}" ({1})'.format(data_dict['id'], data_dict.get('name','')))
    # a dataset id i s necessary
    try:
        id_or_name = data_dict['id']
    except KeyError:
        raise toolkit.ValidationError({'id': 'missing id'})
    dataset_dict = toolkit.get_action('package_show')(context, {'id': id_or_name})
    
    # DOI has to be already reserved (minted)
    doi = dataset_dict.get('doi', '')
    default_prefix = config.get('datacite_publication.doi_prefix', '10.xxxxx')    
    allowed_prefixes = config.get('datacite_publication.custom_prefix', '').split(' ') + [ default_prefix ]

    log.debug('_approve: Doi "{0}" ({1})'.format(doi, ', '.join(allowed_prefixes)))

    doi_prefix = doi.split('/')[0].strip()
    
    if (not doi) or (len(doi) <=0) or (doi_prefix not in allowed_prefixes) :
        raise toolkit.ValidationError({'doi': 'dataset has no valid minted DOI [' + ', '.join(allowed_prefixes) + ']/*'})
    
    # Check authorization
    package_id = dataset_dict.get('package_id', dataset_dict.get('id', id_or_name))
    if not authz.is_authorized(
            'package_update', context,
            {'id': package_id}).get('success', False) or not helpers.datacite_publication_is_admin():
        log.error('ERROR approving dataset, current user is not authorized: isAdmin = {0}'.format(helpers.datacite_publication_is_admin()))
        raise toolkit.NotAuthorized({
                'permissions': ['Not authorized to approve the dataset (admin only).']})
    
    # change publication state
    dataset_dict['publication_state'] = 'approved'
    dataset_dict['private'] = False
    context['message'] = APPROVAL_MESSAGE + " for dataset {0}".format(package_id)
    toolkit.get_action('package_update')(context=context, data_dict=dataset_dict)
    
    # notify owner and involved users
    dataset_owner = dataset_dict.get('creator_user_id', '')
    datacite_approved_mail(dataset_owner, dataset_dict, context)

    return {'success': True, 'error': None}
    
def _finish_manually(data_dict, context, type='package'):
    
    log.debug('_finish_manually: Finishing "{0}" ({1})'.format(data_dict['id'], data_dict.get('name','')))
    # a dataset id i s necessary
    try:
        id_or_name = data_dict['id']
    except KeyError:
        raise toolkit.ValidationError({'id': 'missing id'})
    dataset_dict = toolkit.get_action('package_show')(context, {'id': id_or_name})
    
    # DOI has to be already reserved (minted)
    if not dataset_dict.get('doi', None):
        raise toolkit.ValidationError({'doi': 'dataset has no valid minted DOI'})
        
    # Check authorization
    package_id = dataset_dict.get('package_id', dataset_dict.get('id', id_or_name))
    if not authz.is_authorized(
            'package_update', context,
            {'id': package_id}).get('success', False) or not helpers.datacite_publication_is_admin():
        log.error('ERROR finishing publication dataset, current user is not authorized: isAdmin = {0}'.format(helpers.datacite_publication_is_admin()))
        raise toolkit.NotAuthorized({
                'permissions': ['Not authorized to finish manually the dataset publication (admin only).']})
    
    # change publication state
    dataset_dict['publication_state'] = 'published'
    dataset_dict['private'] = False
    context['message'] = FINISH_MESSAGE + " for dataset {0}".format(package_id)
    toolkit.get_action('package_update')(context=context, data_dict=dataset_dict)
    
    # notify owner and involved users
    dataset_owner = dataset_dict.get('creator_user_id', '')
    datacite_finished_mail(dataset_owner, dataset_dict, context)

    return {'success': True, 'error': None}
    
def _publish_to_datacite(data_dict, context, type='package'):
    
    log.debug('_publish_to_datacite: Publishing to datacite "{0}" ({1})'.format(data_dict['id'], data_dict.get('name','')))
    # a dataset id i s necessary
    try:
        id_or_name = data_dict['id']
    except KeyError:
        raise toolkit.ValidationError({'id': 'missing id'})
    dataset_dict = toolkit.get_action('package_show')(context, {'id': id_or_name})
    
    # state has to be approved
    state = dataset_dict.get('publication_state', '')
    if state != 'approved':
        raise toolkit.ValidationError({'publication_state': 'dataset needs to be in state "approved" (by the admin)'})
    
    # DOI has to be already reserved (minted)
    doi = dataset_dict.get('doi', '')
    default_prefix = config.get('datacite_publication.doi_prefix', '10.xxxxx')    
    allowed_prefixes = config.get('datacite_publication.custom_prefix', '').split(' ') + [ default_prefix ]
    doi_prefix = doi.split('/')[0].strip()
    
    if (not doi) or (len(doi) <=0) or (doi_prefix not in allowed_prefixes) :
        raise toolkit.ValidationError({'doi': 'dataset has no valid minted DOI [' + ', '.join(allowed_prefixes) + ']/*'})
    
    # Check authorization
    package_id = dataset_dict.get('package_id', dataset_dict.get('id', id_or_name))
    if not authz.is_authorized(
            'package_update', context,
            {'id': package_id}).get('success', False) or not helpers.datacite_publication_is_admin():
        log.error('ERROR finishing publication dataset in datacite, current user is not authorized: isAdmin = {0}'.format(helpers.datacite_publication_is_admin()))
        raise toolkit.NotAuthorized({
                'permissions': ['Not authorized to perform the dataset publication to datacite (admin only).']})
    
    datacite_publisher = DatacitePublisher()
    
    try:
        doi, error = datacite_publisher.publish(doi, pkg = dataset_dict, context = context)
    except Exception as e:
       log.error("exception publishing package {0} to Datacite, error {1}".format(package_id, traceback.format_exc()))
       return {'success': False, 'error': 'Exception when publishing to DataCite: {0}'.format(e)}
    except:
       log.error("error publishing package {0} to Datacite, error {1}".format(package_id, sys.exc_info()[0]))
       return {'success': False, 'error': 'Unknown error when publishing to DataCite: {0}'.format(sys.exc_info()[0])}
    
    if error:
       log.error("error publishing package {0} to Datacite, error {1}".format(package_id, error))
       return {'success': False, 'error': error}
    
    # change publication state
    dataset_dict['publication_state'] = 'published'
    dataset_dict['private'] = False
    context['message'] = FINISH_MESSAGE + " for dataset {0}".format(package_id)
    toolkit.get_action('package_update')(context=context, data_dict=dataset_dict)
    
    # notify owner and involved users
    dataset_owner = dataset_dict.get('creator_user_id', '')
    datacite_finished_mail(dataset_owner, dataset_dict, context)

    return {'success': True, 'error': None}

def _update_in_datacite(data_dict, context, type='package'):
    
    log.debug('_update_in_datacite: Updating in datacite "{0}" ({1})'.format(data_dict['id'], data_dict.get('name','')))
    # a dataset id i s necessary
    try:
        id_or_name = data_dict['id']
    except KeyError:
        raise toolkit.ValidationError({'id': 'missing id'})
    dataset_dict = toolkit.get_action('package_show')(context, {'id': id_or_name})
    
    # state has to be approved
    state = dataset_dict.get('publication_state', '')
    if state != 'published':
        raise toolkit.ValidationError({'publication_state': 'dataset needs to be in state "published" (in datacite)'})
    
    # DOI has to be already present
    doi = dataset_dict.get('doi', '')
    default_prefix = config.get('datacite_publication.doi_prefix', '10.xxxxx')    
    allowed_prefixes = config.get('datacite_publication.custom_prefix', '').split(' ') + [ default_prefix ]
    doi_prefix = doi.split('/')[0].strip()
    
    if (not doi) or (len(doi) <=0) or (doi_prefix not in allowed_prefixes) :
        raise toolkit.ValidationError({'doi': 'dataset has no valid minted DOI [' + ', '.join(allowed_prefixes) + ']/*'})
    
    # Check authorization
    package_id = dataset_dict.get('package_id', dataset_dict.get('id', id_or_name))
    if not authz.is_authorized(
            'package_update', context,
            {'id': package_id}).get('success', False) or not helpers.datacite_publication_is_admin():
        log.error('ERROR updating publication dataset in datacite, current user is not authorized: isAdmin = {0}'.format(helpers.datacite_publication_is_admin()))
        raise toolkit.NotAuthorized({
                'permissions': ['Not authorized to perform the dataset update to datacite (admin only).']})
    
    datacite_publisher = DatacitePublisher()
    
    try:
        doi, error = datacite_publisher.publish(doi, pkg = dataset_dict, context = context, update = True )
    except Exception as e:
       log.error("exception updating package {0} in Datacite, error {1}".format(package_id, traceback.format_exc()))
       return {'success': False, 'error': 'Exception when updating in DataCite: {0}'.format(e)}
    except:
       log.error("error updating package {0} in Datacite, error {1}".format(package_id, sys.exc_info()[0]))
       return {'success': False, 'error': 'Unknown error when updating in DataCite: {0}'.format(sys.exc_info()[0])}
    
    if error:
       log.error("error updating package {0} to Datacite, error {1}".format(package_id, error))
       return {'success': False, 'error': error}
    
    return {'success': True, 'error': None}

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
def datacite_publication_requested_mail(user_id, entity, user_email='', entity_type='package'):

    try:
        log.debug('datacite_publication_requested_mail: Notifying request from "{0}" ({1})'.format(user_id, entity.get('name','')))

        # Get admin data
        admin_name = _('CKAN System Administrator')
        admin_email = config.get('email_to')
        if not admin_email:
            raise mailer.MailerException('Missing "email-to" in config')

        # Entity info
        entity_id = entity['id']
        entity_name = entity['name']
        
        # Get user information
        user = _get_user_info(user_id)
        user_email = user['email']
        user_name = user.get('display_name', user['name'])

        body =  u"Notifying publication request to {0} ({1}): \n".format(admin_name, admin_email)
        body += u"\t - User: {0} ({1})\n".format(user_name, user_email)
        body += u"\t - Entity: {0} ({1})\n".format(entity_name, entity_type)
        body += u"\t - URL: {0} \n".format(_get_entity_url(entity, entity_type=entity_type))
        subject = _('Publication Request {0}').format(entity_name)

        # Send copy to admin
        mailer.mail_recipient(admin_name, admin_email, subject, body)
        
        # Send copy to user
        if not user_email:
            raise mailer.MailerException('Missing user email')
        body += u"\n\n * Your DOI request is being processed by the EnviDat team. The DOI is reserved but it will not be valid until the registration process is finished. *"
        
    except Exception as e:
        log.error((u'datacite_publication_requested_mail: '
                     u'Failed to send mail to admin from "{0}": {1}').format(user_id,e))

# send email to user on publication approval
def datacite_approved_mail(user_id, entity, context, user_email='', entity_type='package'):

    try:
        log.debug(u'datacite_approved_mail: Notifying approval for dataset {0}'.format(entity.get('name','')))

        # keep track of sent mails
        sent_mails = []
        
        # Entity info
        entity_id = entity['id']
        entity_name = entity['name']
        entity_doi = entity['doi']
        
        # Get admin data
        admin_name = config.get('site_title', 'CKAN') + ' '  + _('Administrator')
        admin_email = config.get('email_to')

        # Get user information
        user = _get_user_info(user_id)
        if not user_email:
            user_email = user['email']
        user_name = user.get('display_name', user['name'])
        
        # get the mail content
        body =  u"Notifying publication approval from {0} ({1}): \n".format(admin_name, admin_email)
        body += u"\t - User: {0} ({1})\n".format(user_name, user_email)
        body += u"\t - Entity: {0} ({1})\n".format(entity_name, entity_type)
        body += u"\t - URL: {0} \n".format(_get_entity_url(entity, entity_type=entity_type))
        body += u"\t - DOI: https://doi.org/{0} ".format(entity_doi)
        subject = _('Publication Approved {0}').format(entity_name)

        # Send mail to user who requested the publication
        user_request = _get_user_request(entity_id, context)
        if user_request:
            log.debug(u'Requesting author was {0}'.format(user_request.get('display_name')))
            if user_request['email'] not in sent_mails:
                mailer.mail_recipient(user_request.get('display_name', user_request['name']), user_request['email'], subject, body)
                sent_mails += [user_request['email']]
         
        # Send copy to admin
        if admin_email and admin_email not in sent_mails:
            mailer.mail_recipient(admin_name, admin_email, subject, "\t ** COPY ** \n\n" + body)
            sent_mails += [admin_email]
        
        # Send copy to dataset owner (?)
        if user_email and user_email not in sent_mails:
            mailer.mail_recipient(user_name, user_email, subject, body)
            sent_mails += [user_email]
           
        # Send copy to dataset contact point
        if entity.get("maintainer_email") and entity.get("maintainer_email") not in sent_mails:
            mailer.mail_recipient("Dataset Contact Point", entity.get("maintainer_email"), subject, "\t ** COPY ** \n\n" + body)
            sent_mails += [entity.get("maintainer_email")]
        else:
            maintainer_object = json.loads(entity.get("maintainer", "{}"))
            maintainer_email = maintainer_object.get("email")
            maintainer_name = maintainer_object.get("name", "Dataset Contact Point")
            if maintainer_email and maintainer_email not in sent_mails:
                # TODO: Temporary disabled this for testing
                log.debug("skipping mail sending to {0}".format(maintainer_email))
                # mailer.mail_recipient(maintainer_name, maintainer_email, subject, "\t ** COPY ** \n\n" + body)
                sent_mails += [maintainer_email]
        log.debug("Publication finishing mail sent to: {0}".format(','.join(sent_mails)))
    except Exception as e:
        log.error(('datacite_approved_mail: '
                     'Failed to send mail to user "{0}": {1}, {2}').format(user_id,e, traceback.format_exc().splitlines()))

# send email to user on publication finishing
def datacite_finished_mail(user_id, entity, context, user_email='', entity_type='package'):

    try:
        log.debug('datacite_finished_mail: Notifying finishined publication of dataset {0}'.format(entity.get('name','')))

        # keep track of sent mails
        sent_mails = []
        
        # Entity info
        entity_id = entity['id']
        entity_name = entity['name']
        entity_doi = entity['doi']
        
        # Get admin data
        admin_name = config.get('site_title', 'CKAN') + ' '  + _('Administrator')
        admin_email = config.get('email_to')

        # Get user information
        user = _get_user_info(user_id)
        if not user_email:
            user_email = user['email']
        user_name = user.get('display_name', user['name'])
        
        # get the mail content
        body =  u"Notifying publication finishing from {0} ({1}): \n".format(admin_name, admin_email)
        body += u"\t - User: {0} ({1})\n".format(user_name, user_email)
        body += u"\t - Entity: {0} ({1})\n".format(entity_name, entity_type)
        body += u"\t - URL: {0} \n".format(_get_entity_url(entity, entity_type=entity_type))
        body += u"\t - DOI: https://doi.org/{0} ".format(entity_doi)
        subject = _('Publication Finished {0}').format(entity_name)

        # Send mail to user who requested the publication
        user_request = _get_user_request(entity_id, context)
        if user_request:
            log.debug(u'Requesting author was {0}'.format(user_request.get('display_name')))
            if user_request['email'] not in sent_mails:
                mailer.mail_recipient(user_request.get('display_name', user_request['name']), user_request['email'], subject, body)
                sent_mails += [user_request['email']]
         
        # Send copy to admin
        if admin_email and admin_email not in sent_mails:
            mailer.mail_recipient(admin_name, admin_email, subject, "\t ** COPY ** \n\n" + body)
            sent_mails += [admin_email]
        
        # Send copy to dataset owner (?)
        if user_email and user_email not in sent_mails:
            mailer.mail_recipient(user_name, user_email, subject, body)
            sent_mails += [user_email]
           
        # Send copy to dataset contact point
        if entity.get("maintainer_email") and entity.get("maintainer_email") not in sent_mails:
            mailer.mail_recipient("Dataset Contact Point", entity.get("maintainer_email"), subject, "\t ** COPY ** \n\n" + body)
            sent_mails += [entity.get("maintainer_email")]
        else:
            maintainer_object = json.loads(entity.get("maintainer", "{}"))
            maintainer_email = maintainer_object.get("email")
            maintainer_name = maintainer_object.get("name", "Dataset Contact Point")
            if maintainer_email and maintainer_email not in sent_mails:
                # TODO: Temporary disabled this for testing
                log.debug(u"skipping mail sending to {0}".format(maintainer_email))
                #mailer.mail_recipient(maintainer_name, maintainer_email, subject, "\t ** COPY ** \n\n" + body)
                sent_mails += [maintainer_email]
        log.debug(u"Publication finishing mail sent to: {0}".format(','.join(sent_mails)))
    except Exception as e:
        log.error(('datacite_finished_mail: '
                     'Failed to send mail to user "{0}": {1}, {2}').format(user_id,e, traceback.format_exc().splitlines()))

def _get_entity_url(entity, entity_type='package'):
    # Entity info
    site_url = config.get('ckan.site_url', 'ckan_url')
    entity_id = entity['id']
    entity_name = entity['name']
    entity_doi = entity['doi']
    if entity_type == 'package' :
        entity_url = '/'.join([site_url,'dataset', entity_name])
    else:
        entity_url = '/'.join([site_url,'resource', entity_id])
    return entity_url

def _get_user_info(user_id):
    context = {}
    context['ignore_auth'] = True
    context['keep_email'] = True
    user = toolkit.get_action('user_show')(context, {'id': user_id})
    return user
    
def _get_user_request(entity_id, context):
    try:
        revisions_list = toolkit.get_action('package_activity_list')(context, {'id': entity_id})
        for revision in revisions_list:
            revision_message = revision.get('message', '')
            if revision_message.lower().find(REQUEST_MESSAGE.lower()) >= 0:
                user_request_name = revision.get('author')
                user_request = toolkit.get_action('user_show')(context, {'id': user_request_name})
                return user_request
    except Exception as e:
        log.error((u'_get_user_request: '
                     u'Failed to find requester user for publication of "{0}": {1}, {2}')
                        .format(entity_id, e , '\n'.join(traceback.format_exc().splitlines())))
    return None

