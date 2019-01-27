import sys
import traceback
import ckan.plugins.toolkit as toolkit
from pylons import config

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
        id = data_dict['id']
    except KeyError:
        raise toolkit.ValidationError({'id': 'missing id'})

    return("10.23456/test-doi")
