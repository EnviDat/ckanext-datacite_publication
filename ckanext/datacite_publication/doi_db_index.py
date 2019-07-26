import sqlalchemy
import sys
import traceback
import json

from ckantoolkit import config
import ckan.plugins as plugins

from ckanext.datacite_publication.minter import DatacitePublicationMinter

import logging
log = logging.getLogger(__name__)

class DataciteIndexDOI(DatacitePublicationMinter):
    def __init__(self):
    
        self.prefix = config.get('datacite_publication.doi_prefix')    
        self.url = config.get('datacite_publication.sqlalchemy.url')
        self.site_id = config.get('datacite_publication.site_id')
        
        #TODO: check prefix exists
        self.con = sqlalchemy.create_engine(self.url, client_encoding='utf8')
        self.meta = sqlalchemy.MetaData(bind=self.con, reflect=True)

    def is_doi_valid(self, doi, ckan_id, entity_type='package'):
        prefix = doi.split('/',1)[0]
        suffix = doi.split('/',1)[1]
        doi_realisation = self.meta.tables['doi_realisation']

        log.debug('check_doi doi = {0}, ckan_id = {1}, entity_type = {2}, site_id = "{3}"'.format(doi, ckan_id, entity_type, self.site_id))

        clause = sqlalchemy.select([doi_realisation.c.prefix,
                                    doi_realisation.c.suffix]
                                   ).where(doi_realisation.c.site_id == self.site_id
                                   ).where(doi_realisation.c.ckan_entity == entity_type
                                   ).where(doi_realisation.c.ckan_id == ckan_id)
        results = self.con.execute(clause).fetchall()
        log.debug(results)
        if not results:
           log.warn('CKAN ID not found ({entity_type}): {ckan_id}'.format(entity_type=entity_type, ckan_id=ckan_id))
           return(False)

        for row in results:
            db_prefix=str(row[0][0])
            db_suffix=str(row[1])
            if(prefix==db_prefix) and (suffix==db_suffix):
                log.debug('Check CKAN ID-DOI OK!! {entity_type}: {prefix}/{suffix}: {ckan_id}'.format(
                                                      entity_type=entity_type,
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

    def is_dataset_published(self, ckan_id, entity_type):
        doi_realisation = self.meta.tables['doi_realisation']
        log.debug('is_dataset_published = {0} {1}'.format(id, entity_type))
        clause = sqlalchemy.select([doi_realisation.c.prefix_id,
                                    doi_realisation.c.suffix_id]
                                   ).where(doi_realisation.c.site_id == self.site_id
                                   ).where(doi_realisation.c.ckan_entity == entity_type
                                   ).where(doi_realisation.c.ckan_id == ckan_id)
        results = self.con.execute(clause).fetchall()
        log.debug(results)
        if not results:
           log.debug('CKAN ID not found ({entity_type}): {ckan_id}'.format(entity_type=entity_type, ckan_id=ckan_id))
           return(False, "")
        else:
           doi = "NOT FOUND"
           try:
               doi = str(results[0][0]) + "/" + str(results[0][1])
           except Exception as e:
               error = "Could not find DOI, exception: " + str(e)
           log.warn('CKAN ID already has a DOI: ' + doi)
           return (True, doi)


    def mint(self, prefix, pkg = None, *args, **kwargs):
        # metadata
        pkg_metadata = json.dumps(pkg)

        # user
        ckan_user = kwargs.get('user', 'undefined')
        suffix = kwargs.get('suffix', None)

        return self.mint_doi(ckan_id=pkg.get('id', "None"), ckan_user=ckan_user, ckan_name=pkg.get('name', "None"), prefix=prefix, suffix=suffix, metadata=pkg_metadata)

    def mint_doi(self, ckan_id, ckan_user, ckan_name, prefix = None, suffix = None, metadata = "{}", entity_type='package'):

        doi_realisation = self.meta.tables['doi_realisation']

        log.debug("mint_doi doi = {0}/{1}, ckan_id = {2}, entity_type = {3}, site_id = '{4}'".format(prefix, suffix, ckan_id, ckan_user,  entity_type, self.site_id))

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
        has_doi,existing_doi = self.is_dataset_published(ckan_id, entity_type)
        if has_doi:
            error = "ERROR minting DOI: Dataset already published, DOI: " + existing_doi
            return (None, error)

        # insert row
        try:
            if suffix:
                mint_insert = doi_realisation.insert().values(prefix_id=prefix_id, suffix_id=suffix, ckan_id=ckan_id, ckan_name=ckan_name, ckan_user=ckan_user, site_id=self.site_id, metadata = metadata)
            else:
                mint_insert = doi_realisation.insert().values(prefix_id=prefix_id, ckan_id=ckan_id, ckan_name=ckan_name, ckan_user=ckan_user, site_id=self.site_id, metadata = metadata)
        
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
        
        log.debug(str(results))
        
        for result in results:
            doi = result[0] + '/' + result[1]
            log.debug("NEW DOI = " + doi)
            return (doi, None)
        
        error = "Could not retrieve inserted DOI"
        log.error(error)
        return(None, error)

    def __repr__(self):
        return str(self)

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __unicode__(self):
        return (u'DataciteIndexDOI({0}): \'{1}\' '.format(self.site_id, self.con))
