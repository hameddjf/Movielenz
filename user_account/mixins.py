class UserQuerySetMixin:
    """Mixin for optimizing user querysets."""
    
    def get_queryset(self):
        qs = super().get_queryset()
        return qs.select_related(
            'content_type'
        ).prefetch_related(
            'user__preferred_genres'
        )