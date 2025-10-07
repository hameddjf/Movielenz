# accounts/serializers.py
from dj_rest_auth.registration.serializers import RegisterSerializer
from dj_rest_auth.serializers import UserDetailsSerializer, PasswordResetConfirmSerializer as BasePasswordResetConfirmSerializer
from django.conf import settings
from django.core.mail import send_mail
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.urls import resolve, Resolver404, reverse, NoReverseMatch
from django.db import IntegrityError
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.contrib.auth import authenticate

from urllib.parse import urlparse

from rest_framework import serializers

from .models import WatchlistItem, FavoriteItem, RecentlyWatchedItem, User
from .tokens import account_activation_token

from movielenz.models import Genre

import logging
logger = logging.getLogger(__name__)

class BaseContentSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    title = serializers.CharField(read_only=True)

    class Meta:
        fields = ['id', 'title'] #, 'type']


User = get_user_model()

class ContentObjectRelatedField(serializers.RelatedField):
    """
    A custom field to use for the `content_object` generic relationship.
    """
    def to_representation(self, value):
        """
        Serialize tagged objects to a simple textual representation.
        """
        return {
            'id': value.pk,
            'title': str(value),
            'type': value.__class__.__name__.lower()
        }

    def to_internal_value(self, data):
        raise NotImplementedError("Direct assignment to content_object is not supported via this field.")


# class UserRegistrationSerializer(serializers.ModelSerializer):
#     password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
#     # password2 = serializers.CharField(write_only=True, required=False, label=_("Confirm password"))

#     class Meta:
#         model = User
#         fields = ('email', 'first_name', 'last_name', 'password', 'date_of_birth')
#         extra_kwargs = {
#             'first_name': {'required': False},
#             'last_name': {'required': False},
#             'date_of_birth': {'required': False, 'allow_null': True},
#         }

#     # def validate(self, attrs):
#     #     if attrs['password2'] != attrs['password']:
#     #         raise serializers.ValidationError({"password2": _("Password2 fields didn't match.")})
#     #     return attrs

#     def create(self, validated_data):
#         """
#         این متد برای اطمینان از هش شدن صحیح رمز عبور ضروری است.
#         """
#         user = User.objects.create_user(
#             email=validated_data['email'],
#             password=validated_data['password'],
#             first_name=validated_data.get('first_name', ''),
#             last_name=validated_data.get('last_name', ''),
#             date_of_birth=validated_data.get('date_of_birth')
#         )
#         return user


# class CustomRegisterSerializer(RegisterSerializer):
#     first_name = serializers.CharField(max_length=30, required=False)
#     last_name = serializers.CharField(max_length=30, required=False)
#     date_of_birth = serializers.DateField(required=False, allow_null=True)

#     def get_cleaned_data(self):
#         # داده‌های اصلی (ایمیل، پسورد) را از کلاس پدر دریافت کنید
#         data = super().get_cleaned_data()
#         # فیلدهای سفارشی خود را به آن اضافه کنید
#         data.update({
#             'first_name': self.validated_data.get('first_name', ''),
#             'last_name': self.validated_data.get('last_name', ''),
#             'date_of_birth': self.validated_data.get('date_of_birth', None),
#         })
#         return data

#     def save(self, request):
#         # متد save کلاس پدر را فراخوانی کنید تا کاربر ایجاد شود
#         user = super().save(request)
#         # فیلدهای اضافی را به کاربر اختصاص دهید
#         user.first_name = self.validated_data.get('first_name', '')
#         user.last_name = self.validated_data.get('last_name', '')
#         user.date_of_birth = self.validated_data.get('date_of_birth', None)
#         user.save()
#         return user

class ResendEmailVerificationSerializer(serializers.Serializer):
    """
    سریالایزر برای اعتبارسنجی ایمیل ورودی جهت ارسال مجدد لینک تایید.
    """
    email = serializers.EmailField(required=True)
class PasswordResetEmailSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)

class CustomPasswordResetConfirmSerializer(BasePasswordResetConfirmSerializer):
    """
    سریالایزر سفارشی برای تأیید بازنشانی رمز عبور.
    این سریالایزر وظیفه اعتبارسنجی رمز عبور جدید و تکرار آن را بر عهده دارد.
    """
    # می‌توانیم پیام‌های خطا را در اینجا شخصی‌سازی کنیم، اما برای شروع،
    # استفاده از مقادیر پیش‌فرض dj_rest_auth کافی و استاندارد است.
    # به عنوان مثال، اگر بخواهیم فیلدها را بازنویسی کنیم:
    # new_password1 = serializers.CharField(max_length=128, write_only=True, required=True)
    # new_password2 = serializers.CharField(max_length=128, write_only=True, required=True)

    def save(self):
        # متد save در کلاس والد (BasePasswordResetConfirmSerializer)
        # به طور کامل منطق تغییر رمز عبور را مدیریت می‌کند.
        # این متد از طریق context که توسط ویو فراهم می‌شود به request دسترسی دارد
        # و کاربر را از آن استخراج کرده و رمز عبور جدید را برایش تنظیم می‌کند.
        # بنابراین نیازی به بازنویسی این متد نیست مگر اینکه بخواهیم رفتار خاصی اضافه کنیم.
        return super().save()

class CustomLoginSerializer(serializers.Serializer): # دیگر از LoginSerializer ارث‌بری نمی‌کنیم
    username = None # اطمینان از اینکه فیلد username وجود ندارد
    email = serializers.EmailField(required=True, write_only=True)
    password = serializers.CharField(required=True, write_only=True, style={'input_type': 'password'})

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')
        request = self.context.get('request')

        if not email or not password:
            raise serializers.ValidationError(_('Must include "email" and "password".'), code='authorization')

        print(f"✅ CustomLoginSerializer.validate is running for email: {email}")
        logger.info(f"Serializer validation attempt for email: {email}")

        # فراخوانی مستقیم authenticate با پارامترهای صحیح (email و password)
        # بک‌اند allauth این پارامترها را دریافت و پردازش خواهد کرد
        user = authenticate(request=request, email=email, password=password)

        if not user:
            # اگر authenticate نتواند کاربر را پیدا کند، None برمی‌گرداند
            print(f"❌ Authentication failed for email: {email}. authenticate() returned None.")
            logger.warning(f"Authentication failed for {email}. User not found or password incorrect.")
            raise serializers.ValidationError(_('Unable to log in with provided credentials.'), code='authorization')

        # بررسی اینکه آیا کاربر مجاز به ورود است (مثلاً غیرفعال نشده باشد)
        if not user.activated:
            print(f"❌ Authentication failed for email: {email}. User is inactive.")
            logger.warning(f"Authentication failed for {email}. User account is inactive.")
            raise serializers.ValidationError(_('User account is disabled.'), code='authorization')
        
        # اگر همه چیز موفقیت‌آمیز بود، کاربر احراز هویت شده را در attrs قرار می‌دهیم
        # تا LoginView بتواند از آن برای ایجاد توکن استفاده کند.
        attrs['user'] = user
        print(f"✅ Authentication successful for email: {email}")
        logger.info(f"Authentication successful for {email} in serializer.")
        return attrs


class CustomRegisterSerializer(RegisterSerializer):
    """
    سریالایزر سفارشی برای ثبت‌نام کاربر که به طور کامل مستقل عمل می‌کند.
    """
    # فیلدهای غیر ضروری را حذف می‌کنیم
    username = None
    password1 = None
    password2 = None
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})

    # فیلدهای سفارشی خود را تعریف می‌کنیم
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    date_of_birth = serializers.DateField(required=False, allow_null=True)

    def validate(self, attrs):
        """
        این متد را برای حذف اعتبارسنجی password2 نگه می‌داریم.
        """
        # با برگرداندن مستقیم attrs، از اعتبارسنجی والد صرف نظر می‌کنیم.
        return attrs

    def save(self, request):
        """
        متد save را به طور کامل بازنویسی می‌کنیم تا کنترل ایجاد کاربر را در دست بگیریم
        و از خطای AttributeError مربوط به allauth جلوگیری کنیم.
        """
        data = self.validated_data
        email = self.validated_data.get('email')
        password = self.validated_data.get('password')

        first_name = self.validated_data.get('first_name', '')
        last_name = self.validated_data.get('last_name', '')
        date_of_birth = self.validated_data.get('date_of_birth', None)

        user = User.objects.create_user(
            username=email,  # یا هر مقدار یکتای دیگر
            password=data['password'],
            email=email,
        )
        
        subject = 'تأیید حساب کاربری'
        message = f'لطفا برای تأیید حساب خود به لینک زیر مراجعه کنید:\n' f'http://{request.get_host()}{reverse("rest_verify_email", kwargs={"uidb64": urlsafe_base64_encode(force_bytes(user.pk)), "token": account_activation_token.make_token(user)})}'
        send_mail(subject, message, 'hameddjf106@gmail.com', [user.email])
        token = account_activation_token.make_token(user)
        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
        activation_link = f"http://{request.get_host()}{reverse('rest_verify_email', kwargs={'uidb64': uidb64, 'token': token})}"
        print("Activation link:", activation_link)
        # تنظیم مقادیر فیلدهای سفارشی
        user.first_name = first_name
        user.last_name = last_name
        user.date_of_birth = date_of_birth
        user.save()

        return user
    
# class CustomUserDetailsSerializer(UserDetailsSerializer):
#     """
#     سریالایزر سفارشی برای نمایش و ویرایش اطلاعات کاربر.
#     این سریالایزر فیلدهای سفارشی مدل User را در پاسخ API پروفایل کاربر
#     (user-details) نمایش داده و امکان ویرایش آن‌ها را فراهم می‌کند.
#     """
#     date_of_birth = serializers.DateField(required=False, allow_null=True)

#     class Meta(UserDetailsSerializer.Meta):
#         # فیلدهای کلاس پدر را به ارث برده و فیلد جدید را اضافه می‌کنیم.
#         fields = UserDetailsSerializer.Meta.fields + ('date_of_birth',)
#         read_only_fields = (settings.ACCOUNT_EMAIL_VERIFICATION,)

class UserProfileSerializer(serializers.ModelSerializer):
    preferred_genre_ids = serializers.PrimaryKeyRelatedField(
        # queryset=ContentType.objects.none(),
        queryset = Genre.objects.none(),
        many=True, source='preferred_genres', 
        write_only=True, 
        help_text=_("لیستی از ID های ژانرهای مورد علاقه"),
        required=False
    )
    preferred_genres_hyperlinks = serializers.HyperlinkedRelatedField(
        many=True,
        source='preferred_genres', 
        read_only=True,          
        view_name='genre-detail',
        help_text=_("لینک به ژانرهای مورد علاقه (فقط خواندنی).")
    )
    preferred_genres_display = serializers.StringRelatedField(
        source='preferred_genres',
        many=True,
        read_only=True,
        help_text=_("نام ژانرهای مورد علاقه (فقط خواندنی).")
    )

    class Meta:
        model = User
        fields = (
            'id', 'email', 'first_name', 'last_name','activated', 'profile_picture', 
            'date_of_birth', 'subscription_status', 'subscription_end_date',
            'preferred_language', 'preferred_genres_display',
            'preferred_genres_hyperlinks','preferred_genre_ids',
            'last_login', 'date_joined'
        )
        read_only_fields = ('email', 'subscription_status', 'subscription_end_date', 'last_login', 'date_joined', 'id',)
        extra_kwargs = {
            'first_name': {'required': False, 'allow_blank': True},
            'last_name': {'required': False, 'allow_blank': True},
            'profile_picture': {'required': False, 'allow_null': True},
            'date_of_birth': {'required': False, 'allow_null': True},
            'preferred_language': {'required': False},
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            actual_queryset = Genre.objects.all()
            if 'preferred_genre_ids' in self.fields:
                self.fields['preferred_genre_ids'].queryset = actual_queryset
            if 'preferred_genres_hyperlinks' in self.fields:
                self.fields['preferred_genres_hyperlinks'].queryset = actual_queryset
        except ImportError:
            pass


# ----- Serializers for User-Content Interactions -----

class BaseUserContentInteractionSerializer(serializers.ModelSerializer):
    # content_type_name = serializers.CharField(write_only=True, help_text=_("نام مدل محتوا (مثلا: 'movie' یا 'series')"))
    # object_id = serializers.IntegerField(write_only=True, help_text=_("شناسه شیء محتوا"))
    
    content_item_url = serializers.URLField(
        write_only=True, 
        help_text=_('{"content_item_url" : "http://127.0.0.1:8000/movie/3/)"}')
    )
    
    content_details = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = None
        fields = ('id', 'user', 'content_item_url', 'content_details', 'added_at')
        read_only_fields = ('user', 'added_at', 'id')
        
    def _get_model_from_view_match(self, match):
        """
         مدل را از resolved URL match استخراج کند.
        """
        view_class = getattr(match.func, 'cls', None)
        if not view_class:
            return None
        
        queryset = getattr(view_class, 'queryset', None)
        if queryset is not None:
            return queryset.model
        
        serializer_class = getattr(view_class, 'serializer_class', None)
        if serializer_class and hasattr(serializer_class, 'Meta') and hasattr(serializer_class.Meta, 'model'):
            return serializer_class.Meta.model
            
        return None

    def get_content_details(self, obj):
        if obj.content_object:
            request = self.context.get('request')
            item_url = None
            model_to_view_name_map = self.context.get('model_to_view_name_map', {})
            view_name = model_to_view_name_map.get(obj.content_type.model)

            if request and view_name:
                try:
                    item_url = reverse(view_name, kwargs={'pk': obj.content_object.pk}, request=request)
                except NoReverseMatch:
                    item_url = _("URL not resolvable") # یا None

            return {
                'id': obj.content_object.pk,
                'title': getattr(obj.content_object, 'title', str(obj.content_object)), # فرض بر اینکه 'title' وجود دارد
                'type': obj.content_type.model,
                'url': item_url
            }
        return None

    def validate(self, attrs):
        content_item_url = attrs.get('content_item_url')
        current_user = self.context['request'].user
        if self.instance and not content_item_url:
            return super().validate(attrs)
        if not self.instance and not content_item_url:
            raise serializers.ValidationError({"content_item_url": _("This field is required for creation.")})
        if content_item_url:
            try:
                parsed_url = urlparse(content_item_url)
                path = parsed_url.path
                match = resolve(path)
            except Resolver404:
                raise serializers.ValidationError({'content_item_url': _("URL path does not match any known patterns.")})
            except Exception as e:
                raise serializers.ValidationError({'content_item_url': _("Invalid URL format or path: %(error)s") % {'error': str(e)}})

            model_class = self._get_model_from_view_match(match)
            if not model_class:
                raise serializers.ValidationError({'content_item_url': _("Could not determine the model type from the provided URL.")})

            object_pk_str = match.kwargs.get('pk')
            if not object_pk_str:
                for kw_val in match.kwargs.values():
                    if isinstance(kw_val, (int, str)) and str(kw_val).isdigit():
                        object_pk_str = str(kw_val)
                        break
                if not object_pk_str:
                    raise serializers.ValidationError({'content_item_url': _("Could not extract object ID from the URL.")})
            try:
                object_pk = int(object_pk_str)
            except ValueError:
                 raise serializers.ValidationError({'content_item_url': _("Object ID extracted from URL is not a valid integer.")})
            if not model_class.objects.filter(pk=object_pk).exists():
                raise serializers.ValidationError({'content_item_url': _("The content object linked by the URL does not exist.")})
            
            content_type_resolved = ContentType.objects.get_for_model(model_class)
            
            attrs['resolved_content_type'] = content_type_resolved
            attrs['resolved_object_id'] = object_pk

            if not self.instance:
                InteractionModel = self.Meta.model 
                existing_item = InteractionModel.objects.filter(
                    user=current_user, 
                    content_type=content_type_resolved, 
                    object_id=object_pk
                ).first()
                if existing_item:
                    attrs['existing_item_instance'] = existing_item
                # if InteractionModel.objects.filter(
                #     user=current_user, 
                #     content_type=content_type_resolved, 
                #     object_id=object_pk
                # ).exists():
                #     raise serializers.ValidationError(_("This item is already in your list."))
        return attrs

    def create(self, validated_data):
        existing_item = validated_data.pop('existing_item_instance', None)
        if existing_item:
            self.instance = existing_item
            self._is_existing_instance = True
            return self.instance

        self._is_existing_instance = False
        
        validated_data.pop('content_item_url', None) 
        
        content_type = validated_data.pop('resolved_content_type')
        object_id = validated_data.pop('resolved_object_id')
        
        validated_data['user'] = self.context['request'].user
        validated_data['content_type'] = content_type
        validated_data['object_id'] = object_id
        
        try:
            return super().create(validated_data)
        except IntegrityError:
            InteractionModel = self.Meta.model
            instance = InteractionModel.objects.filter(
                user=validated_data['user'], 
                content_type=validated_data['content_type'], 
                object_id=validated_data['object_id']
            ).first()
            if instance:
                self.instance = instance
                self._is_existing_instance = True
                return instance
            raise serializers.ValidationError(_("This item is already in your list (database constraint)."))
        except Exception as e:
            raise serializers.ValidationError(str(e))


class WatchlistItemSerializer(BaseUserContentInteractionSerializer):
    class Meta(BaseUserContentInteractionSerializer.Meta):
        model = WatchlistItem


class FavoriteItemSerializer(BaseUserContentInteractionSerializer):
    class Meta(BaseUserContentInteractionSerializer.Meta):
        model = FavoriteItem

      
class RecentlyWatchedItemSerializer(BaseUserContentInteractionSerializer):
    progress_seconds = serializers.IntegerField(required=False, allow_null=True)

    class Meta:
        model = RecentlyWatchedItem
        fields = (
            'id',
            'user',
            "content_item_url",
            # 'content_type_name',
            # 'object_id',        
            'content_details',
            'watched_at',     
            'progress_seconds'
        )
        read_only_fields = ('user', 'id', 'watched_at')

    def create(self, validated_data):
        ModelClass = self.Meta.model
        user_instance = validated_data['user']
        content_type = validated_data.pop('resolved_content_type')
        object_id = validated_data.pop('resolved_object_id')
        validated_data.pop('content_item_url', None)

        lookup_data = {
            'user': user_instance,
            'content_type': content_type,
            'object_id': object_id,
        }
        defaults_data = {
            # 'progress_seconds': validated_data.get('progress_seconds', self.fields['progress_seconds'].default),
            'progress_seconds': validated_data.get('progress_seconds'),
            'watched_at': timezone.now()
        }
        instance, created = ModelClass.objects.update_or_create(
            **lookup_data,
            defaults=defaults_data
        )
        return instance

    def update(self, instance, validated_data):
        instance.progress_seconds = validated_data.get('progress_seconds', instance.progress_seconds)
        instance.watched_at = timezone.now()
        instance.save(update_fields=['progress_seconds', 'watched_at'])
        return instance