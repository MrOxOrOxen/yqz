import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from email.header import Header
from email.header import Header
from memory_store import *
from constants import *
from logger import add_log
import aiohttp

EMAIL_CONFIG = {
    "smtp_server": "smtp.exmail.qq.com",
    "smtp_port": 465,
    "sender_email": "admin@yqzhaya.com",
    "sender_password": email_password,
    "receiver_email": "admin@yqzhaya.com",
    "enabled": True
}

async def send_email_text(live_start_time, live_end_time, duration_str, title):
    if not EMAIL_CONFIG.get("enabled", False):
        return
    
    try:
        msg = MIMEText(
            f"""状态：PREPARING
标题：{title}
直播时间：{live_start_time} - {live_end_time}
直播时长：{duration_str}
            """,
            'plain', 'utf-8'
        )

        msg['From'] = Header(f"推送姬 <{EMAIL_CONFIG['sender_email']}>", 'utf-8')
        msg['To'] = Header(EMAIL_CONFIG['receiver_email'], 'utf-8')
        msg['Subject'] = Header("【推送姬】云崎早_haya直播时间数据存档", 'utf-8')

        with smtplib.SMTP_SSL(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port']) as server:
            server.login(EMAIL_CONFIG['sender_email'], EMAIL_CONFIG['sender_password'])
            server.sendmail(
                EMAIL_CONFIG['sender_email'],
                EMAIL_CONFIG['receiver_email'],
                msg.as_string()
            )
        
        add_log("[推送姬] 下播邮件发送成功")
        
    except Exception as e:
        add_log(f"[推送姬] 下播邮件发送失败: {str(e)}")

async def send_email(live_start_time, live_end_time, duration_str, title, cover=""):
    if not EMAIL_CONFIG.get("enabled", False):
        return
    try:
        msg = MIMEMultipart("related")
        msg["From"] = Header(f"推送姬 <{EMAIL_CONFIG['sender_email']}>", "utf-8")
        msg["To"] = Header(EMAIL_CONFIG["receiver_email"], "utf-8")
        msg["Subject"] = Header("【推送姬】云崎早_haya直播时间数据存档", "utf-8")

        if cover != "":
            cover_html = """
            <br>
            <img src="cid:live_cover"
                 style="max-width:600px; width:100%; height:auto;">
            <br>
            """
        else:
            cover_html = ""

        html = f"""
        <html>
        <body>
            <p>
                状态：PREPARING<br>
                标题：{title}<br>
                直播时间：{live_start_time} - {live_end_time}<br>
                直播时长：{duration_str}<br>
            </p>

            {cover_html}

        </body>
        </html>
        """
        msg.attach(MIMEText(html, "html", "utf-8"))

        if cover:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(cover) as response:
                        if response.status == 200:
                            image_data = await response.read()
                            image = MIMEImage(image_data)
                            image.add_header("Content-ID", "<live_cover>")
                            image.add_header("Content-Disposition", "inline", filename="live_cover.jpg")
                            msg.attach(image)
                            add_log("[推送姬] 直播封面已加入邮件")
                        else:
                            add_log(f"[推送姬] 下载直播封面失败: HTTP {response.status}")

            except Exception as e:
                add_log(
                    f"[推送姬] 下载直播封面失败: {e}"
                )

        with smtplib.SMTP_SSL(EMAIL_CONFIG["smtp_server"], EMAIL_CONFIG["smtp_port"]) as server:
            server.login(EMAIL_CONFIG["sender_email"], EMAIL_CONFIG["sender_password"])
            server.sendmail(EMAIL_CONFIG["sender_email"], EMAIL_CONFIG["receiver_email"], msg.as_string())
        add_log("[推送姬] 下播邮件发送成功")

    except Exception as e:
        add_log(f"[推送姬] 下播邮件发送失败: {str(e)}")