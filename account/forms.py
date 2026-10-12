# from django import forms
# from django.contrib.auth.forms import UserCreationForm, UserChangeForm
# from .models import ShopUser


# class ShopUserCreationsForm(UserCreationForm):
#     class Meta(UserCreationForm.Meta):
#         model = ShopUser
#         fields = ('phone', 'last_name', 'first_name', 'is_active', 'is_staff', 'address')

#     def clean_phone(self):
#         phone = self.cleaned_data.get('phone')

#         if self.instance.pk:
#             if ShopUser.objects.filter(phone=phone).exclude(pk=self.instance.pk).exists():
#                 raise forms.ValidationError("Phone already exists")

#         else:
#             if ShopUser.objects.filter(phone=phone).exists():
#                 raise forms.ValidationError("Phone already exists")

#         if not phone.isdigit():
#             raise forms.ValidationError("Invalid phone number")
#         if not phone.startswith('09'):
#             raise forms.ValidationError("phone must be start with 09 digits.")
#         if len(phone) != 11:
#             raise forms.ValidationError("phone must be 11 digits")
#         return phone


# class ShopUserChangeForm(UserChangeForm):
#     class Meta(UserCreationForm.Meta):
#         model = ShopUser
#         fields = ('phone', 'last_name', 'first_name', 'is_active', 'is_staff', 'address')

#     def clean_phone(self):
#         phone = self.cleaned_data.get('phone')

#         if self.instance.pk:
#             if ShopUser.objects.filter(phone=phone).exclude(pk=self.instance.pk).exists():
#                 raise forms.ValidationError("Phone already exists")

#         else:
#             if ShopUser.objects.filter(phone=phone).exists():
#                 raise forms.ValidationError("Phone already exists")

#         if not phone.isdigit():
#             raise forms.ValidationError("Invalid phone number")
#         if not phone.startswith('09'):
#             raise forms.ValidationError("phone must be start with 09 digits.")
#         if len(phone) != 11:
#             raise forms.ValidationError("phone must be 11 digits")
#         return phone


from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import ShopUser


class ShopUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = ShopUser
        fields = ('phone', 'first_name', 'last_name', 'address')

    def clean_phone(self):
        phone = self.cleaned_data.get('phone')

        if not phone.isdigit():
            raise forms.ValidationError("شماره تلفن باید فقط شامل ارقام باشد.")
        if not phone.startswith('09'):
            raise forms.ValidationError("شماره تلفن باید با 09 شروع شود.")
        if len(phone) != 11:
            raise forms.ValidationError("شماره تلفن باید دقیقاً 11 رقم باشد.")
            
        if ShopUser.objects.filter(phone=phone).exists():
            raise forms.ValidationError("این شماره تلفن قبلاً ثبت شده است.")

        return phone


class ShopUserChangeForm(UserChangeForm):
    class Meta:
        model = ShopUser
        fields = ('phone', 'first_name', 'last_name', 'is_active', 'is_staff', 'address')

    def clean_phone(self):
        phone = self.cleaned_data.get('phone')

        if not phone.isdigit():
            raise forms.ValidationError("شماره تلفن باید فقط شامل ارقام باشد.")
        if not phone.startswith('09'):
            raise forms.ValidationError("شماره تلفن باید با 09 شروع شود.")
        if len(phone) != 11:
            raise forms.ValidationError("شماره تلفن باید دقیقاً 11 رقم باشد.")

        if self.instance.pk:
            if ShopUser.objects.filter(phone=phone).exclude(pk=self.instance.pk).exists():
                raise forms.ValidationError("این شماره تلفن توسط کاربر دیگری استفاده شده است.")

        return phone


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = ShopUser
        fields = ('first_name', 'last_name', 'address')
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'نام'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'نام خانوادگی'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'آدرس کامل'}),
        }