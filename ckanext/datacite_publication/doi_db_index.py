import sqlalchemy
import sys
import traceback

from ckantoolkit import config
import ckan.plugins as plugins

import logging
log = logging.getLogger(__name__)

class DataciteIndexDOI(plugins.SingletonPlugin):
    def __init__(self):
    
    
        self.prefix = config.get('datacite_publication.doi_prefix')    
        self.url = config.get('datacite_publication.sqlalchemy.url')
        self.site_id = config.get('datacite_publication.site_id')
        
        #TODO: check prefix exists
        
        self.con = sqlalchemy.create_engine(self.url, client_encoding='utf8')
        self.meta = sqlalchemy.MetaData(bind=self.con, reflect=True)

    def is_doi_valid(self, doi, ckan_id, entity='package'):
        prefix = doi.split('/',1)[0]
        suffix = doi.split('/',1)[1]
        doi_realisation = self.meta.tables['doi_realisation']

        log.debug('check_doi doi = {0}, ckan_id = {1}, entity = {2}, site_id = "{3}"'.format(doi, ckan_id, entity, self.site_id))

        clause = sqlalchemy.select([doi_realisation.c.prefix,
                                    doi_realisation.c.suffix]
                                   ).where(doi_realisation.c.site_id == self.site_id
                                   ).where(doi_realisation.c.ckan_entity == entity
                                   ).where(doi_realisation.c.ckan_id == ckan_id)
        results = self.con.execute(clause).fetchall()
        log.debug(results)
        if not results:
           log.warn('CKAN ID not found ({entity}): {ckan_id}'.format(entity=entity, ckan_id=ckan_id))
           return(False)

        for row in results:
            db_prefix=str(row[0][0])
            db_suffix=str(row[1])
            if(prefix==db_prefix) and (suffix==db_suffix):
                log.debug('Check CKAN ID-DOI OK!! {entity}: {prefix}/{suffix}: {ckan_id}'.format(
                                                      entity=entity,
                                                      prefix=db_prefix,
                                                      suffix=db_suffix, ckan_id=ckan_id))
                return True
            log.error('CKAN ID linked to another DOI: {prefix}/{suffix}: {ckan_id}'.format(prefix=db_prefix,
                                                     suffix=db_suffix,
                                                     ckan_id=ckan_id))
        return(False)

    def is_doi_existing(self, prefix, suffix):
 
        doi_realisation = self.meta.tables['doi_realisation']
        log.debug('is_doi_existing doi = {0}/{1}'.format(prefix, suffix))

        clause = sqlalchemy.select([doi_realisation.c.prefix_id,
                                    doi_realisation.c.suffix_id]
                                   ).where(doi_realisation.c.prefix_id == prefix
                                   ).where(doi_realisation.c.suffix_id == suffix)
        
        results = self.con.execute(clause).fetchall()

        if not results:
            log.debug('FALSE')
            return(False)
        else:
            log.debug('TRUE')
            return True


    def mint_doi(self, ckan_id, ckan_user, ckan_name, prefix = None, suffix = None, entity='package'):
    
        doi_realisation = self.meta.tables['doi_realisation']

        log.debug("mint_doi doi = {0}/{1}, ckan_id = {2}, entity = {3}, site_id = '{4}'".format(prefix, suffix, ckan_id, ckan_user,  entity, self.site_id))
        
        # check if already exists
        prefix_id = self.prefix
        if prefix:
            prefix_id = prefix
        
        if suffix:
            if self.is_doi_existing(prefix_id, suffix):
                error = "ERROR minting DOI: Already exists"
                log.error(error)
                return (None, error)
                
        # check if ckan_id already registered

        # insert row
        try:
            mint_insert = doi_realisation.insert().values(prefix_id=prefix_id, ckan_id=ckan_id , ckan_name=ckan_name, ckan_user=ckan_user, site_id=self.site_id, metadata = "pending")
        
            log.debug(mint_insert.compile().params)
            result = self.con.execute(mint_insert)
            inserted_primary_key = result.inserted_primary_key[0]
                
            clause = sqlalchemy.select([doi_realisation.c.prefix_id,
                                    doi_realisation.c.suffix_id]
                                   ).where(doi_realisation.c.doi_pk == inserted_primary_key)
        
            results = self.con.execute(clause).fetchall()
        except Exception as e:
            error = "Could not mint DOI, exception: " + str(e)
            traceback.print_exc()
            log.error(error)
            return(None, error)
        
        print(results)
        
        for result in results:
            doi = result[0] + '/' + result[1]
            log.debug("NEW DOI = " + doi)
            return(doi,None)
        
        error = "Could not retrieve inserted DOI"
        log.error(error)
        return(None, error)

    def __repr__(self):
        return str(self)

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __unicode__(self):
        return (u'IndexDOI({0}): \'{1}\' '.format(self.site_id, self.con))
