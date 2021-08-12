from openagua.models import User

from openagua.security.utils import hash_password

def test_new_user():
    """
    GIVEN a User model
    WHEN a new User is created
    THEN check the email, hashed_password, authenticated, and role fields are defined correctly
    """
    user = User()
    user.email = 'nobody@gmail.com'
    user.password = hash_password('plaintextpassword')
    assert user.email == 'nobody@gmail.com'
    assert user.password != 'plaintextpassword'
    assert not user.authenticated
    assert user.role == 'user'