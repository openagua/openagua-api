import json
from openagua.models import Dashboard, StudyDashboards, Card, DashboardCards
from openagua.lib.studies import get_study
from openagua import db
import bleach


def add_dashboard(study_id=None, network_id=None, dashboard=None):
    new_dashboard = Dashboard()
    layout = dashboard.get('layout')
    if type(layout) != str:
        layout = json.dumps(layout)

    new_dashboard.title = dashboard.get('title', '')
    new_dashboard.description = dashboard.get('description')
    new_dashboard.layout = layout
    db.session.add(new_dashboard)
    db.session.commit()

    add_dashboard_to_study(study_id=study_id, network_id=network_id, dashboard_id=new_dashboard.id)

    return new_dashboard


def add_dashboard_to_study(study_id, network_id, dashboard_id):
    study_dashboard = StudyDashboards()
    study_dashboard.study_id = study_id
    study_dashboard.network_id = network_id
    study_dashboard.dashboard_id = dashboard_id
    db.session.add(study_dashboard)
    db.session.commit()

    return study_dashboard


def get_dashboards(**kwargs):
    if 'project_id' in kwargs and 'datauser_id' in kwargs:
        study = get_study(project_id=kwargs['project_id'], datauser_id=kwargs['datauser_id'])
        dashboards = study.dashboards
    elif 'study_id' in kwargs:
        study = get_study(id=kwargs['study_id'])
        dashboards = study.dashboards
    elif 'network_id' in kwargs:
        # TODO: fix this - sqlalchemy should handle this better
        dashboards = db.session.query(Dashboard).join(StudyDashboards).filter(StudyDashboards.network_id==kwargs['network_id']).all()

    dashboards = [dashboard.to_json() for dashboard in dashboards]
    return dashboards


def get_dashboard(dashboard_id):
    return Dashboard.query.filter_by(id=dashboard_id).first()


def delete_dashboard(dashboard_id):
    dashboard = Dashboard.query.filter_by(id=dashboard_id).first()
    db.session.delete(dashboard)
    db.session.commit()
    return


def update_dashboard(**kwargs):
    dashboard = get_dashboard(kwargs.get('id'))
    if 'title' in kwargs:
        dashboard.title = kwargs.get('title')
    if 'description' in kwargs:
        dashboard.description = kwargs.get('description')
    if 'layout' in kwargs:
        layout = kwargs.get('layout')
        if type(layout) != str:
            layout = json.dumps(layout)
        dashboard.layout = layout
    db.session.commit()

    if 'cards' in kwargs:
        ids = []
        for card in kwargs['cards']:
            if card.get('id') <= 0:
                card = add_card(**card)
                add_card_to_dashboard(dashboard.id, card.id)
            else:
                card = update_card(**card)
            ids.append(card.id)

        # remove deleted ids
        dashboard = get_dashboard(dashboard.id)
        for card in dashboard.cards:
            if card.id not in ids:
                remove_card_from_dashboard(dashboard.id, card.id)

    dashboard = get_dashboard(dashboard.id)
    return dashboard


def remove_card_from_dashboard(dashboard_id, card_id):
    db_card = DashboardCards.query.filter_by(dashboard_id=dashboard_id, card_id=card_id).first()
    db.session.delete(db_card)
    db.session.commit()


def cleaned(text):
    return bleach.clean(text, tags=bleach.sanitizer.ALLOWED_TAGS + ['sup', 'sub'])


def add_card(**kwargs):
    card = Card()
    card.title = kwargs['title']
    card.description = cleaned(kwargs.get('description', ''))
    card.type = kwargs['type']
    card.layout = json.dumps(kwargs['layout'])
    card.content = json.dumps(kwargs['content'])
    card.favorite_id = kwargs.get('favorite_id')

    db.session.add(card)
    db.session.commit()

    return card


def update_card(**kwargs):
    card = Card.query.filter_by(id=kwargs['id']).first()
    card.title = kwargs['title']
    card.description = cleaned(kwargs.get('description', ''))
    card.type = kwargs['type']
    card.layout = json.dumps(kwargs['layout'])
    card.content = json.dumps(kwargs['content'])
    card.favorite_id = kwargs.get('favorite_id')

    # db.session.update(card)
    db.session.commit()

    return card


def add_card_to_dashboard(dashboard_id, card_id):
    dc = DashboardCards()
    dc.dashboard_id = dashboard_id
    dc.card_id = card_id
    db.session.add(dc)
    db.session.commit()

    return dc
