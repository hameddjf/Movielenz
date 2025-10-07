import django_filters
from .models import Article

class ArticleFilter(django_filters.FilterSet):
    """
    فیلترهای سفارشی برای مقالات در نمای عمومی.
    """
    tags = django_filters.CharFilter(field_name='tags__slug', lookup_expr='in')
    
    author = django_filters.CharFilter(field_name='author__username')

    class Meta:
        model = Article
        fields = ['tags', 'author']