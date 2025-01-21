# Copyright (c) Qotto, 2018-2023
# Open-source software, see LICENSE file for details

from io import StringIO
from typing import Any, Dict

from .fields import SMSDeliver, SMSSubmit

__all__ = [
    'read_incoming_sms',
    'read_outgoing_sms',
]


def read_incoming_sms(data: str) -> Dict[str, Any]:
    sms = SMSDeliver.decode(StringIO(data))
    sender = sms['sender']['number']
    if sms['sender']['toa']['ton'] == 'international':
        sender = '+' + sender
    date = sms['scts']
    content = sms['user_data']['data']
    header = sms['user_data'].get('header')
    partial: Any = False
    if header:
        for element in header.get('elements', list()):
            if element['iei'] in [0x00, 0x08]:
                el_data = element['data']
                partial = {
                    'reference': f"{el_data['reference']}-{el_data['parts_count']}",
                    'parts_count': el_data['parts_count'],
                    'part_number': el_data['part_number'],
                }
    return {
        'date': date,
        'sender': sender,
        'content': content,
        'partial': partial,
    }


def read_outgoing_sms(data: str) -> Dict[str, Any]:
    sms = SMSSubmit.decode(StringIO(data))
    recipient = sms['recipient']['number']
    if sms['recipient']['toa']['ton'] == 'international':
        recipient = '+' + recipient
    content = sms['user_data']['data']
    return {
        'recipient': recipient,
        'content': content,
    }
