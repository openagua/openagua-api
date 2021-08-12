# manage.py
import os
from getpass import getpass
from datetime import datetime
from flask_script import Manager
from flask_migrate import Migrate, MigrateCommand

from openagua.security.utils import hash_password
from openagua.security.registerable import register_user
from openagua import app, db
from openagua.models import User, Role

from zlib import error

import hydra_base as hb
from hydra_base.util import hdb

migrate = Migrate(app, db, directory='data/migrations')
manager = Manager(app)

manager.add_command('db', MigrateCommand)


@manager.command
def init_hydra():
    # create the database
    print("Creating database...")
    db_url = hb.config.get('mysqld', 'url')
    db_url = hb.db.create_mysql_db(db_url)
    hb.db.connect(db_url)

    # add defaults
    print("Adding defaults...")
    hdb.create_default_users_and_perms()
    hdb.create_default_units_and_dimensions()

    # add root user
    print("Creating root user...")
    hdb.make_root_user()
    print("Done!")


@manager.command
def fix_hydra():
    """
    This is legacy code that was used to migrate from blob to text. It is left here for future reference.
    """
    import transaction
    import zlib
    from hydra_base.db.model import Dataset
    from tqdm import tqdm

    # create the database
    print("Connecting to database...")
    db_url = hb.config.get('mysqld', 'url')
    hb.db.connect(db_url)

    print('querying')
    query = hb.db.DBSession.query(Dataset)
    start = 0
    end = 600000
    step = 50
    verbose = False
    print('starting')
    for idx in tqdm(range(start, end, step), ncols=100, disable=verbose):
        indices = list(range(idx, idx + step))
        if verbose:
            print('Converting ids {}'.format([indices[0], indices[-1]]))
        if idx < start:
            continue
        if verbose:
            print('querying...')
        rows = query.filter(Dataset.id.in_(indices)).filter(Dataset.value == None).all()
        if not rows:
            continue
        for row in rows:
            try:
                blob = row.value_blob
                if type(blob) == bytes:
                    try:
                        val = blob.decode()
                    except UnicodeDecodeError:
                        try:
                            val = zlib.decompress(blob).decode()
                        except zlib.error:
                            zobj = zlib.decompressobj()
                            val = zobj.decompress(blob).decode()
                else:
                    val = blob
            except Exception as err:
                print('Warning: could not convert dataset {} (index {})'.format(row.id, idx))
                continue
            row.value = val
            row.value_blob = None
        if verbose:
            print('committing...')
        hb.db.DBSession.flush()
        transaction.commit()

    print('done!')
    return


@manager.command
def register_superuser(email, password):
    print("Creating account...")

    role = Role.query.filter(Role.name == 'superuser').first()
    if not role:
        role = Role()
        role.name = 'superuser'
        db.session.add(role)

    # Create user
    user = User()
    user.email = email
    user.password = hash_password(password)
    user.active = True
    user.confirmed_at = datetime.utcnow()

    # Bind admin to role
    user.roles.append(role)

    # Store user and roles
    db.session.add(user)
    db.session.commit()

    # register on data platform & add datauser record
    from openagua.lib.users import register_datauser
    register_datauser(
        username=email,
        password=password,
        user_id=user.id
    )

    print(' [*] Success! Admin user {} registered.'.format(email))


@manager.command
def addsuperuser():
    '''
    Add a user with admin privledges.
    '''

    email = input("Email: ")
    user = User.query.filter(User.email == email).first()
    if user:
        print('Email already exists. Exiting.')
        return

    password1 = True
    password2 = False
    tries = 0
    maxtries = 3
    while not password1 == password2 and tries < maxtries:
        password1 = None
        while not password1:
            password1 = getpass("Password: ")
            if not password1:
                print("Password cannot be blank. Please try again.")
                tries += 1
            if tries == maxtries:
                break
        else:
            password2 = getpass("Verify password: ")
            if password2 != password1:
                print("Passwords don't match. Please enter passwords again.")
                tries += 1

    if tries == maxtries:
        print('Max tries exceeded. Please start over.')
        return

    password = password1

    register_superuser(email, password)


if __name__ == "__main__":
    manager.run()
