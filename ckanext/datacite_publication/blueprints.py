from ckan import model
import ckanext.datacite_publication.logic as logic
from flask import Blueprint


def get_blueprints(name, module):
    # Create Blueprint for plugin
    blueprint = Blueprint(name, module)

    blueprint.add_url_rule(
        u"/dataset/<id>/approve_publication/datacite",
        u"approve_publication_package",
        approve_publication_package
    )
    return blueprint


def _get_context():
    return {"model": model, "session": model.Session,
            # "user": user_name,
            "ignore_auth": False}


def approve_publication_package(id):
    context = _get_context()
    data_dict = {"id": id}
    return logic.datacite_approve_publication_package(context, data_dict)
