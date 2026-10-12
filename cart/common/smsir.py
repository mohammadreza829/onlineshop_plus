from sms_ir import SmsIr
from django.conf import settings

def send_sms_ir(message, reciept):
    print(reciept)
    sms_ir = SmsIr(settings.SMS_IR_API_KEY, settings.SMS_IR_LINE_NUMBER)
    sms_ir.send_sms(reciept, message)