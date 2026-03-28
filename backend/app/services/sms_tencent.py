"""腾讯云短信 SendSms（登录验证码）。"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)


def _e164_cn(phone: str) -> str:
    """腾讯云要求国际格式，大陆手机为 +8613xxxxxxxxx"""
    p = phone.strip().replace(" ", "")
    if p.startswith("+"):
        return p
    if len(p) == 11 and p.isdigit():
        return f"+86{p}"
    return p


def send_tencent_login_code(phone: str, code: str) -> None:
    """
    调用腾讯云短信 SendSms 发送验证码。

    控制台需创建「验证码」类模板，通常仅一个参数（验证码），对应 TemplateParamSet=[code]。
    环境变量见 .env.example（SMS_TENCENT_* / TENCENTCLOUD_*）。
    """
    try:
        from tencentcloud.common import credential
        from tencentcloud.common.exception.tencent_cloud_sdk_exception import (
            TencentCloudSDKException,
        )
        from tencentcloud.sms.v20210111 import models, sms_client
    except ImportError as e:
        raise RuntimeError(
            "请安装腾讯云 SDK: pip install tencentcloud-sdk-python"
        ) from e

    secret_id = (
        os.environ.get("TENCENTCLOUD_SECRET_ID")
        or os.environ.get("SMS_TENCENT_SECRET_ID")
        or ""
    ).strip()
    secret_key = (
        os.environ.get("TENCENTCLOUD_SECRET_KEY")
        or os.environ.get("SMS_TENCENT_SECRET_KEY")
        or ""
    ).strip()
    region = os.environ.get("SMS_TENCENT_REGION", "ap-guangzhou").strip()
    sdk_app_id = os.environ.get("SMS_TENCENT_SMS_SDK_APP_ID", "").strip()
    sign_name = os.environ.get("SMS_TENCENT_SIGN_NAME", "").strip()
    template_id = os.environ.get("SMS_TENCENT_TEMPLATE_ID", "").strip()

    missing = [
        n
        for n, v in [
            ("TENCENTCLOUD_SECRET_ID (或 SMS_TENCENT_SECRET_ID)", secret_id),
            ("TENCENTCLOUD_SECRET_KEY (或 SMS_TENCENT_SECRET_KEY)", secret_key),
            ("SMS_TENCENT_SMS_SDK_APP_ID", sdk_app_id),
            ("SMS_TENCENT_SIGN_NAME", sign_name),
            ("SMS_TENCENT_TEMPLATE_ID", template_id),
        ]
        if not v
    ]
    if missing:
        raise RuntimeError("腾讯云短信配置不完整，缺少: " + ", ".join(missing))

    cred = credential.Credential(secret_id, secret_key)
    client = sms_client.SmsClient(cred, region)

    req = models.SendSmsRequest()
    req.SmsSdkAppId = sdk_app_id
    req.SignName = sign_name
    req.TemplateId = template_id
    req.TemplateParamSet = [code]
    req.PhoneNumberSet = [_e164_cn(phone)]

    try:
        resp = client.SendSms(req)
    except TencentCloudSDKException as e:
        logger.exception("Tencent SendSms SDK error: %s", e)
        raise RuntimeError(f"腾讯云短信接口错误: {e}") from e

    statuses = getattr(resp, "SendStatusSet", None) or []
    if not statuses:
        raise RuntimeError("腾讯云短信返回异常：无 SendStatusSet")

    for st in statuses:
        code = getattr(st, "Code", "") or ""
        msg = getattr(st, "Message", "") or ""
        if code != "Ok":
            logger.error("Tencent SMS send failed: Code=%s Message=%s", code, msg)
            raise RuntimeError(f"短信发送失败: {msg or code}")

    logger.info("Tencent SMS sent ok for phone ending %s", phone[-4:])
