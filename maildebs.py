#!/usr/bin/env python3

import io
import os
import re
import sys
import subprocess
import smtplib
import configparser
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.text import MIMEText
from setup import __project__, __version__


HERE = os.path.dirname(__file__)


def create_message(sender, recipients, subject, body, attachments):
    root_container = MIMEMultipart(_subtype='related')
    root_container['From'] = sender
    root_container['To'] = recipients
    root_container['Subject'] = subject
    root_container.preamble = 'This is a multi-part message in MIME format.'
    root_container.attach(MIMEText(body, _subtype='plain'))
    for attachment in attachments:
        with io.open(attachment, 'rb') as f:
            attachment_container = MIMEApplication(f.read())
        filename = os.path.split(attachment)[1]
        attachment_container.add_header('Content-Id', '<%s>' % filename)
        attachment_container.add_header('Content-Disposition', 'attachment', filename=filename)
        root_container.attach(attachment_container)
    return root_container


def send_email(message, host='localhost', port=25):
    server = smtplib.SMTP(host, port)
    try:
        server.ehlo()
        server.sendmail(
            message['From'],
            message['To'],
            message.as_string())
    finally:
        server.quit()


def main():
    config = configparser.ConfigParser()
    config.read(os.path.expanduser('~/.maildebs.conf'))
    project = __project__
    version = __version__
    recipient = config['message']['recipient']
    sender = config['message'].get('sender', '%s <%s>' % (
        subprocess.check_output(['git', 'config', '--global', 'user.name']).decode('utf-8').strip(),
        subprocess.check_output(['git', 'config', '--global', 'user.email']).decode('utf-8').strip(),
        ))
    sender_match = re.match(r'(?P<name>[^<]+) <(?P<email>[^>]+)>', sender)
    recipient_match = re.match(r'(?P<name>[^<]+) <(?P<email>[^>]+)>', recipient)
    subst = {
        'project': project,
        'version': version,
        'recipient_name': recipient_match.group('name').split(),
        'recipient_email': recipient_match.group('email'),
        'recipient_forename': recipient_match.group('name').split()[0],
        'recipient_surname': recipient_match.group('name').split()[1],
        'sender_name': sender_match.group('name').split(),
        'sender_email': sender_match.group('email'),
        'sender_forename': sender_match.group('name').split()[0],
        'sender_surname': sender_match.group('name').split()[1],
        }
    subject = config['message']['subject'].format(**subst)
    body = config['message']['body'].format(**subst)
    attachments = sys.argv[1:]
    send_email(
        create_message(sender, recipient, subject, body, attachments),
        config['smtp'].get('host', 'localhost'),
        config['smtp'].get('port', 25))


if __name__ == '__main__':
    main()
