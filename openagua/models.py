from flask import current_app as app
from openagua.security import UserMixin, RoleMixin
from sqlalchemy.dialects.mysql import LONGTEXT

import jwt
import datetime

from munch import Munch as AttrDict
import json

from sqlalchemy_json import mutable_json_type

from openagua import db
from openagua.security.utils import hash_password, verify_password
from openagua.lib.security import generate_random_alphanumeric_key, hash_key


class User(db.Model, UserMixin):
    id = db.Column(db.Integer(), primary_key=True)
    email = db.Column(db.String(255), unique=True)
    username = db.Column(db.String(31), unique=True)
    password = db.Column(db.String(255))
    active = db.Column(db.Boolean())
    confirmed_at = db.Column(db.DateTime())
    new_user = db.Column(db.Boolean(), server_default='1')

    # other info
    firstname = db.Column(db.String(50))
    lastname = db.Column(db.String(50))
    organization = db.Column(db.String(50))
    socketid = db.Column(db.String(50))

    settings = db.Column(db.Text())

    # relationships
    roles = db.relationship('Role', secondary='user_roles', backref=db.backref('users', lazy='dynamic'))
    messages = db.relationship('Message', secondary='user_messages', backref=db.backref('users', lazy='dynamic'))

    def __init__(self, **kwargs):
        self.email = kwargs['email']
        self.username = kwargs.get('username')
        self.active = kwargs.get('active')
        password = kwargs['password']
        self.password = hash_password(password)

    def get(self, setting):
        settings = json.loads(self.settings if self.settings else '{}')
        return settings.get(setting)

    def get_settings(self):
        return json.loads(self.settings if self.settings else '{}')

    def to_json(self, include_id=False):
        user = {
            'username': self.username,
            'email': self.email,
        }
        if include_id:
            user['id'] = self.id

        return user

    def hash_password(self, password):
        self.password = hash_password(password)

    def verify_password(self, password):
        return verify_password(password, self.password)

    def encode_auth_token(self):
        """
        Generates the Auth Token
        :return: string
        """
        try:
            payload = {
                'exp': datetime.datetime.utcnow() + datetime.timedelta(days=0, seconds=15),
                'iat': datetime.datetime.utcnow(),
                'sub': self.id
            }
            return jwt.encode(
                payload,
                app.config.get('SECRET_KEY'),
                algorithm='HS256'
            )
        except Exception as e:
            return e

    @staticmethod
    def decode_auth_token(auth_token):
        """
        Decodes the auth token
        :param auth_token:
        :return: integer|string
        """
        try:
            payload = jwt.decode(auth_token, app.config.get('SECRET_KEY'))
            return payload['sub']
        except jwt.ExpiredSignatureError:
            return 'Signature expired. Please log in again.'
        except jwt.InvalidTokenError:
            return 'Invalid token. Please log in again.'

    def generate_api_key(self):
        """
        This follows the basic API key approach described in:
        https://www.freecodecamp.org/news/best-practices-for-building-api-keys-97c26eabfea9/
        :return: The newly generated, unhashed key.
        """
        # generate key

        while True:
            key_prefix = generate_random_alphanumeric_key(k=6)
            key_base = generate_random_alphanumeric_key(k=33)
            user_key = '.'.join([key_prefix, key_base])
            hashed_key_base = hash_key(key_base)
            db_key = '.'.join([key_prefix, hashed_key_base])

            try:
                APIKey.query.filter_by(id=db_key).one()
            except Exception as err:
                break

        # update key in database
        apikey = APIKey.query.filter_by(user_id=self.id).first()
        if apikey:
            apikey.id = db_key

        else:
            apikey = APIKey()
            apikey.id = db_key
            apikey.user_id = self.id
            db.session.add(apikey)
        db.session.commit()

        return user_key

    @staticmethod
    def verify_api_key(key):
        try:
            key_prefix, key_base = key.split('.')
            hashed_key_base = hash_key(key_base)
            db_key = '.'.join([key_prefix, hashed_key_base])
            apikey = APIKey.query.get(db_key)
            if not apikey:
                return None
            user = User.query.get(apikey.user_id)
        except ValueError:
            user = None  # no dot (.) in key
        except Exception as err:
            return None
        return user


class Role(db.Model, RoleMixin):
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(80), unique=True)
    description = db.Column(db.String(255))


class UserRoles(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    user_id = db.Column(db.Integer(), db.ForeignKey('user.id', ondelete='CASCADE'))
    role_id = db.Column(db.Integer(), db.ForeignKey('role.id', ondelete='CASCADE'))


class APIKey(db.Model):
    __tablename__ = 'apikey'
    id = db.Column(db.String(255), primary_key=True, unique=True)
    user_id = db.Column(db.Integer(), db.ForeignKey('user.id', ondelete='CASCADE'))


class DataUser(db.Model):
    __tablename__ = 'datauser'
    id = db.Column(db.Integer(), primary_key=True)
    user_id = db.Column(db.Integer(), db.ForeignKey('user.id', ondelete='CASCADE'))
    dataurl_id = db.Column(db.Integer(), db.ForeignKey('dataurl.id', ondelete='CASCADE'))
    userid = db.Column(db.Integer())
    username = db.Column(db.String(50))
    password = db.Column(db.String(255))  # Note: this is for 3rd party databases, not the main connected database.
    sessionid = db.Column(db.String(255))
    settings = db.Column(db.Text())

    def get_setting(self, setting):
        s = json.loads(self.settings or "{}")
        return s.get(setting)


class DataUrl(db.Model):
    __tablename__ = 'dataurl'
    id = db.Column(db.Integer(), primary_key=True)
    url = db.Column(db.String(255), unique=True)

    def to_json(self):
        return dict(
            id=self.id,
            url=self.url
        )


class Study(db.Model):
    __tablename__ = 'study'
    id = db.Column(db.Integer(), primary_key=True)
    created_by = db.Column(db.Integer(), db.ForeignKey('user.id', ondelete='CASCADE'))
    dataurl_id = db.Column(db.Integer(), db.ForeignKey('dataurl.id', ondelete='CASCADE'))
    project_id = db.Column(db.Integer())
    settings = db.Column(db.Text())
    secrets = db.Column(db.Text())  # this should be encrypted
    layout = db.Column(db.Text())

    # relationships
    favorites = db.relationship('Favorite')
    inputsetups = db.relationship('InputSetup')
    dashboards = db.relationship('Dashboard', secondary='study_dashboards', lazy='dynamic')

    def get(self, setting):
        settings = json.loads(self.settings if self.settings else '{}')
        return settings.get(setting)


# User-saved objects

class Favorite(db.Model):
    __tablename__ = 'favorite'
    id = db.Column(db.Integer(), primary_key=True)
    study_id = db.Column(db.Integer(), db.ForeignKey('study.id', ondelete='CASCADE'))
    network_id = db.Column(db.Integer())
    name = db.Column(db.String(80))
    description = db.Column(db.String(255), server_default='')
    provider = db.Column(db.String(16))
    type = db.Column(db.String(16))
    filters = db.Column(db.JSON())
    pivot = db.Column(db.JSON())
    analytics = db.Column(db.JSON())
    content = db.Column(db.JSON())

    def to_json(self):
        j = {}
        for c in self.__table__.columns:
            j[c.name] = getattr(self, c.name)
            if c.name in ['content', 'filters', 'pivot', 'analytics']:
                j[c.name] = j.get(c.name) or {}

        return j


class Message(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    message = db.Column(db.String(512))
    is_new = db.Column(db.Boolean())


class UserMessages(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    user_id = db.Column(db.Integer(), db.ForeignKey('user.id', ondelete='CASCADE'))
    message_id = db.Column(db.Integer(), db.ForeignKey('message.id', ondelete='CASCADE'))


class Run(db.Model):
    sid = db.Column(db.String(255), primary_key=True)
    model_id = db.Column(db.Integer())
    layout = db.Column(db.Text())

    def get_layout(self):
        return json.loads(self.layout)


class Ping(db.Model):
    sid = db.Column(db.String(255), db.ForeignKey('user.id', ondelete='CASCADE'), primary_key=True)
    status = db.Column(db.String(10), primary_key=True)
    source_id = db.Column(db.Integer(), db.ForeignKey('dataurl.id'))
    name = db.Column(db.String(100))
    network_id = db.Column(db.Integer())
    # start_time = db.Column(db.DateTime())
    # end_time = db.Column(db.DateTime())
    last_ping = db.Column(db.Integer())
    extra_info = db.Column(db.Text())

    def to_json(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class Model(db.Model):
    """Models available for simulation and/or optimization."""
    id = db.Column(db.Integer(), primary_key=True)
    service = db.Column(db.String(32))
    name = db.Column(db.String(80))
    description = db.Column(db.String(255))
    user_id = db.Column(db.Integer(), db.ForeignKey('user.id', ondelete='CASCADE'))
    study_id = db.Column(db.Integer(), db.ForeignKey('study.id', ondelete='CASCADE'))
    scope = db.Column(db.String(32))  # private (only available to user/project) or public (available to anybody)
    image_id = db.Column(db.String(32))
    executable = db.Column(db.String(128))
    key = db.Column(db.String(32))
    init_script = db.Column(db.Text())  # bash script to run on newly-launched machine

    templates = db.relationship('ModelTemplate')

    networks = db.relationship('NetworkModel')

    def to_json(self, include_templates=False, include_network_ids=False):
        ret = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        if include_templates:
            ret['templates'] = [t.to_json() for t in self.templates]
        ret['network_ids'] = []
        if include_network_ids:
            for network in self.networks:
                ret['network_ids'].append(network.network_id)
        return AttrDict(ret)


class NetworkModel(db.Model):
    """Models available for a study/network"""
    model_id = db.Column(db.Integer(), db.ForeignKey('model.id', ondelete='CASCADE'), primary_key=True)
    dataurl_id = db.Column(db.Integer(), db.ForeignKey('dataurl.id', ondelete='CASCADE'), primary_key=True)
    network_id = db.Column(db.Integer(), primary_key=True)
    active = db.Column(db.Boolean())
    settings = db.Column(db.Text())  # settings for the model

    db.UniqueConstraint('model_id', 'dataurl_id', 'network_id')

    # model = db.relationship('Model')

    def get(self, setting):
        settings = json.loads(self.settings if self.settings else '{}')
        return settings.get(setting)

    def to_json(self):
        ret = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        return AttrDict(ret)


class UserNetworkSettings(db.Model):
    """Models available for a study/network"""
    user_id = db.Column(db.Integer(), db.ForeignKey('user.id', ondelete='CASCADE'))
    dataurl_id = db.Column(db.Integer(), db.ForeignKey('dataurl.id', ondelete='CASCADE'), primary_key=True)
    network_id = db.Column('network_id', db.Integer(), primary_key=True)
    settings = db.Column(mutable_json_type(dbtype=db.JSON(), nested=True))  # settings for the network

    db.UniqueConstraint('user_id', 'dataurl_id', 'network_id')

    def __init__(self, **kwargs):
        self.user_id = kwargs.get('user_id')
        self.dataurl_id = kwargs.get('dataurl_id')
        self.network_id = kwargs.get('network_id')
        self.settings = kwargs.get('settings', {})

    def get(self, setting):
        settings = self.settings or {}
        return settings.get(setting)

    def to_json(self):
        ret = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        return AttrDict(ret)


class ModelTemplate(db.Model):
    """Dependancy relationships between models and templates."""
    model_id = db.Column(db.Integer(), db.ForeignKey('model.id', ondelete='CASCADE'), primary_key=True)
    dataurl_id = db.Column(db.Integer(), db.ForeignKey('dataurl.id', ondelete='CASCADE'), primary_key=True)
    template_id = db.Column(db.Integer(), primary_key=True)
    template_name = db.Column(db.Text())  # this should be checked before the ID

    def to_json(self, include_models=False):
        ret = {c.name: getattr(self, c.name) for c in self.__table__.columns}

        return AttrDict(ret)


class InputSetup(db.Model):
    __tablename__ = 'input_setup'
    id = db.Column(db.Integer(), primary_key=True)
    study_id = db.Column(db.Integer(), db.ForeignKey('study.id', ondelete='CASCADE'))
    name = db.Column(db.String(80), nullable=False)
    description = db.Column(db.String(255), server_default='')
    filters = db.Column(db.Text(), nullable=False)
    setup = db.Column(db.Text(), nullable=False)


class Card(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    title = db.Column(db.String(31))
    description = db.Column(db.String(255))
    type = db.Column(db.String(31))
    content = db.Column(db.Text())
    layout = db.Column(db.Text())
    favorite_id = db.Column(db.Integer(), db.ForeignKey('favorite.id', ondelete='CASCADE'))

    favorite = db.relationship('Favorite', backref=db.backref('card', lazy='dynamic'))

    def to_json(self):
        return dict(
            id=self.id,
            title=self.title,
            description=self.description,
            type=self.type,
            content=json.loads(self.content),
            layout=json.loads(self.layout),
            favorite_id=self.favorite_id,
            favorite=self.favorite.to_json() if self.favorite_id and self.favorite else None
        )


class Dashboard(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    title = db.Column(db.String(80))
    description = db.Column(db.String(255))
    layout = db.Column(db.Text())

    # relationships
    cards = db.relationship('Card', single_parent=True, cascade="all, delete-orphan", secondary='dashboard_cards')

    def to_json(self):
        return dict(
            id=self.id,
            title=self.title,
            description=self.description,
            layout=json.loads(self.layout or '{}'),
            cards=[card.to_json() for card in self.cards]
        )


class DashboardCards(db.Model):
    # id = db.Column(db.Integer(), primary_key=True)
    dashboard_id = db.Column(db.Integer(), db.ForeignKey('dashboard.id', ondelete='CASCADE'), primary_key=True)
    card_id = db.Column(db.Integer(), db.ForeignKey('card.id', ondelete='CASCADE'), primary_key=True)

    db.UniqueConstraint('dashboard_id', 'card_id')


class StudyDashboards(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    study_id = db.Column(db.Integer(), db.ForeignKey('study.id', ondelete='CASCADE'))
    network_id = db.Column(db.Integer())
    dashboard_id = db.Column(db.Integer(), db.ForeignKey('dashboard.id', ondelete='CASCADE'))


class Star(db.Model):
    user_id = db.Column(db.Integer(), db.ForeignKey('user.id', ondelete='CASCADE'), primary_key=True)
    study_id = db.Column(db.Integer(), db.ForeignKey('study.id', ondelete='CASCADE'), primary_key=True)

    study = db.relationship('Study')
