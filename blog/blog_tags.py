
from django import template
from .models import Article, Tag

register = template.Library()

@register.simple_tag
def get_latest_articles(count=5):
    """
    تگی برای دریافت آخرین مقالات منتشر شده.
    نحوه استفاده در قالب: {% get_latest_articles 5 as latest_articles %}
    """
    return Article.published.all()[:count]

@register.inclusion_tag('blog/tags/tag_cloud.html')
def show_tag_cloud():
    """
    تگی برای نمایش لیست تگ‌ها (ابر برچسب).
    این تگ یک قالب را رندر می‌کند.
    نحوه استفاده: {% show_tag_cloud %}
    """
    tags = Tag.objects.all()
    return {'tags': tags}