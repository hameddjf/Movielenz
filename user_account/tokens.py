from django.contrib.auth.tokens import PasswordResetTokenGenerator
import hashlib

class TokenGenerator(PasswordResetTokenGenerator):
    def _make_hash_value(self, user, timestamp):
        return f"{user.pk}{timestamp}{user.is_active}"

account_activation_token = TokenGenerator()
