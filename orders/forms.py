from django import forms


class OrderCreateForm(forms.Form):

    first_name = forms.CharField(
        max_length=100,
        label="نام"
    )


    last_name = forms.CharField(
        max_length=100,
        label="نام خانوادگی"
    )


    phone = forms.CharField(
        max_length=20,
        label="شماره تماس"
    )


    postal_code = forms.CharField(
        max_length=20,
        label="کد پستی"
    )


    address = forms.CharField(
        widget=forms.Textarea,
        label="آدرس"
    )
    
    
class PhoneVerificationForm(forms.Form):
    phone = forms.CharField(max_length=11,label='شماره تلفن')
    
   