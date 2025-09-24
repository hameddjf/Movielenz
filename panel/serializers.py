# admin_panel/serializers.py

from rest_framework import serializers

from django.utils.translation import gettext_lazy as _

from user_account.models import User
from user_account.enums import  UserRole


class UserAdminSerializer(serializers.ModelSerializer):
    """
    سریالایزر برای مدیریت کامل کاربران در پنل ادمین.
    """
    # فیلد پسورد فقط برای نوشتن (ایجاد یا تغییر) است و هرگز خوانده نمی‌شود.
    password = serializers.CharField(
        write_only=True, 
        required=False,  # برای ویرایش کاربر، تغییر پسورد الزامی نیست
        style={'input_type': 'password'}
    )
    
    # نمایش نام کامل کاربر برای راحتی در پنل
    full_name = serializers.CharField(source='get_full_name', read_only=True)

    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'email',
            'full_name', # فیلد خواندنی
            'first_name',
            'last_name',
            'password', # فیلد نوشتنی
            'role',
            'activated',
            'subscription_status',
            'subscription_end_date',
            'date_joined',
            'profile_picture',
        ]
        # این فیلدها فقط در درخواست‌های POST/PATCH/PUT نوشته می‌شوند
        extra_kwargs = {
            'first_name': {'write_only': True, 'required': False},
            'last_name': {'write_only': True, 'required': False},
        }
        read_only_fields = ['date_joined']

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

    def update(self, instance, validated_data):
        """
        متد به‌روزرسانی کاربر. اگر پسورد جدیدی ارسال شده باشد، آن را هش می‌کند.
        """
        password = validated_data.pop('password', None)

        current_user_role = getattr(instance, 'role', None) 
        requesting_user = self.context.get('request').user if 'request' in self.context else None
        requesting_user_role = getattr(requesting_user, 'role', None) if requesting_user else None
        role_to_set = validated_data.get('role')

        if role_to_set:
          if requesting_user_role == UserRole.ADMIN and role_to_set == UserRole.OWNER:
                raise serializers.ValidationError({
                    'role': _("شما به عنوان Admin مجاز به تعیین نقش Owner نیستید.")
                })
        instance = super().update(instance, validated_data)

        if password:
            instance.set_password(password)
            instance.save()

        return instance