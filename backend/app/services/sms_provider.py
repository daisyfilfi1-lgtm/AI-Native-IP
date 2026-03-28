"""短信发送：mock / 腾讯云真实短信。"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)


def send_login_verification_code(phone: str, code: str) -> None:
    """
    发送登录验证码。

    - SMS_PROVIDER=mock：仅打日志（开发/联调）。
    - SMS_PROVIDER=tencent：腾讯云短信（需配置 SMS_TENCENT_* 与密钥）。
    """
    provider = os.environ.get("SMS_PROVIDER", "mock").strip().lower()
    if provider == "mock":
        logger.warning(
            "SMS mock: phone=%s code=%s (set SMS_PROVIDER=tencent for real SMS)",
            phone,
            code,
        )
        return

    if provider in ("tencent", "tencentcloud"):
        from app.services.sms_tencent import send_tencent_login_code

        send_tencent_login_code(phone, code)
        return

    raise NotImplementedError(
        f"SMS_PROVIDER={provider} is not implemented; use mock or tencent"
    )
