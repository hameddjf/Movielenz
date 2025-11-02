def activate_user(strategy, details, user=None, *args, **kwargs):
    """
    Pipeline function to automatically activate users created via social auth
    """
    if user and not user.activated:
        user.activated = True
        user.save(update_fields=['activated'])
    return {'user': user}