# Copyright (c) Qotto, 2018-2023
# Open-source software, see LICENSE file for details

"""
TP-DU fields according to GSM 03.40.

Unlike elements, fields represent independent datagram chunks, and are decoded from a file-like object.

Fields may contain one or multiple elements.
"""

from .codecs import GSM
from .codecs import UCS2
from .elements import Date
from .elements import Number
from .elements import TypeOfAddress
from binascii import unhexlify
from bitstring import BitStream
from io import StringIO

from typing import Any, Dict


class Address:
    """
    GSM address representation. Typically a telephone number, or an alphanumeric identifier.
    """
    @classmethod
    def decode(cls, pdu_data: StringIO) -> Dict[str, Any]:
        """
        Decodes an address from PDU.

        Example:

        >>> Address.decode(StringIO('0B915155214365F7'))
        {'length': 11, 'toa': {'ton': 'international', 'npi': 'isdn'}, 'number': '15551234567'}

        An address can also be alphanumeric:

        >>> Address.decode(StringIO('0BD0CDE6DB5DCE03'))
        {'length': 11, 'toa': {'ton': 'alphanumeric', 'npi': 'unknown'}, 'number': 'MMoney'}

        Or contain extended characters

        >>> Address.decode(StringIO('14D0C4F23C7D760390EF7619'))
        {'length': 20, 'toa': {'ton': 'alphanumeric', 'npi': 'unknown'}, 'number': 'Design@Home'}
        """
        length = int(pdu_data.read(2), 16)
        toa = TypeOfAddress.decode(pdu_data.read(2))
        encoded_number = pdu_data.read(length + length % 2)
        if toa['ton'] == 'alphanumeric':
            number = GSM.decode(encoded_number)
        else:
            number = Number.decode(encoded_number)
        return {
            'length': length,
            'toa': toa,
            'number': number,
        }


class SMSC:
    """
    SMS-C datagram.
    """
    @classmethod
    def decode(cls, pdu_data: StringIO):
        """
        Decodes the SMS-C information PDU.

        Example:

        >>> SMSC.decode(StringIO('07912299976758F2'))
        {'length': 7, 'toa': {'ton': 'international', 'npi': 'isdn'}, 'number': '22997976852'}
        """
        length = int(pdu_data.read(2), 16)
        if not length:
            return {
                'length': 0,
                'toa': None,
                'number': None,
            }

        toa = TypeOfAddress.decode(pdu_data.read(2))
        encoded_number = pdu_data.read(2*(length-1))
        if toa['ton'] == 'alphanumeric':
            number = GSM.decode(encoded_number)
        else:
            number = Number.decode(encoded_number)
        return {
            'length': length,
            'toa': toa,
            'number': number,
        }


class PDUHeader:
    """
    Describes the incomming TPDU header of SM-TP
    """
    MTI = {
        0b00: 'deliver',
        0b01: 'submit-report',
        0b10: 'status-report',
    }
    MTI_INV = dict([(v[1], v[0]) for v in MTI.items()])

    @classmethod
    def decode(cls, pdu_data: StringIO) -> Dict[str, Any]:
        """
        Decodes an incomming PDU header.

        >>> PDUHeader.decode(StringIO('44'))
        {'rp': False, 'udhi': True, 'sri': False, 'lp': False, 'mms': False, 'mti': 'deliver'}
        """
        result = dict()
        io_data = BitStream(hex=pdu_data.read(2))
        # Reply Path
        result['rp'] = io_data.read('bool')
        # User Data PDUHeader Indicator
        result['udhi'] = io_data.read('bool')
        # Status Report Indication
        result['sri'] = io_data.read('bool'); io_data.pos += 1 # skips a bit
        # Loop Prevention
        result['lp'] = io_data.read('bool')
        # More Messages to Send
        result['mms'] = not io_data.read('bool')
        # Message Type Indicator
        result['mti'] = cls.MTI.get(io_data.read('bits:2').uint)
        if result['mti'] is None:
            raise ValueError("Invalid Message Type Indicator")
        return result


class OutgoingPDUHeader:
    """
    Describes the outgoing TPDU header of SM-TP
    """
    MTI = {
        0b00: 'deliver',
        0b01: 'submit',
        0b10: 'status',
    }
    MTI_INV = dict([(v[1], v[0]) for v in MTI.items()])

    @classmethod
    def decode(cls, pdu_data: StringIO) -> Dict[str, Any]:
        """
        Decodes an outgoing PDU header.

        >>> OutgoingPDUHeader.decode(StringIO('11'))
        {'rp': False, 'udhi': False, 'srr': False, 'vpf': 2, 'rd': False, 'mti': 'submit'}
        """
        result = dict()
        io_data = BitStream(hex=pdu_data.read(2))
        # Reply Path
        result['rp'] = io_data.read('bool')
        # User Data Header Indicator
        result['udhi'] = io_data.read('bool')
        # Status Report Request
        result['srr'] = io_data.read('bool')
        # Validity Period Format
        result['vpf'] = io_data.read('bits:2').uint
        # Reject Duplicates
        result['rd'] = io_data.read('bool')
        # Message Type Indicator
        result['mti'] = cls.MTI.get(io_data.read('bits:2').uint)
        if result['mti'] is None:
            raise ValueError("Invalid Message Type Indicator")
        return result


class DCS:
    """
    Data Coding Scheme (simplified, only the encoding is read)
    """
    @classmethod
    def decode(cls, pdu_data: StringIO) -> Dict[str, str]:
        dcs = int(pdu_data.read(2), 16)
        coding = (dcs & 0b1100) >> 2
        if coding == 1:
            return {'encoding': 'binary'}
        elif coding == 2:
            return {'encoding': 'ucs2'}
        else:
            return {'encoding': 'gsm'}


class InformationElement:
    @staticmethod
    def concatenated_sms(data: str, length_bits: int = 8) -> Dict[str, Any]:
        io_data = BitStream(hex=data)
        return {
            'reference': io_data.read(f'uintbe:{length_bits}'),
            'parts_count': io_data.read('uintbe:8'),
            'part_number': io_data.read('uintbe:8'),
        }

    IEI = {
        0x00: lambda v: InformationElement.concatenated_sms(v, 8),
        0x08: lambda v: InformationElement.concatenated_sms(v, 16),
    }

    @classmethod
    def decode(cls, pdu_data: StringIO) -> Dict[str, Any]:
        iei = int(pdu_data.read(2), 16)
        length = int(pdu_data.read(2), 16)
        data = pdu_data.read(2*length)
        processing_func = cls.IEI.get(iei)
        processed_data: Any = data
        if processing_func is not None:
            processed_data = processing_func(data)
        return {
            'iei': iei,
            'length': length,
            'data': processed_data,
        }


class UserDataHeader:
    @classmethod
    def decode(cls, pdu_data: StringIO) -> Dict[str, Any]:
        length = int(pdu_data.read(2), 16)
        final_position = pdu_data.tell() + 2 * length
        elements = list()
        while pdu_data.tell() < final_position:
            elements.append(InformationElement.decode(pdu_data))
        return {
            'length': length,
            'elements': elements,
        }


class UserData:
    @classmethod
    def decode(cls, pdu_data: StringIO, ctx: dict = None):
        length = int(pdu_data.read(2), 16)
        pdu_start = pdu_data.tell()
        header, header_length = None, 0
        if ctx['header']['udhi']:
            header = UserDataHeader.decode(pdu_data)
            header_length = header['length'] + 1
        data: Any = None
        if ctx['dcs']['encoding'] == 'binary':
            data = unhexlify(pdu_data.read(2*(length-header_length)))
        elif ctx['dcs']['encoding'] == 'gsm':
            pdu_data.seek(pdu_start)
            header_length_bits = header_length * 8
            header_length_septets = int(header_length_bits / 7) + (1 if header_length_bits % 7 else 0)
            data_length_bits = length * 7
            data_length_bytes = int(data_length_bits / 8) + (1 if data_length_bits % 8 else 0)
            data = GSM.decode(pdu_data.read(2*data_length_bytes))[header_length_septets:length]
        elif ctx['dcs']['encoding'] == 'ucs2':
            data = UCS2.decode(pdu_data.read(2*(length-header_length)))
        else:
            raise AssertionError("Non-recognized encoding")
        return {
            'header': header,
            'data': data,
        }


class SMSDeliver:
    """
    SMS-DELIVER TP-DU.
    """
    @classmethod
    def decode(cls, pdu_data: StringIO):
        """
        Decodes an SMS-DELIVER TP-DU.
        """
        result = dict()
        result['smsc'] = SMSC.decode(pdu_data)
        result['header'] = PDUHeader.decode(pdu_data)
        result['sender'] = Address.decode(pdu_data)
        result['pid'] = int(pdu_data.read(2), 16)
        result['dcs'] = DCS.decode(pdu_data)
        result['scts'] = Date.decode(pdu_data.read(2*7))
        result['user_data'] = UserData.decode(pdu_data, result)
        return result


class SMSSubmit:
    """
    SMS-SUBMIT TP-DU.
    """
    @classmethod
    def decode(cls, pdu_data: StringIO):
        """
        Decodes an SMS-SUBMIT TP-DU.
        """
        result = dict()
        result['smsc'] = SMSC.decode(pdu_data)
        result['header'] = OutgoingPDUHeader.decode(pdu_data)
        result['message-ref'] = int(pdu_data.read(2), 16)
        result['recipient'] = Address.decode(pdu_data)
        result['pid'] = int(pdu_data.read(2), 16)
        result['dcs'] = DCS.decode(pdu_data)
        if result['header']['vpf'] == 0:
            pass
        elif result['header']['vpf'] == 2:
            result['vp'] = int(pdu_data.read(2), 16)
            if result['vp'] <= 143:
                result['validity-minutes'] = result['vp'] * 5
            elif result['vp'] <= 167:
                result['validity-hours'] = 12 + (result['vp'] - 143) // 2
            elif result['vp'] <= 196:
                result['validity-days'] = result['vp'] - 166
            else:
                result['validity-weeks'] = result['vp'] - 192
        elif result['header']['vpf'] == 3:
            result['vp'] = Date.decode(pdu_data.read(2*7))
        else:
            pdu_data.read(2*7) # skips the enhanced format

        result['user_data'] = UserData.decode(pdu_data, result)
        return result
