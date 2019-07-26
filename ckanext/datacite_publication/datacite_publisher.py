from ckantoolkit import config
import ckan.plugins as plugins

import logging
log = logging.getLogger(__name__)

class DatacitePublisher(plugins.SingletonPlugin):

    def __init__(self):
        self.datacite_url = config.get('datacite_publication.datacite_url','')

    def publish(self, doi, pkg = None, *args, **kwargs):
        #error = None
        error = "Datacite publishing implementation pending"
        return(doi, error)

    def __repr__(self):
        return str(self)

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __unicode__(self):
        return (u'DatacitePublisher: datacite_url=\'{0}\' '.format(self.datacite_url))
