import unittest
from io import StringIO

from smspdudecoder.fields import SMSDeliver


class SMSDeliverTestCase(unittest.TestCase):
    def test_decode_truncated_ucs2(self):
        pdu = '0891683110304105F1240D91683167414052F700081270115183942344597D70E6597D70E651CF80A551CF80A55C'
        pdu_stream = StringIO(pdu)
        decoded_data = SMSDeliver.decode(pdu_stream)
        self.assertEqual(decoded_data['user_data']['data'], '好烦好烦减肥减肥尀')
