from ckan import model
import ckan.plugins.toolkit as toolkit
from ckan.common import g
import ckan.lib.base as base
import ckan.lib.helpers as h

from flask import Blueprint, request

from logging import getLogger

log = getLogger(__name__)
render = base.render


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
        u'/dataset/<dataset_id>/resource/<id>/publish/datacite',
        u'publish_resource',
        publish_resource
    )

    return blueprint


def _get_context():
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
        error_message = 'Error approving dataset publication: \n' + result.get('error', 'Internal Exception, please '
                                                                                        'contact the portal admin.')
        h.flash_error(error_message)
        # toolkit.abort(500, error_message)
    return toolkit.redirect_to(controller='dataset', action='read',
                               id=id)


def manual_finish_publication_package(id):
    """Finish manually the publication process for a dataset by the admin.
    """
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
    """Finish the publication process for a dataset by the admin through the datacite API.
    """
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
    """Update the metadata for a dataset by the admin through the datacite API.
    """
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


def publish_resource(dataset_id, id):
    """Publish a resource with a custom DOI by an admin (manually minted).
    """
    context = _get_context()

    log.debug("controller: publish_resource: ({0}) {1}".format(dataset_id, id))

    update = request.args.get('update', 'false').lower() == 'true'

    try:
        result = toolkit.get_action(
            'datacite_publish_resource')(
            context,
            {'id': id, 'package_id': dataset_id, 'update': update}
        )
    except toolkit.ObjectNotFound:
        toolkit.abort(404, 'Dataset/resource not found')
    except toolkit.NotAuthorized:
        toolkit.abort(403, 'Not authorized')
    except toolkit.ValidationError:
        toolkit.abort(400, 'Validation error')

    if result.get('success', True):
        if update:
            h.flash_notice('DOI publication update finished.')
        else:
            h.flash_notice('DOI publication finished.')
    else:
        error_message = 'Error publishing resource: \n' + result.get('error',
                                                                     'Internal Exception, please contact'
                                                                     ' the portal admin.')
        h.flash_error(error_message)

    return toolkit.redirect_to(controller='resource', action='read',
                               id=dataset_id, resource_id=id)
