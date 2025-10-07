import logging
from urllib.parse import urlparse

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext_lazy as _
from django.urls import resolve, Resolver404
from django.utils.http import urlsafe_base64_decode
from django.core.mail import send_mail
from django.urls import reverse
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode
from rest_framework import generics, viewsets, status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError
    
from .models import WatchlistItem, FavoriteItem, RecentlyWatchedItem
from .tokens import account_activation_token
from .serializers import (
    CustomRegisterSerializer, UserProfileSerializer,
    WatchlistItemSerializer, FavoriteItemSerializer, RecentlyWatchedItemSerializer,
    CustomPasswordResetConfirmSerializer,
)
# from django.urls import reverse
User = get_user_model()
logger = logging.getLogger(__name__)
# class UserRegistrationView(generics.CreateAPIView):
#     queryset = User.objects.all()
#     serializer_class = CustomRegisterSerializer
#     permission_classes = [AllowAny]

# accounts/views.py
from dj_rest_auth.views import (
    LoginView, LogoutView, UserDetailsView, PasswordChangeView,
    PasswordResetView, PasswordResetConfirmView as BasePasswordResetConfirmView
)
from dj_rest_auth.registration.views import (
    RegisterView
)

from .serializers import (
    CustomRegisterSerializer,
    # CustomUserDetailsSerializer
)

# --- ویوهای مربوط به ثبت‌نام و تایید ایمیل ---


# class CustomRegisterView(RegisterView):
#     """
#     ویوی سفارشی برای ثبت‌نام کاربر با استفاده از ایمیل و رمز عبور.

#     این ویو از `CustomRegisterSerializer` برای افزودن فیلدهای سفارشی
#     (first_name, last_name, date_of_birth) به فرآیند ثبت‌نام استفاده می‌کند.
#     پس از ثبت‌نام موفق، در صورتی که تایید ایمیل فعال باشد، یک ایمیل
#     برای کاربر ارسال خواهد شد.
#     """
#     serializer_class = CustomRegisterSerializer

    # def perform_create(self, serializer):
    #     """
    #     این متد پس از اعتبارسنجی موفق سریالایزر فراخوانی می‌شود.
    #     منطق ایجاد کاربر در متد `save` سریالایزر مدیریت شده است.
    #     """
    #     user = serializer.save(self.request)
    #     logger.info(f"کاربر جدید با ایمیل {user.email} با موفقیت ثبت‌نام کرد.")
    #     return user
    
class CustomVerifyEmailView(APIView):
    def get(self, request, uidb64, token):
        print("🔗 verify view:", uidb64, token)
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
            print("Found user:", user.email, user.activated)
        except Exception as e:
            print("Error decoding UID:", e)
            return Response({'error': 'لینک نامعتبر'}, status=status.HTTP_400_BAD_REQUEST)

        if account_activation_token.check_token(user, token):
            user.activated = True
            user.save()
            return Response({'success': '✅ تأیید شد'}, status=status.HTTP_200_OK)
        else:
            return Response({'error': 'لینک منقضی/ناصحیح'}, status=status.HTTP_400_BAD_REQUEST)

# class CustomVerifyEmailView(VerifyEmailView):
#     """
#     ویوی سفارشی برای تایید ایمیل کاربر پس از کلیک روی لینک ارسالی.

#     می‌توان با override کردن متد post، منطق سفارشی (مانند اهدای امتیاز به کاربر)
#     را پس از تایید موفق ایمیل پیاده‌سازی کرد.
#     """
#     def post(self, request, *args, **kwargs):
#         response = super().post(request, *args, **kwargs)
#         if response.status_code == status.HTTP_200_OK:
#             # ایمیل با موفقیت تایید شده است.
#             logger.info(f"ایمیل برای کاربر '{request.user}' با موفقیت تایید شد.")
#             # در اینجا می‌توانید منطق سفارشی خود را اضافه کنید.
#             # برای مثال:
#             # request.user.add_welcome_points()
#             # request.user.save()
#             return Response({"detail": "ایمیل شما با موفقیت تایید شد."}, status=status.HTTP_200_OK)
#         return response

class CustomRegisterView(RegisterView):
    """
    ویوی ثبت‌نام که از سریالایزر سفارشی استفاده می‌کند.
    منطق ارسال ایمیل توسط allauth مدیریت می‌شود.
    """
    serializer_class = CustomRegisterSerializer

class ResendEmailVerificationView(generics.GenericAPIView):
    """
    ویوی ارسال مجدد ایمیل تأیید برای کاربرانی که ثبت‌نام کرده‌اند.
    """
    permission_classes = [AllowAny]
    def post(self, request, *args, **kwargs):
        email = request.data.get('email')

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({"detail": "کاربری با این ایمیل وجود ندارد."}, status=status.HTTP_404_NOT_FOUND)

        # ایجاد لینک تأیید
        token = account_activation_token.make_token(user)
        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
        activation_link = f"http://{request.get_host()}{reverse('rest_verify_email', kwargs={'uidb64': uidb64, 'token': token})}"

        subject = 'تأیید حساب کاربری'
        message = f'لطفا برای تأیید حساب خود به لینک زیر مراجعه کنید:\n{activation_link}'
        send_mail(subject, message, 'hameddjf106@gmail.com', [user.email])

        return Response({"detail": "ایمیل تأیید مجدداً ارسال شد."}, status=status.HTTP_200_OK)

# --- ویوهای مربوط به لاگین، پروفایل و مدیریت رمز عبور ---

class CustomLoginView(LoginView):
    permission_classes = [AllowAny]
    authentication_classes = []
    def post(self, request, *args, **kwargs):
        # حالا این پرینت باید اجرا شود
        print("✅ CustomLoginView.post method has been executed!")
        logger.info(f"Login attempt with data: {request.data}")
        
        email = request.data.get('email', 'نامشخص')
        logger.info(f"تلاش برای ورود توسط کاربر با ایمیل: {email}")

        response = super().post(request, *args, **kwargs)

        if response.status_code == status.HTTP_200_OK:
            logger.info(f"ورود موفق برای کاربر با ایمیل: {email}")
        else:
            # اگر اینجا رسیدید، یعنی مشکل از اعتبار (credentials) است نه دسترسی (permission)
            print(f"❌ Login failed inside the view. Response: {response.data}")
            logger.warning(f"تلاش ناموفق برای ورود با ایمیل: {email}. دلیل: {response.data}")
            
        return response

class CustomLogoutView(LogoutView):
    """
    ویوی سفارشی برای خروج کاربر.

    این ویو به صراحت فقط متد POST را می‌پذیرد تا از خروج تصادفی کاربر
    از طریق درخواست‌های GET (مثلاً توسط موتورهای جستجو) جلوگیری شود.
    یک پیام موفقیت‌آمیز سفارشی نیز در پاسخ بازگردانده می‌شود.
    """
    http_method_names = ['post', 'options']
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user_email = request.user.email
        super().post(request, *args, **kwargs)
        logger.info(f"کاربر با ایمیل {user_email} با موفقیت خارج شد.")
        return Response(
            {"detail": "شما با موفقیت خارج شدید."},
            status=status.HTTP_200_OK
        )

# class CustomUserDetailsView(UserDetailsView):
#     """
#     ویوی سفارشی برای نمایش و ویرایش اطلاعات کاربر احراز هویت شده.

#     این ویو از `CustomUserDetailsSerializer` استفاده می‌کند تا فیلدهای سفارشی
#     مانند `date_of_birth` را نیز در بر بگیرد و امکان ویرایش آن‌ها را فراهم کند.
#     """
#     serializer_class = CustomUserDetailsSerializer
#     permission_classes = [IsAuthenticated]


class CustomPasswordChangeView(PasswordChangeView):
    """
    ویوی سفارشی برای تغییر رمز عبور توسط کاربر لاگین کرده.
    پاسخ موفقیت‌آمیز سفارشی‌سازی شده است.
    """
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == status.HTTP_200_OK:
            logger.info(f"کاربر {request.user.email} رمز عبور خود را با موفقیت تغییر داد.")
            return Response({"detail": "رمز عبور شما با موفقیت تغییر یافت."}, status=status.HTTP_200_OK)
        return response


class CustomPasswordResetView(PasswordResetView):
    """
    ویوی سفارشی برای ارسال ایمیل بازیابی رمز عبور.
    """

    def post(self, request, *args, **kwargs):
        logger.debug(f"داده های ورودی: {request.data}")
        email_address = request.data.get('email')
        if not email_address:
            logger.warning("ایمیل در داده های ورودی یافت نشد.")
            return Response(
                {"detail": "لطفا ایمیل خود را وارد کنید."},
                status=status.HTTP_400_BAD_REQUEST)
        try:
            response = super().post(request, *args, **kwargs)
            if response.status_code == status.HTTP_200_OK:
                logger.info(f"ایمیل بازیابی رمز عبور برای {email_address} ارسال شد (طبق پاسخ super()).")
                return Response(
                    {"detail": "ایمیل بازیابی رمز عبور برای شما ارسال شد. لطفاً صندوق ورودی خود را بررسی کنید."},
                    status=status.HTTP_200_OK)
            else:
                logger.error(f"خطا در ارسال ایمیل بازیابی رمز عبور توسط super().post(). کد وضعیت: {response.status_code}. پاسخ: {response.data}")
                return response
        except Exception as e:
            logger.exception(f"خطای غیرمنتظره در هنگام پردازش بازیابی رمز عبور: {e}")
            return Response(
                {"detail": "یک خطای داخلی رخ داده است. لطفاً بعداً دوباره امتحان کنید."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class CustomPasswordResetConfirmView(BasePasswordResetConfirmView):
    """
    ویوی سفارشی برای تأیید و نهایی کردن فرآیند بازنشانی رمز عبور.
    (نسخه اصلاح شده و نهایی)
    """
    serializer_class = CustomPasswordResetConfirmSerializer

    def post(self, request, *args, **kwargs):
        """
        پردازش درخواست POST برای تنظیم رمز عبور جدید.
        """
        logger.debug(f"درخواست تأیید بازنشانی رمز عبور دریافت شد. UID: {kwargs.get('uidb64')}")

        # ======================= شروع بخش اصلاح شده =======================

        # 1. یک کپی از داده‌های Body درخواست (new_password1, new_password2) تهیه می‌کنیم.
        serializer_data = request.data.copy()

        # 2. مقادیر uid و token را از پارامترهای URL (kwargs) به داده‌های سریالایزر اضافه می‌کنیم.
        #    سریالایزر dj_rest_auth انتظار فیلدی به نام 'uid' دارد، نه 'uidb64'.
        serializer_data['uid'] = kwargs.get('uidb64')
        serializer_data['token'] = kwargs.get('token')

        # 3. حالا سریالایزر را با داده‌های کامل (هم Body و هم URL) نمونه‌سازی می‌کنیم.
        serializer = self.get_serializer(data=serializer_data)

        # ======================== پایان بخش اصلاح شده ========================

        try:
            # اعتبارسنجی داده‌ها. حالا سریالایزر هم رمزها را چک می‌کند و هم توکن را.
            serializer.is_valid(raise_exception=True)
            
            # ذخیره رمز عبور جدید
            serializer.save()
            
            logger.info(f"رمز عبور برای کاربر با UID: {kwargs.get('uidb64')} با موفقیت تغییر یافت.")
            return Response(
                {"detail": "رمز عبور شما با موفقیت تغییر یافت."},
                status=status.HTTP_200_OK
            )

        except ValidationError as e:
            logger.warning(f"خطای اعتبارسنجی در تأیید بازنشانی رمز عبور: {e.detail}")
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.exception(f"خطای غیرمنتظره در هنگام تأیید بازنشانی رمز عبور: {e}")
            return Response(
                {"detail": "یک خطای داخلی در سرور رخ داده است. لطفاً بعداً دوباره تلاش کنید."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]
    
    http_method_names = ['get', 'patch', 'head', 'options']
    

    def get_object(self):
        return self.request.user 

    def perform_update(self, serializer):
        serializer.save(user=self.request.user)


class BaseUserContentInteractionViewSet(viewsets.ModelViewSet):
    http_method_names = ['get', 'post', 'delete', 'head', 'options']
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.Meta.model.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        
        content_type = serializer.context.get('content_type_model')
        object_id = request.data.get('object_id')
        
        current_status = status.HTTP_201_CREATED
        if hasattr(serializer, '_is_existing_instance') and serializer._is_existing_instance:
            current_status = status.HTTP_200_OK
            
        return Response(serializer.data, status=current_status, headers=headers)
        
        # if self.Meta.model in [WatchlistItem, FavoriteItem]:
        #     if self.Meta.model.objects.filter(
        #         user=request.user, 
        #         content_type=content_type, 
        #         object_id=object_id
        #     ).exists():
        #         return Response(
        #             {"detail": _("این آیتم از قبل در لیست شما وجود دارد.")},
        #             status=status.HTTP_400_BAD_REQUEST
        #         )
        
        # return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    @action(detail=False, methods=['delete'], url_path='content')
    def delete_by_content_item(self, request, *args, **kwargs):
        content_item_url = request.data.get('content_item_url')

        if not content_item_url:
            return Response(
                {"content_item_url": [_("This field is required.")]},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            parsed_url = urlparse(content_item_url)
            path = parsed_url.path
            match = resolve(path)
        except Resolver404:
            return Response({'content_item_url': _("URL path does not match any known patterns.")}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'content_item_url': _("Invalid URL format or path: %(error)s") % {'error': str(e)}}, status=status.HTTP_400_BAD_REQUEST)
        serializer_class = self.get_serializer_class()
        temp_serializer_instance = serializer_class() 
        
        model_class = temp_serializer_instance._get_model_from_view_match(match)

        if not model_class:
            return Response({'content_item_url': _("Could not determine the model type from the provided URL.")}, status=status.HTTP_400_BAD_REQUEST)

        object_pk_str = match.kwargs.get('pk')
        if not object_pk_str:
            for kw_val in match.kwargs.values():
                if isinstance(kw_val, (int, str)) and str(kw_val).isdigit():
                    object_pk_str = str(kw_val)
                    break
            if not object_pk_str:
                return Response({'content_item_url': _("Could not extract object ID from the URL.")}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            object_pk = int(object_pk_str)
        except ValueError:
            return Response({'content_item_url': _("Object ID extracted from URL is not a valid integer.")}, status=status.HTTP_400_BAD_REQUEST)
        content_type_resolved = ContentType.objects.get_for_model(model_class)
        try:
            instance = self.Meta.model.objects.filter(
                user=request.user,
                content_type=content_type_resolved,
                object_id=object_pk
            ).first()

            if instance:
                self.perform_destroy(instance) 
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response({"detail": _("آیتم یافت نشد.")}, status=status.HTTP_404_NOT_FOUND)
                
        except Exception as e: 
            logger = logging.getLogger(__name__)
            logger.error(f"Error deleting interaction item for user {request.user.id} with content_type {content_type_resolved.id}, object_id {object_pk}: {e}")
            return Response({"detail": _("An error occurred while deleting the item.")}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class WatchlistViewSet(BaseUserContentInteractionViewSet):
    serializer_class = WatchlistItemSerializer
    
    class Meta:
        model = WatchlistItem

class FavoriteViewSet(BaseUserContentInteractionViewSet):
    serializer_class = FavoriteItemSerializer

    class Meta:
        model = FavoriteItem

class RecentlyWatchedViewSet(BaseUserContentInteractionViewSet):
    serializer_class = RecentlyWatchedItemSerializer

    class Meta:
        model = RecentlyWatchedItem

    def get_queryset(self):
        return super().get_queryset().order_by('-watched_at')