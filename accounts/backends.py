"""Authentication backend that lets users log in with their email address."""

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class EmailBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        UserModel = get_user_model()
        if username is None:
            username = kwargs.get(UserModel.USERNAME_FIELD)
        if username is None:
            return None
        try:
            user = UserModel.objects.get(email__iexact=username.strip())
        except UserModel.DoesNotExist:
            UserModel().set_password(password)  # mitigate timing attack
            return None
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
