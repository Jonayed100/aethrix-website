from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class EmailBackend(ModelBackend):
    """Sign in with email (any letter case) and password.

    Usernames still work too, so the Django admin login keeps working.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        login = (kwargs.get("email") or username or "").strip()
        if not login or password is None:
            return None
        User = get_user_model()
        candidates = list(User.objects.filter(email__iexact=login)) or list(User.objects.filter(username__iexact=login))
        if not candidates:
            # Spend the same time as a real check so attackers can't time which emails exist.
            User().set_password(password)
            return None
        for user in candidates:
            if user.check_password(password) and self.user_can_authenticate(user):
                return user
        return None
