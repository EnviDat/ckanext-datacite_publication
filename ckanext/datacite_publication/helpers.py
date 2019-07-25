# coding: utf8

from ckan.common import c
import ckan.plugins.toolkit as toolkit


from logging import getLogger
log = getLogger(__name__)

def datacite_publication_is_admin(name=None):

    username = name
    if not name:
        username = c.user

    if not username or len(name.strip())<1:
        return False

    # Get user information
    context = {}
    context['ignore_auth'] = True

    try:
        user = toolkit.get_action('user_show')(context, {'id': username})
    except:
        log.error("Exception getting user for username " + str(username))
        return False

    return user.get('sysadmin', False)

def datacite_publication_doi_is_editable(data):
    if datacite_publication_is_admin():
        return True
    else:
        publication_state = data.get('publication_state', '').strip()
        return len(publication_state)<= 0
