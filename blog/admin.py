# Register your models here.
from django.contrib import admin
from .models import Article, Tag

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)} 

@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'status', 'published_at')
    list_filter = ('status', 'created_at', 'published_at', 'author')
    search_fields = ('title', 'content')
    raw_id_fields = ('author',)
    date_hierarchy = 'published_at'
    ordering = ('status', '-published_at')
    prepopulated_fields = {'slug': ('title',)}
    
    actions = ['make_published']

    def make_published(self, request, queryset):
        """
        اکشن سفارشی برای انتشار مقالات انتخاب شده.
        """
        rows_updated = queryset.update(status='published')
        self.message_user(request, f"{rows_updated} مقاله با موفقیت منتشر شد.")
    make_published.short_description = "انتشار مقالات انتخاب شده"