from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from flask_admin.base import MenuLink

from flask import abort, redirect, url_for, request

from ..security import current_user

from openagua import app, models, db

# set up the base admin
admin = Admin(app, name=app.config['APP_NAME'], template_mode='bootstrap3')


class UserView(ModelView):
    column_exclude_list = ['password', ]
    column_searchable_list = ['email']

    def is_accessible(self):
        if not current_user.is_active or not current_user.is_authenticated:
            return False

        if current_user.has_role('admin') or current_user.has_role('superuser'):
            return True

    def inaccessible_callback(self, name, **kwargs):
        if current_user.is_authenticated:
            abort(403)  # permission denied
        else:
            return redirect(url_for('login', next=request.url))  # divert to login


class RoleView(ModelView):
    def is_accessible(self):
        if not current_user.is_active or not current_user.is_authenticated:
            return False

        if current_user.has_role('admin') or current_user.has_role('superuser'):
            return True

    def inaccessible_callback(self, name, **kwargs):
        if current_user.is_authenticated:
            abort(403)  # permission denied
        else:
            return redirect(url_for('login', next=request.url))  # divert to login


# Add administrative views here
admin.add_view(UserView(models.User, db.session))
admin.add_view(RoleView(models.Role, db.session))

# Add menu links
admin.add_link(MenuLink(name='Sign out', url='/logout'))
