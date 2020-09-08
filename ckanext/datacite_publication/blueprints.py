from ckan import model
import ckan.plugins.toolkit as toolkit
import ckan.logic
from ckan.common import g
import ckanext.datacite_publication.logic as logic
from flask import Blueprint

import ckan.lib.base as base
import ckan.lib.helpers as h

render = base.render

from logging import getLogger

log = getLogger(__name__)


def get_blueprints(name, module):
    # Create Blueprint for plugin
    blueprint = Blueprint(name, module)

    blueprint.add_url_rule(
        # 'make_public_package',
        '/dataset/<id>/make_public/datacite',
        'make_public_package',
        make_public_package
    )

    blueprint.add_url_rule(
        # 'publish_package',
        '/dataset/<id>/publish/datacite',
        'publish_package',
        publish_package
    )

    blueprint.add_url_rule(
        u"/dataset/<id>/approve_publication/datacite",
        u"approve_publication_package",
        approve_publication_package
    )

    blueprint.add_url_rule(
        #'manual_finish_publication_package',
        u'/dataset/<id>/manual_finish_publication/datacite',
        u'manual_finish_publication_package',
        manual_finish_publication_package
    )
    blueprint.add_url_rule(
        # 'finish_publication_package',
        u'/dataset/<id>/finish_publication_package/datacite',
        u'finish_publication_package',
        finish_publication_package
    )
    blueprint.add_url_rule(
        # 'update_publication_package',
        u'/dataset/<id>/update_publication_package/datacite',
        u'update_publication_package',
        update_publication_package
    )
    blueprint.add_url_rule(
        # 'publish_resource',
        u'/dataset/<id>/resource/{resource_id}/publish/datacite',
        u'publish_resource',
        publish_resource
    )

    return blueprint


def _get_context():
    site_user = ckan.logic.get_action(u"get_site_user")({u"ignore_auth": True}, {})
    log.debug("blueprints._get_context USER = {0}".format(site_user))
    return {u"model": model, u"session": model.Session,
            u"user": g.user,
            u"ignore_auth": False}


def make_public_package(id):
    context = _get_context()

    try:
        result = toolkit.get_action(
            'datacite_make_public_package')(
            context,
            {'id': id}
        )
    except toolkit.ObjectNotFound:
        toolkit.abort(404, 'Dataset not found')
    except toolkit.NotAuthorized:
        toolkit.abort(403, 'Not authorized')

    if result.get('success', True):
        h.flash_notice('Dataset is now public.')
    else:
        error_message = 'Error making dataset public: \n' + result.get('error',
                                                                       'Internal Exception, please contact the portal '
                                                                       'admin.')
        h.flash_error(error_message)
    return toolkit.redirect_to(controller='dataset', action='read',
                               id=id)


def publish_package(id):
    context = _get_context()

    try:
        result = toolkit.get_action(
            'datacite_publish_package')(
            context,
            {'id': id}
        )
    except toolkit.ObjectNotFound:
        toolkit.abort(404, 'Dataset not found')
    except toolkit.NotAuthorized:
        toolkit.abort(403, 'Not authorized')

    if result.get('success', True):
        h.flash_notice(
            'DOI successfully reserved. Your publication request will be approved by an EnviDat admin as soon as '
            'possible.')
    else:
        error_message = 'Error publishing dataset: \n' + result.get('error',
                                                                    'Internal Exception, please contact the portal '
                                                                    'admin.')
        h.flash_error(error_message)
        # toolkit.abort(500, error_message)
    return toolkit.redirect_to(controller='dataset', action='read',
                               id=id)


def approve_publication_package(id):
    context = _get_context()

    log.debug("controller: approve_publication_package: {0}".format(id))

    try:
        result = toolkit.get_action(
            'datacite_approve_publication_package')(
            context,
            {'id': id}
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
        error_message = 'Error approving dataset publication: \n' + result.get('error',
                                                                               'Internal Exception, please contact the portal admin.')
        h.flash_error(error_message)
        # toolkit.abort(500, error_message)
    return toolkit.redirect_to(controller='dataset', action='read',
                               id=id)


def manual_finish_publication_package(id):
    '''Finish manually the publication process for a dataset by the admin.
    '''
    context = _get_context()

    log.debug("controller: manual_finish_publication_package: {0}".format(id))

    try:
        result = toolkit.get_action(
            'datacite_manual_finish_publication_package')(
            context,
            {'id': id}
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
        error_message = 'Error finishing dataset publication: \n' + result.get('error',
                                                                               'Internal Exception, please contact '
                                                                               'the portal admin.')
        h.flash_error(error_message)
        # toolkit.abort(500, error_message)
    return toolkit.redirect_to(controller='dataset', action='read',
                               id=id)


def finish_publication_package(id):
    '''Finish the publication process for a dataset by the admin through the datacite API.
    '''
    context = _get_context()

    log.debug("controller: finish_publication_package: {0}".format(id))

    try:
        result = toolkit.get_action(
            'datacite_finish_publication_package')(
            context,
            {'id': id}
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
        error_message = 'Error finishing dataset publication: \n' + result.get('error',
                                                                               'Internal Exception, please contact the portal admin.')
        h.flash_error(error_message)
        # toolkit.abort(500, error_message)
    return toolkit.redirect_to(controller='dataset', action='read',
                               id=id)


def update_publication_package(id):
    '''Update the metadata for a dataset by the admin through the datacite API.
    '''
    context = _get_context()

    log.debug("controller: update_publication_package: {0}".format(id))

    try:
        result = toolkit.get_action(
            'datacite_update_publication_package')(
            context,
            {'id': id}
        )
    except toolkit.ObjectNotFound:
        toolkit.abort(404, 'Dataset not found')
    except toolkit.NotAuthorized:
        toolkit.abort(403, 'Not authorized')
    except toolkit.ValidationError:
        toolkit.abort(400, 'Validation error')

    if result.get('success', True):
        h.flash_notice('DOI metadat updated.')
    else:
        error_message = 'Error updating dataset: \n' + result.get('error',
                                                                  'Internal Exception, please contact the portal admin.')
        h.flash_error(error_message)
        # toolkit.abort(500, error_message)
    return toolkit.redirect_to(controller='dataset', action='read',
                               id=id)


def publish_resource(id):
    '''Start publication process for a resource.
    '''

    context = _get_context()

    r = toolkit.response
    r.content_disposition = 'attachment; filename=' + id + '_DOI.txt'

    try:
        published_resource = toolkit.get_action(
            'datacite_publish_resource')(
            context,
            {'id': id}
        )
    except toolkit.ObjectNotFound:
        toolkit.abort(404, 'Dataset not found')
    except toolkit.NotAuthorized:
        toolkit.abort(403, 'Not authorized')

    return published_resource
