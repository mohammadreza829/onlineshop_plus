from django import forms

from account.otp import normalize_phone

from .models import Address
from .validation import normalize_postal_code


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
        return normalize_phone(self.cleaned_data.get("receiver_phone"))

    def clean_postal_code(self):
        return normalize_postal_code(self.cleaned_data.get("postal_code"))
