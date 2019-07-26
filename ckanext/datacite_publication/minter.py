from ckantoolkit import config
import ckan.plugins as plugins
import uuid

import logging
log = logging.getLogger(__name__)

class DatacitePublicationMinter(plugins.SingletonPlugin):

    def mint(self, prefix, pkg = None, *args, **kwargs):
        error = None
        doi = prefix + '/' + str(uuid.uuid4())
        return(doi, error)

    def __repr__(self):
        return str(self)

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __unicode__(self):
        return (u'DatacitePublicationMinter')
