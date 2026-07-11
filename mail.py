import smtplib
from email.mime.text import MIMEText
from email.header import Header
from memory_store import *
from constants import *
from logger import add_log

EMAIL_CONFIG = {
    "smtp_server": "smtp.exmail.qq.com",
    "smtp_port": 465,
    "sender_email": "admin@yqzhaya.com",
    "sender_password": email_password,
    "receiver_email": "admin@yqzhaya.com",
    "enabled": True
}

async def send_email(live_start_time, live_end_time, duration_str, title):
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