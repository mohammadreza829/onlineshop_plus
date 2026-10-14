from django import forms

from .models import Address


class AddressForm(forms.ModelForm):
    class Meta:
        model = Address
        fields = [
            "title",
            "receiver_name",
            "receiver_phone",
            "province",
            "city",
            "full_address",
            "postal_code",
            "is_default",
        ]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control", "placeholder": "مثلاً: خانه"}),
            "receiver_name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "نام و خانوادگی"}
            ),
            "receiver_phone": forms.TextInput(attrs={"class": "form-control", "placeholder": "09170000000"}),
            "province": forms.Select(attrs={"class": "form-select"}),
            "city": forms.TextInput(attrs={"class": "form-control"}),
            "full_address": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "postal_code": forms.TextInput(attrs={"class": "form-control"}),
            "is_default": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def clean_receiver_phone(self):
        phone = self.cleaned_data.get("receiver_phone")
        if not phone.isdigit() or len(phone) != 11 or not phone.startswith("09"):
            raise forms.ValidationError("شماره همراه نامعتبر است.")
        return phone

    def clean_postal_code(self):
        postal_code = self.cleaned_data.get("postal_code")
        if not postal_code.isdigit() or len(postal_code) != 10:
            raise forms.ValidationError("کد پستی باید ۱۰ رقم باشد.")
        return postal_code
