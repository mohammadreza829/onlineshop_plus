from django.conf import settings
from sms_ir import SmsIr


def send_sms_ir(message, receptor):
    sms_ir = SmsIr(settings.SMS_IR_API_KEY, settings.SMS_IR_LINE_NUMBER)
    sms_ir.send_sms(receptor, message)
