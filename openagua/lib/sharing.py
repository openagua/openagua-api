from flask import g

from openagua.lib.users import get_datauser
from openagua.utils import decrypt
from openagua.connection import HydraConnection
from openagua.security import current_user
from openagua.messages import add_message_by_usernames

from openagua.models import User


def share_resource(conn, resource_class, resource_id, emails, permissions, message=None, url=None):
    if url and conn.url != url:
        datauser = get_datauser(url=url, user_id=current_user.id)
        conn = HydraConnection(
            url=url,
            username=datauser.username,
            password=decrypt(datauser.password)
        )
    else:
        datauser = g.datauser

    valid_emails = []
    invalids = []
    for email in emails:
        user = User.query.filter_by(email=email).first()
        if user:
            valid_emails.append(email)
        else:
            invalids.append(email)

    if valid_emails:
        read_only = permissions.get('edit') == 'N'
        share = permissions.get('share', 'N')

        result = conn.call('share_{}'.format(resource_class), resource_id, valid_emails, read_only, share)
        if result and 'faultstring' in result:
            error = 2
            result = result['faultstring']
        else:
            error = 0
            item = conn.call('get_{}'.format(resource_class), resource_id)
            if message:
                default_message = '{} has shared {} {} with you.'.format(
                    datauser.username,
                    resource_id,
                    item.name
                )
                message = default_message + '\n\n' + default_message

            add_message_by_usernames(valid_emails, message)
            result = None
    else:
        error = 1
        result = 'No valid emails'

    results = {'error': error, 'result': result, 'valids': valid_emails, 'invalids': invalids}

    return results


def set_resource_permissions(conn, item_class, item_id, usernames, permissions, url=None, send_message=True):
    if url and conn.url != url:
        datauser = get_datauser(url=url, user_id=current_user.id)
        if conn.url != url:
            conn = HydraConnection(
                url=url,
                username=datauser.username,
                password=decrypt(datauser.password)
            )
    else:
        datauser = g.datauser

    read = permissions['view']
    write = permissions['edit']
    share = permissions['share']

    if type(usernames) == str:
        usernames = [usernames]

    conn.call('set_{}_permission'.format(item_class), item_id, usernames, read, write, share)

    # error = 0
    # item = conn.call('get_{}'.format(item_class), **{'{}_id'.format(item_class): item_id})
    # message = '{} has unshared {} {} with you.'.format(
    #     datauser.username,
    #     item_class,
    #     item.name
    # )
    # if send_message:
    #     add_message_by_usernames(usernames, message)
    # result = None

    return
