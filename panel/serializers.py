# admin_panel/serializers.py

from rest_framework import serializers

from user_account.models import User
from user_account.enums import  UserRole

from rest_framework import serializers
from django.utils.translation import gettext_lazy as _

class UserAdminSerializer(serializers.ModelSerializer):
    """
    سریالایزر برای مدیریت پروفایل کاربران با منطق تفکیک شده.
    """
    password = serializers.CharField(
        write_only=True, 
        required=False,
        style={'input_type': 'password'}
    )
    full_name = serializers.CharField(source='get_full_name', read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'full_name', 'first_name', 'last_name',
            'password', 'role', 'activated', 'subscription_status',
            'subscription_end_date', 'date_joined', 'profile_picture',
        ]
        read_only_fields = ['date_joined', 'subscription_status', 'subscription_end_date']
        extra_kwargs = {
            'first_name': {'write_only': True, 'required': False},
            'last_name': {'write_only': True, 'required': False},
        }

    def get_fields(self):
      """
      فیلدها را به صورت داینامیک بر اساس نقش کاربر تنظیم می‌کند.
      """
      fields = super().get_fields()
      request = self.context.get('request')

      # ابتدا بررسی کن که آیا کاربر اصلا وجود دارد و لاگین کرده است یا نه
      if request and hasattr(request, "user") and request.user.is_authenticated:
          # فقط در صورتی که کاربر لاگین کرده باشد، نقش او را بررسی کن
          if request.user.role not in [UserRole.ADMIN, UserRole.OWNER]:
              fields['role'].read_only = True
      else:
          # اگر کاربر لاگین نکرده باشد (مثلاً در زمان ساخت schema توسط drf-spectacular)
          # بهتر است فیلد role را read_only در نظر بگیریم تا مشکلی پیش نیاید.
          fields['role'].read_only = True
      
      return fields

    def update(self, instance, validated_data):
        """
        متد به‌روزرسانی کاربر با کنترل‌های امنیتی برای تغییر نقش.
        """
        requesting_user = self.context['request'].user
        role_to_set = validated_data.get('role')

        # اگر ادمین در حال تغییر نقش است، نباید بتواند نقش OWNER را تنظیم کند.
        if requesting_user.role == UserRole.ADMIN and role_to_set == UserRole.OWNER:
            raise serializers.ValidationError({
                'role': _("شما به عنوان Admin مجاز به تعیین نقش Owner نیستید.")
            })

        # به‌روزرسانی پسورد در صورت ارائه
        password = validated_data.pop('password', None)
        if password:
            instance.set_password(password)

        # به‌روزرسانی سایر فیلدها
        instance = super().update(instance, validated_data)
        instance.save()
        return instance

    # متد create بدون تغییر باقی می‌ماند، چون منطق قبلی برای ایجاد کاربر توسط ادمین صحیح است.
    
    def create(self, validated_data):
        """
        متد ایجاد کاربر جدید. پسورد در اینجا هش می‌شود.
        """
        
        default_role = UserRole.PREMIUM_USER
        allowed_roles_for_admin = [UserRole.PREMIUM_USER, UserRole.NORMAL_USER]
        role = validated_data.get('role')
        if role in [UserRole.OWNER, UserRole.ADMIN]:
            raise serializers.ValidationError({
                'role': _("شما مجاز به انتخاب نقش Owner یا Admin در زمان ایجاد کاربر جدید نیستید.")
            })
        elif not role:
            validated_data['role'] = default_role
        elif role not in allowed_roles_for_admin:
             raise serializers.ValidationError({
                'role': _("نقش انتخاب شده مجاز نیست.")
             })

        user = User.objects.create_user(**validated_data)
        return user
      
      
# class UserAdminSerializer(serializers.ModelSerializer):
#     """
#     سریالایزر برای مدیریت کامل کاربران در پنل ادمین.
#     """
#     # فیلد پسورد فقط برای نوشتن (ایجاد یا تغییر) است و هرگز خوانده نمی‌شود.
#     password = serializers.CharField(
#         write_only=True, 
#         required=False,  # برای ویرایش کاربر، تغییر پسورد الزامی نیست
#         style={'input_type': 'password'}
#     )
    
#     # نمایش نام کامل کاربر برای راحتی در پنل
#     full_name = serializers.CharField(source='get_full_name', read_only=True)

#     class Meta:
#         model = User
#         fields = [
#             'id',
#             'username',
#             'email',
#             'full_name', # فیلد خواندنی
#             'first_name',
#             'last_name',
#             'password', # فیلد نوشتنی
#             'role',
#             'activated',
#             'subscription_status',
#             'subscription_end_date',
#             'date_joined',
#             'profile_picture',
#         ]
#         # این فیلدها فقط در درخواست‌های POST/PATCH/PUT نوشته می‌شوند
#         extra_kwargs = {
#             'first_name': {'write_only': True, 'required': False},
#             'last_name': {'write_only': True, 'required': False},
#         }
#         read_only_fields = ['date_joined']

#     def create(self, validated_data):
#         """
#         متد ایجاد کاربر جدید. پسورد در اینجا هش می‌شود.
#         """
        
#         default_role = UserRole.PREMIUM_USER
#         allowed_roles_for_admin = [UserRole.PREMIUM_USER, UserRole.NORMAL_USER]
#         role = validated_data.get('role')
#         if role in [UserRole.OWNER, UserRole.ADMIN]:
#             raise serializers.ValidationError({
#                 'role': _("شما مجاز به انتخاب نقش Owner یا Admin در زمان ایجاد کاربر جدید نیستید.")
#             })
#         elif not role:
#             validated_data['role'] = default_role
#         elif role not in allowed_roles_for_admin:
#              raise serializers.ValidationError({
#                 'role': _("نقش انتخاب شده مجاز نیست.")
#              })

#         user = User.objects.create_user(**validated_data)
#         return user

#     def update(self, instance, validated_data):
#         """
#         متد به‌روزرسانی کاربر. اگر پسورد جدیدی ارسال شده باشد، آن را هش می‌کند.
#         """
#         password = validated_data.pop('password', None)

#         current_user_role = getattr(instance, 'role', None) 
#         requesting_user = self.context.get('request').user if 'request' in self.context else None
#         requesting_user_role = getattr(requesting_user, 'role', None) if requesting_user else None
#         role_to_set = validated_data.get('role')

#         if role_to_set:
#           if requesting_user_role == UserRole.ADMIN and role_to_set == UserRole.OWNER:
#                 raise serializers.ValidationError({
#                     'role': _("شما به عنوان Admin مجاز به تعیین نقش Owner نیستید.")
#                 })
#         instance = super().update(instance, validated_data)

#         if password:
#             instance.set_password(password)
#             instance.save()

#         return instance
      
# blog
from rest_framework import serializers
from django.utils.text import slugify
from blog.models import Article, Tag

# TagSerializer شما عالی است و بدون تغییر باقی می‌ماند
class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id', 'name', 'slug']
        read_only_fields = ['slug']

    def create(self, validated_data):
        name = validated_data.get('name')
        slug = slugify(name, allow_unicode=True)
        # چک کردن عدم وجود اسلاگ تکراری
        if Tag.objects.filter(slug=slug).exists():
            raise serializers.ValidationError("تگی با این اسلاگ وجود دارد.")
        validated_data['slug'] = slug
        return super().create(validated_data)
      
class ArticleSerializer(serializers.ModelSerializer):
    """
    سریالایزر جامع برای مدیریت مقالات در پنل (CRUD).
    """
    author = serializers.StringRelatedField(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    tags_id = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        source='tags',
        many=True,
        write_only=True,
        label="لیست ID تگ‌ها"
    )

    class Meta:
        model = Article
        fields = [
            'id', 'author', 'title', 'slug', 'content', 'featured_image', 
            'status', 'created_at', 'updated_at', 'published_at', 
            'tags', 'tags_id'
        ]
        # slug در اینجا read_only است چون به صورت خودکار ساخته می‌شود
        read_only_fields = ['slug', 'author', 'published_at']

    def create(self, validated_data):
        """
        هنگام ایجاد، نویسنده و اسلاگ را به صورت خودکار تنظیم می‌کند.
        """
        validated_data['author'] = self.context['request'].user
        
        # تولید خودکار اسلاگ از عنوان
        title = validated_data.get('title')
        slug = slugify(title, allow_unicode=True)
        if Article.objects.filter(slug=slug).exists():
             raise serializers.ValidationError("مقاله‌ای با این عنوان (و اسلاگ) قبلاً ثبت شده است.")
        validated_data['slug'] = slug

        return super().create(validated_data)

    def update(self, instance, validated_data):
        """
        متد update که شما نوشتید کاملاً صحیح است و تگ‌ها را به درستی مدیریت می‌کند.
        """
        tags_data = validated_data.pop('tags', None)
        instance = super().update(instance, validated_data)
        if tags_data is not None:
            instance.tags.set(tags_data)
        return instance
    
# movie
from movielenz.models import Movie, Series
from episode.models import Episode , EpisodeQuality
class EpisodeQualitySerializer(serializers.ModelSerializer):
    """
    سریالایزر برای مدیریت کیفیت‌های مختلف یک قسمت.
    """
    class Meta:
        model = EpisodeQuality
        fields = ['id', 'quality', 'file']

class EpisodeSerializer(serializers.ModelSerializer):
    """
    سریالایزر برای مدیریت قسمت‌ها.
    این سریالایزر کیفیت‌های مربوط به هر قسمت را نیز به صورت تودرتو نمایش می‌دهد.
    """
    # نمایش کیفیت‌ها به صورت فقط خواندنی در جزئیات قسمت
    qualities = EpisodeQualitySerializer(many=True, read_only=True)

    class Meta:
        model = Episode
        fields = ['id', 'season', 'title', 'slug', 'qualities', 'movie']
        read_only_fields = ['slug']
        extra_kwargs = {
            'movie': {'write_only': True}
        }

# --- سریالایزرهای فیلم ---
class MovieListSerializer(serializers.ModelSerializer):
    """ سریالایزر سبک برای لیست فیلم‌ها (بدون تغییر) """
    class Meta:
        model = Movie
        fields = ['id', 'title', 'poster', 'release_date', 'status']

class MovieDetailSerializer(serializers.ModelSerializer):
    """
    سریالایزر کامل برای جزئیات فیلم، شامل قسمت‌های مرتبط.
    """
    genres = serializers.StringRelatedField(many=True, read_only=True)
    # نمایش قسمت‌های مرتبط با فیلم (مثلا نسخه‌های مختلف یا پشت صحنه)
    episodes = EpisodeSerializer(many=True, read_only=True)

    class Meta:
        model = Movie
        fields = [
            'id', 'title', 'description', 'poster', 'release_date',
            'genres', 'status', 'created_at', 'episodes'
        ]

class SeriesListSerializer(serializers.ModelSerializer):
    """ سریالایزر سبک برای لیست سریال‌ها (بدون تغییر) """
    class Meta:
        model = Series
        fields = ['id', 'title', 'poster', 'release_date', 'status']

class SeriesDetailSerializer(serializers.ModelSerializer):
    """
    سریالایزر کامل برای جزئیات سریال، شامل قسمت‌ها و کیفیت‌هایشان.
    """
    genres = serializers.StringRelatedField(many=True, read_only=True)
    # نمایش قسمت‌های سریال به صورت تودرتو
    episodes = EpisodeSerializer(many=True, read_only=True)

    class Meta:
        model = Series
        fields = [
            'id', 'title', 'description', 'poster', 'release_date',
            'genres', 'status', 'created_at', 'episodes'
        ]