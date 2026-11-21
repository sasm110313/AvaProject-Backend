import json
import logging
import urllib.parse
import urllib.request
from typing import Any

from django.conf import settings

from core.models import SmsLog

logger = logging.getLogger("core")


class SmsService:
    @classmethod
    def _normalize_phone(cls, phone: str) -> str:
        phone = phone.strip()
        if phone.startswith("+98"):
            phone = "0" + phone[3:]
        elif phone.startswith("98"):
            phone = "0" + phone[2:]
        elif not phone.startswith("0") and len(phone) == 10:
            phone = "0" + phone
        return phone

    @classmethod
    def send_sms(
        cls,
        phone: str,
        message: str,
        template: str = "",
        token: str = "",
    ) -> SmsLog:
        phone = cls._normalize_phone(phone)
        provider = getattr(settings, "SMS_PROVIDER", "smsir").lower()
        kavenegar_key = getattr(settings, "KAVENEGAR_API_KEY", "")
        farazsms_key = getattr(settings, "FARAZSMS_API_KEY", "")
        smsir_key = getattr(settings, "SMSIR_API_KEY", "")

        # Default fallback to simulation if API keys are not provided
        if provider == "kavenegar" and not kavenegar_key:
            provider = "console"
        elif provider == "farazsms" and not farazsms_key:
            provider = "console"
        elif provider == "smsir" and not smsir_key:
            provider = "console"

        log = SmsLog(
            phone=phone,
            message=message,
            template=template,
            provider=provider,
            status="simulated" if provider == "console" else "failed",
        )

        if provider == "console":
            logger.info("📱 [SMS SIMULATION] To: %s | Template: %s | Message: %s", phone, template, message)
            log.status = "simulated"
            log.provider_msg_id = "SIM-" + phone[-4:]
            log.save()
            return log

        # --------------------------------------------------------------------
        # KAVENEGAR PROVIDER
        # --------------------------------------------------------------------
        if provider == "kavenegar":
            try:
                if template:
                    # Kavenegar Verify Lookup API (Fast pattern matching)
                    url = f"https://api.kavenegar.com/v1/{kavenegar_key}/verify/lookup.json"
                    params = {
                        "receptor": phone,
                        "token": token or message,
                        "template": template,
                    }
                else:
                    sender = getattr(settings, "KAVENEGAR_SENDER", "")
                    url = f"https://api.kavenegar.com/v1/{kavenegar_key}/sms/send.json"
                    params = {
                        "receptor": phone,
                        "message": message,
                    }
                    if sender:
                        params["sender"] = sender

                data = urllib.parse.urlencode(params).encode("utf-8")
                req = urllib.request.Request(url, data=data, headers={"User-Agent": "AvaStore/1.0"})
                with urllib.request.urlopen(req, timeout=5) as response:
                    res_body = json.loads(response.read().decode("utf-8"))
                    if res_body.get("return", {}).get("status") == 200:
                        log.status = "sent"
                        entries = res_body.get("entries", [])
                        if entries and isinstance(entries, list):
                            log.provider_msg_id = str(entries[0].get("messageid", ""))
                    else:
                        log.status = "failed"
                        log.error_message = str(res_body)
            except Exception as exc:
                logger.error("Kavenegar SMS exception for %s: %s", phone, exc)
                log.status = "failed"
                log.error_message = str(exc)

            log.save()
            return log

        # --------------------------------------------------------------------
        # FARAZSMS / IPPANEL PROVIDER
        # --------------------------------------------------------------------
        if provider == "farazsms":
            try:
                url = "https://ippanel.com/services.jspd"
                sender = getattr(settings, "FARAZSMS_SENDER", "3000505")
                payload = {
                    "uname": getattr(settings, "FARAZSMS_USERNAME", ""),
                    "pass": farazsms_key,
                    "from": sender,
                    "to": json.dumps([phone]),
                    "msg": message,
                    "op": "send",
                }
                data = urllib.parse.urlencode(payload).encode("utf-8")
                req = urllib.request.Request(url, data=data, headers={"User-Agent": "AvaStore/1.0"})
                with urllib.request.urlopen(req, timeout=5) as response:
                    res_raw = response.read().decode("utf-8")
                    if res_raw.startswith("["):
                        log.status = "sent"
                        log.provider_msg_id = res_raw.strip("[]\"' ")
                    else:
                        log.status = "failed"
                        log.error_message = res_raw
            except Exception as exc:
                logger.error("FarazSMS exception for %s: %s", phone, exc)
                log.status = "failed"
                log.error_message = str(exc)

            log.save()
            return log

        # --------------------------------------------------------------------
        # SMS.IR PROVIDER (v1 Verify & Bulk)
        # --------------------------------------------------------------------
        if provider == "smsir":
            smsir_template_id = getattr(settings, "SMSIR_TEMPLATE_ID", 100000)
            try:
                # If token or template is provided, use Ultra Fast Verify endpoint
                if token or template:
                    tid = int(template) if str(template).isdigit() else int(smsir_template_id or 100000)
                    param_name = getattr(settings, "SMSIR_TEMPLATE_PARAM_NAME", "Code")
                    verify_payload = {
                        "mobile": phone,
                        "templateId": tid,
                        "parameters": [
                            {"name": param_name, "value": str(token or message)}
                        ],
                    }
                    data_bytes = json.dumps(verify_payload).encode("utf-8")
                    req = urllib.request.Request(
                        "https://api.sms.ir/v1/send/verify",
                        data=data_bytes,
                        headers={
                            "Content-Type": "application/json",
                            "Accept": "application/json",
                            "x-api-key": smsir_key,
                            "User-Agent": "AvaStore/1.0",
                        },
                        method="POST",
                    )
                    with urllib.request.urlopen(req, timeout=8) as response:
                        res_body = json.loads(response.read().decode("utf-8"))
                        status_code = res_body.get("status")
                        if status_code == 1:
                            log.status = "sent"
                            data_obj = res_body.get("data")
                            if isinstance(data_obj, dict):
                                log.provider_msg_id = str(data_obj.get("messageId", ""))
                        else:
                            log.status = "failed"
                            log.error_message = f"SMS.ir error {status_code}: {res_body.get('message', '')}"
                            logger.error("SMS.ir verify send error for %s: %s", phone, res_body)
                else:
                    # Line bulk send
                    line_num = getattr(settings, "SMSIR_LINE_NUMBER", 300034720521)
                    bulk_payload = {
                        "lineNumber": int(line_num),
                        "messageText": message,
                        "mobiles": [phone],
                    }
                    data_bytes = json.dumps(bulk_payload).encode("utf-8")
                    req = urllib.request.Request(
                        "https://api.sms.ir/v1/send/bulk",
                        data=data_bytes,
                        headers={
                            "Content-Type": "application/json",
                            "Accept": "application/json",
                            "x-api-key": smsir_key,
                            "User-Agent": "AvaStore/1.0",
                        },
                        method="POST",
                    )
                    with urllib.request.urlopen(req, timeout=8) as response:
                        res_body = json.loads(response.read().decode("utf-8"))
                        if res_body.get("status") == 1:
                            log.status = "sent"
                            data_obj = res_body.get("data")
                            if isinstance(data_obj, dict):
                                log.provider_msg_id = str(data_obj.get("packId", ""))
                        else:
                            log.status = "failed"
                            log.error_message = f"SMS.ir error {res_body.get('status')}: {res_body.get('message', '')}"
            except urllib.error.HTTPError as exc:
                err_text = exc.read().decode("utf-8", errors="ignore")
                logger.error("SMS.ir HTTPError for %s (%s): %s", phone, exc.code, err_text)
                log.status = "failed"
                log.error_message = f"HTTP {exc.code}: {err_text}"
            except Exception as exc:
                logger.error("SMS.ir exception for %s: %s", phone, exc)
                log.status = "failed"
                log.error_message = str(exc)

            log.save()
            return log

        log.save()
        return log

    @classmethod
    def send_otp(cls, phone: str, code: str) -> SmsLog:
        provider = getattr(settings, "SMS_PROVIDER", "smsir").lower()
        if provider == "smsir":
            template = str(getattr(settings, "SMSIR_TEMPLATE_ID", 100000))
        else:
            template = getattr(settings, "KAVENEGAR_OTP_TEMPLATE", "verify")
        message = f"کد تایید فروشگاه آوای انعکاس: {code}\nاعتبار: ۱۰ دقیقه"
        return cls.send_sms(phone=phone, message=message, template=template, token=code)

    @classmethod
    def send_order_placed(cls, phone: str, order_code: str, total: int) -> SmsLog:
        message = f"مشتری گرامی، سفارش شما با کد {order_code} به مبلغ {total:,} تومان با موفقیت ثبت شد و در صف بررسی قرار گرفت.\nفروشگاه آوای انعکاس"
        return cls.send_sms(phone=phone, message=message, template="order_placed", token=order_code)

    @classmethod
    def send_order_status(cls, phone: str, order_code: str, status_title: str, tracking_code: str = "") -> SmsLog:
        track_part = f"\nکد رهگیری پستی: {tracking_code}" if tracking_code else ""
        message = f"مشتری گرامی، وضعیت سفارش {order_code} به «{status_title}» تغییر یافت.{track_part}\nفروشگاه آوای انعکاس"
        return cls.send_sms(phone=phone, message=message, template="order_status", token=order_code)

    @classmethod
    def send_payment_receipt(cls, phone: str, order_code: str, amount: int, ref_id: str) -> SmsLog:
        message = f"پرداخت سفارش {order_code} به مبلغ {amount:,} تومان تأیید شد.\nشماره پیگیری بانک: {ref_id}\nبا تشکر از خرید شما، آوای انعکاس"
        return cls.send_sms(phone=phone, message=message, template="payment_success", token=ref_id)
