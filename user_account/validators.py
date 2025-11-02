"""
Custom validators for user data.
Ensures data quality and security.
"""
import re
from datetime import date, timedelta
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.core.validators import EmailValidator as BaseEmailValidator


class StrongPasswordValidator:
    """
    Validates password strength.
    Requirements:
    - Minimum 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character
    """
    
    def __call__(self, value):
        """Validate password strength."""
        if len(value) < 8:
            raise ValidationError(
                _('رمز عبور باید حداقل 8 کاراکتر باشد.'),
                code='password_too_short'
            )
        
        if not re.search(r'[A-Z]', value):
            raise ValidationError(
                _('رمز عبور باید حداقل یک حرف بزرگ داشته باشد.'),
                code='password_no_upper'
            )
        
        if not re.search(r'[a-z]', value):
            raise ValidationError(
                _('رمز عبور باید حداقل یک حرف کوچک داشته باشد.'),
                code='password_no_lower'
            )
        
        if not re.search(r'[0-9]', value):
            raise ValidationError(
                _('رمز عبور باید حداقل یک عدد داشته باشد.'),
                code='password_no_digit'
            )
        
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', value):
            raise ValidationError(
                _('رمز عبور باید حداقل یک کاراکتر خاص داشته باشد.'),
                code='password_no_special'
            )
    
    def get_help_text(self):
        """Return help text for password requirements."""
        return _(
            'رمز عبور باید حداقل 8 کاراکتر، شامل حروف بزرگ و کوچک، '
            'اعداد و کاراکترهای خاص باشد.'
        )


class AgeValidator:
    """
    Validates user age based on date of birth.
    """
    
    def __init__(self, min_age=13, max_age=120):
        """
        Initialize validator with age limits.
        
        Args:
            min_age: Minimum allowed age (default: 13)
            max_age: Maximum allowed age (default: 120)
        """
        self.min_age = min_age
        self.max_age = max_age
    
    def __call__(self, value):
        """Validate age."""
        if not value:
            return
        
        today = date.today()
        age = (today - value).days // 365
        
        if age < self.min_age:
            raise ValidationError(
                _('سن شما باید حداقل %(min_age)s سال باشد.') % {'min_age': self.min_age},
                code='too_young'
            )
        
        if age > self.max_age:
            raise ValidationError(
                _('تاریخ تولد نامعتبر است.'),
                code='too_old'
            )
        
        # Check if date is not in future
        if value > today:
            raise ValidationError(
                _('تاریخ تولد نمی‌تواند در آینده باشد.'),
                code='future_date'
            )


class ProfilePictureValidator:
    """
    Validates profile picture file.
    """
    
    def __init__(self, max_size_mb=5, allowed_formats=None):
        """
        Initialize validator with file constraints.
        
        Args:
            max_size_mb: Maximum file size in MB (default: 5)
            allowed_formats: List of allowed MIME types
        """
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.allowed_formats = allowed_formats or [
            'image/jpeg', 'image/jpg', 'image/png', 'image/webp'
        ]
    
    def __call__(self, value):
        """Validate profile picture."""
        if not value:
            return
        
        # Check file size
        if value.size > self.max_size_bytes:
            raise ValidationError(
                _('حجم تصویر نباید بیشتر از %(size)s مگابایت باشد.') % {
                    'size': self.max_size_bytes // (1024 * 1024)
                },
                code='file_too_large'
            )
        
        # Check file format
        if value.content_type not in self.allowed_formats:
            raise ValidationError(
                _('فرمت تصویر باید JPEG، PNG یا WebP باشد.'),
                code='invalid_format'
            )
        
        # Check image dimensions (optional)
        try:
            from PIL import Image
            img = Image.open(value)
            width, height = img.size
            
            if width < 100 or height < 100:
                raise ValidationError(
                    _('تصویر باید حداقل 100×100 پیکسل باشد.'),
                    code='image_too_small'
                )
            
            if width > 4000 or height > 4000:
                raise ValidationError(
                    _('تصویر نباید بیشتر از 4000×4000 پیکسل باشد.'),
                    code='image_too_large'
                )
        except ImportError:
            # PIL not installed, skip dimension check
            pass
        except Exception as e:
            raise ValidationError(
                _('فایل تصویر معتبر نیست.'),
                code='invalid_image'
            )


class EmailDomainValidator(BaseEmailValidator):
    """
    Validates email domain against whitelist/blacklist.
    """
    
    def __init__(self, whitelist=None, blacklist=None, *args, **kwargs):
        """
        Initialize with domain lists.
        
        Args:
            whitelist: List of allowed domains (if set, only these are allowed)
            blacklist: List of blocked domains
        """
        super().__init__(*args, **kwargs)
        self.whitelist = whitelist or []
        self.blacklist = blacklist or [
            'tempmail.com', 'guerrillamail.com', 'mailinator.com',
            '10minutemail.com', 'throwaway.email'
        ]
    
    def __call__(self, value):
        """Validate email domain."""
        # First run standard email validation
        super().__call__(value)
        
        # Extract domain
        domain = value.split('@')[1].lower()
        
        # Check whitelist
        if self.whitelist and domain not in self.whitelist:
            raise ValidationError(
                _('این دامنه ایمیل مجاز نیست.'),
                code='domain_not_allowed'
            )
        
        # Check blacklist
        if domain in self.blacklist:
            raise ValidationError(
                _('استفاده از ایمیل‌های موقت مجاز نیست.'),
                code='temporary_email'
            )


class UsernameValidator:
    """
    Validates username format.
    """
    
    def __init__(self, min_length=3, max_length=30):
        """
        Initialize validator with length constraints.
        
        Args:
            min_length: Minimum username length (default: 3)
            max_length: Maximum username length (default: 30)
        """
        self.min_length = min_length
        self.max_length = max_length
    
    def __call__(self, value):
        """Validate username."""
        if not value:
            return
        
        # Check length
        if len(value) < self.min_length:
            raise ValidationError(
                _('نام کاربری باید حداقل %(min)s کاراکتر باشد.') % {'min': self.min_length},
                code='username_too_short'
            )
        
        if len(value) > self.max_length:
            raise ValidationError(
                _('نام کاربری نباید بیشتر از %(max)s کاراکتر باشد.') % {'max': self.max_length},
                code='username_too_long'
            )
        
        # Check format (alphanumeric, underscore, dash)
        if not re.match(r'^[a-zA-Z0-9_-]+$', value):
            raise ValidationError(
                _('نام کاربری فقط می‌تواند شامل حروف، اعداد، خط تیره و زیرخط باشد.'),
                code='invalid_username'
            )
        
        # Check if starts with letter
        if not value[0].isalpha():
            raise ValidationError(
                _('نام کاربری باید با حرف شروع شود.'),
                code='username_invalid_start'
            )


class SubscriptionDateValidator:
    """
    Validates subscription date ranges.
    """
    
    def __call__(self, start_date, end_date):
        """
        Validate subscription dates.
        
        Args:
            start_date: Subscription start date
            end_date: Subscription end date
        """
        if not start_date or not end_date:
            return
        
        if end_date <= start_date:
            raise ValidationError(
                _('تاریخ پایان اشتراک باید بعد از تاریخ شروع باشد.'),
                code='invalid_date_range'
            )
        
        # Check if duration is reasonable (not more than 10 years)
        max_duration = timedelta(days=365 * 10)
        if (end_date - start_date) > max_duration:
            raise ValidationError(
                _('مدت اشتراک نمی‌تواند بیشتر از 10 سال باشد.'),
                code='duration_too_long'
            )


def validate_phone_number(value):
    """
    Validate Iranian phone number format.
    
    Args:
        value: Phone number string
    
    Raises:
        ValidationError: If phone number is invalid
    """
    if not value:
        return
    
    # Remove spaces and dashes
    cleaned = re.sub(r'[\s-]', '', value)
    
    # Check Iranian mobile format (09xxxxxxxxx or +989xxxxxxxxx)
    if not re.match(r'^(\+98|0)?9\d{9}$', cleaned):
        raise ValidationError(
            _('شماره موبایل معتبر نیست. فرمت صحیح: 09123456789'),
            code='invalid_phone'
        )


def validate_no_profanity(value):
    """
    Check for profanity in text fields.
    
    Args:
        value: Text to validate
    
    Raises:
        ValidationError: If profanity detected
    """
    if not value:
        return
    
    # (این لیست باید کامل‌تر شود)
    profanity_list = ['badword1', 'badword2'] # Example placeholders
    
    value_lower = value.lower()
    for word in profanity_list:
        if word in value_lower:
            raise ValidationError(
                _('متن شامل کلمات نامناسب است.'),
                code='profanity_detected'
            )