# from rest_framework import serializers
# from django.contrib.auth import get_user_model
# from django.utils.text import slugify

# from .models import Article, Tag

# User = get_user_model()

# class TagSerializer(serializers.ModelSerializer):
#     """
#     سریالایزر برای مدل Tag با تولید خودکار اسلاگ.
#     """
#     class Meta:
#         model = Tag
#         fields = ['id', 'name', 'slug']
#         read_only_fields = ['slug'] 

#     def create(self, validated_data):
#         """
#         *** تغییر کلیدی: بازنویسی متد create برای تولید خودکار اسلاگ ***
        
#         این متد تضمین می‌کند که اسلاگ قبل از ایجاد آبجکت در دیتابیس،
#         از روی نام ساخته شود.
#         """
#         name = validated_data.get('name')
#         slug = slugify(name, allow_unicode=True)

#         validated_data['slug'] = slug
#         return super().create(validated_data)

# class ArticleSerializer(serializers.ModelSerializer):
#     """
#     سریالایزر ریفکتور شده برای مدل Article.
#     """
#     author = serializers.StringRelatedField(read_only=True)
    
#     tags = TagSerializer(many=True, read_only=True)
    
#     tags_id = serializers.PrimaryKeyRelatedField(
#         queryset=Tag.objects.all(),
#         source='tags',
#         many=True,
#         write_only=True,
#         label="لیست ID تگ‌ها"
#     )

#     class Meta:
#         model = Article
#         fields = [
#             'id', 'author', 'title', 'slug', 'content', 'featured_image', 
#             'status', 'created_at', 'updated_at', 'published_at', 
#             'tags', 'tags_id'
#         ]
#         read_only_fields = ['slug', 'author', 'created_at', 'updated_at', 'published_at']

#     def create(self, validated_data):
#         """
#         متد create برای تعیین خودکار نویسنده.
#         این متد به درستی پیاده‌سازی شده بود و بدون تغییر باقی می‌ماند.
#         """
#         validated_data['author'] = self.context['request'].user
#         return super().create(validated_data)

#     def update(self, instance, validated_data):
#         """
#         *** تغییر کلیدی: بازنویسی متد update برای مدیریت صحیح تگ‌ها ***
        
#         این متد برای حل مشکل به‌روزرسانی نشدن تگ‌ها در متدهای PUT/PATCH بازنویسی شده است.
#         """
#         tags_data = validated_data.pop('tags', None)

#         instance = super().update(instance, validated_data)

#         if tags_data is not None:
#             instance.tags.set(tags_data)
        
#         return instance

from rest_framework import serializers
from .models import Article, Tag

class TagSerializer(serializers.ModelSerializer):
    """سریالایزر فقط-خواندنی برای تگ‌ها."""
    class Meta:
        model = Tag
        fields = ['name', 'slug']

class ArticleListSerializer(serializers.ModelSerializer):
    """سریالایزر برای نمایش لیست مقالات (اطلاعات خلاصه)."""
    author = serializers.StringRelatedField()
    tags = TagSerializer(many=True, read_only=True)
    
    class Meta:
        model = Article
        fields = ['author', 'title', 'slug', 'featured_image', 'published_at', 'tags']

class ArticleDetailSerializer(serializers.ModelSerializer):
    """سریالایزر برای نمایش جزئیات کامل یک مقاله."""
    author = serializers.StringRelatedField()
    tags = TagSerializer(many=True, read_only=True)

    class Meta:
        model = Article
        fields = [
            'id', 'author', 'title', 'slug', 'content', 'featured_image', 
            'published_at', 'tags'
        ]