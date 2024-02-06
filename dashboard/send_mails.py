import smtplib, ssl
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr
from django.template.loader import get_template
from django.conf import settings


def send(subject, html_content, recipient_list, reply_to, sender_name):
    recipients = ", ".join(recipient_list)
    port = 465  # For SSL
    password = settings.EMAIL_HOST_PASSWORD #sender email password
    sender_email = "noreply@qorums.com"
    message = MIMEMultipart('alternative')
    message['Subject'] = subject
    message['To'] = recipients
    message['From'] = formataddr(("{} - Qorums Notification".format(sender_name), sender_email))
    message['Reply-To'] = reply_to
    message.add_header("X-Priority","1 (High)")
    message.attach(html_content)
    server = smtplib.SMTP_SSL("smtp.gmail.com", port)
    server.login(sender_email, password)
    server.sendmail(sender_email, recipient_list, message.as_string())
    server.quit()


def send_interview_mails(htm_list, hm, candidate):
    subject = 'New Candidate Submitted to {}!'.format(openposition_obj.position_title)
    try:
        d = {
            "position_title": openposition_obj.position_title,
            "user_name": sm.user.get_full_name(),
            "candidate_name": candidate_obj.name,
        }
        htmly_b = get_template('candidate_added_sm.html')
        text_content = ""
        html_content = htmly_b.render(d)
        profile = Profile.objects.get(user=request.user)
        reply_to = profile.email
        sender_name = profile.user.get_full_name()
    except:
        reply_to = 'noreply@qorums.com'
        sender_name = 'No Reply'
    try:
        tasks.send.delay(subject, html_content, 'html', [htm_data['email']], reply_to, sender_name)
    except Exception as e:
        pass