# coding: utf8 


from ckan.common import c
import ckan.plugins.toolkit as toolkit

def datacite_publication_is_admin():

    username = c.user
   
    # Get user information
    context = {}
    context['ignore_auth'] = True
    user = toolkit.get_action('user_show')(context, {'id': username})

    return user.get('sysadmin', False)

def datacite_publication_doi_is_editable(data):
    if datacite_publication_is_admin():
        return True
    else:
        publication_state = data.get('publication_state', '').strip()
        return len(publication_state)<= 0