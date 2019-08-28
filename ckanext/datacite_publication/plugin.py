import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit

import ckanext.datacite_publication.logic
import ckanext.datacite_publication.helpers as helpers

class Datacite_PublicationPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IActions)
    plugins.implements(plugins.ITemplateHelpers)
    plugins.implements(plugins.IRoutes, inherit=True)

    # IConfigurer

    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_public_directory(config_, 'public')
        toolkit.add_resource('fanstatic', 'datacite_publication')

    # IRoutes
    def before_map(self, map_):
        map_.connect(
            'make_public_package',
            '/dataset/{package_id}/make_public/datacite',
            controller='ckanext.datacite_publication.controller:DatacitePublicationController',
            action = 'make_public_package'
        )
        map_.connect(
            'publish_package',
            '/dataset/{package_id}/publish/datacite',
            controller='ckanext.datacite_publication.controller:DatacitePublicationController',
            action = 'publish_package'
        )
        map_.connect(
            'approve_publication_package',
            '/dataset/{package_id}/approve_publication/datacite',
            controller='ckanext.datacite_publication.controller:DatacitePublicationController',
            action = 'approve_publication_package'
        )
        map_.connect(
            'manual_finish_publication_package',
            '/dataset/{package_id}/manual_finish_publication/datacite',
            controller='ckanext.datacite_publication.controller:DatacitePublicationController',
            action = 'manual_finish_publication_package'
        )
        map_.connect(
            'finish_publication_package',
            '/dataset/{package_id}/finish_publication_package/datacite',
            controller='ckanext.datacite_publication.controller:DatacitePublicationController',
            action = 'finish_publication_package'
        )
        map_.connect(
            'update_publication_package',
            '/dataset/{package_id}/update_publication_package/datacite',
            controller='ckanext.datacite_publication.controller:DatacitePublicationController',
            action = 'update_publication_package'
        )
        map_.connect(
            'publish_resource',
            '/dataset/{package_id}/resource/{resource_id}/publish/datacite',
            controller='ckanext.datacite_publication.controller:DatacitePublicationController',
            action = 'publish_resource'
        )
        return map_

    # IActions
    def get_actions(self):
        return {
            'datacite_make_public_package':
                ckanext.datacite_publication.logic.datacite_make_public_package,
            'datacite_publish_package':
                ckanext.datacite_publication.logic.datacite_publish_package,
            'datacite_approve_publication_package':
                ckanext.datacite_publication.logic.datacite_approve_publication_package,
            'datacite_manual_finish_publication_package':
                ckanext.datacite_publication.logic.datacite_manual_finish_publication_package,
            'datacite_finish_publication_package':
                ckanext.datacite_publication.logic.datacite_finish_publication_package,
            'datacite_update_publication_package':
                ckanext.datacite_publication.logic.datacite_update_publication_package,
            'datacite_publish_resource':
                ckanext.datacite_publication.logic.datacite_publish_resource
             }

    # ITemplateHelpers
    def get_helpers(self):
        return { 'datacite_publication_is_admin': helpers.datacite_publication_is_admin,
                 'datacite_publication_doi_is_editable': helpers.datacite_publication_doi_is_editable }
