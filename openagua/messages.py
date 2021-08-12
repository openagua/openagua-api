from flask import current_app as app
from .security import current_user
from .models import User, Message, UserMessages
from . import db


def get_messages(user_id):
    user_messages = UserMessages.query.filter_by(user_id=user_id).all()
    msg_ids = [user_message.message_id for user_message in user_messages]

    # msgs = Message.query.filter(Message.id.in_(msg_ids), Message.is_new==True).all()
    msgs = Message.query.filter(Message.id.in_(msg_ids)).all() if msg_ids else []
    msgs_updated = []
    messages = []
    for msg in msgs:
        messages.append(msg.message)
        msg.is_new = False
        msgs_updated.append(msg)

    db.session.bulk_save_objects(msgs_updated)
    db.session.commit()

    return messages

def add_message(message):
    msg = Message.query.filter_by(message=message).first()
    if msg is None:  # this should be done via manage.py, not here
        msg = Message(message=message, is_new=True)
        db.session.add(msg)
        db.session.commit()
    return msg


def add_user_message(user_id, message):
    msg = add_message(message)
    user_message = UserMessages(user_id=user_id, message_id=msg.id)
    db.session.add(user_message)
    db.session.commit()


def add_message_by_usernames(usernames, message):
    msg = add_message(message)
    users = User.query.filter(User.email.in_(usernames)).all() if usernames else []
    user_messages = []
    for user in users:
        user_message = UserMessages(user_id=user.id, message_id=msg.id)
        user_messages.append(user_message)
    db.session.bulk_save_objects(user_messages)
    db.session.commit()
