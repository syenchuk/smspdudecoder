# Copyright (c) Qotto, 2018-2023
# Open-source software, see LICENSE file for details

"""
Various elements used in TP-DU, according to GSM 03.40.

All these elements are encoded in strings and decoded in native Python objects.
"""

from datetime import datetime
from datetime import timedelta
from datetime import timezone
from io import StringIO
from typing import Dict

import pytz

from bitstring import BitStream

__all__ = [
    'Date',
    'Number',
    'TypeOfAddress',
]


def swap_nibbles(data: str) -> str:
    """
    Swaps nibbles (semi-octets) in the PDU hex string and returns the result.

    Example:

    >>> swap_nibbles('0123')
    '1032'
    """
    res = ''
    for k in range(0, len(data), 2):
        res += data[k+1] + data[k]
    return res


class Date:
    """
    Date representation.
    """
    @classmethod
    def decode(cls, data: str) -> datetime:
        """
        Returns a datetime object, read from the PDU.
        Keep in mind that the resulting datetime is timezone-aware and always converted to UTC.

        Examples:

        >>> Date.decode('70402132522400')
        datetime.datetime(2007, 4, 12, 23, 25, 42, tzinfo=datetime.timezone.utc)

        The same date, with a different offset, results in a different UTC date:

        >>> Date.decode('70402132522423')
        datetime.datetime(2007, 4, 12, 15, 25, 42, tzinfo=datetime.timezone.utc)

        And negative offsets are supported too:

        >>> Date.decode('3130523210658A')
        datetime.datetime(2013, 3, 26, 6, 1, 56, tzinfo=datetime.timezone.utc)

        >>> (Date.decode('11101131522400') - Date.decode('11101131521440')).total_seconds()
        3601.0
        """
        io_data = StringIO(swap_nibbles(data))
        year = 2000 + int(io_data.read(2))
        month = int(io_data.read(2))
        day = int(io_data.read(2))
        hour = int(io_data.read(2))
        minute = int(io_data.read(2))
        second = int(io_data.read(2))
        tz_data = int(io_data.read(2), 16)
        tz_multiplier = -1 if tz_data & 0x80 else +1
        tz_offset_abs = int(f'{tz_data&0x7f:x}')
        tz_delta = timedelta(minutes=15*tz_multiplier*tz_offset_abs)
        local_date = datetime(year, month, day, hour, minute, second, tzinfo=timezone(tz_delta))
        return local_date.astimezone(timezone.utc)

    @classmethod
    def encode(cls, date: datetime) -> str:
        """
        Returns a PDU hex string representating the date.

        If the date is not timezone-aware, UTC timezone is used by default.

        >>> Date.encode(datetime(2018, 1, 1))
        '81101000000000'

        >>> Date.encode(pytz.timezone('Europe/Paris').localize(datetime(2020, 1, 29, 13, 25, 41)))
        '02109231521440'

        >>> Date.encode(pytz.timezone('US/Pacific').localize(datetime(2013, 3, 25, 23, 1, 56)))
        '3130523210658a'
        """
        result = date.strftime('%y%m%d%H%M%S')
        tz_delta = date.utcoffset()
        if tz_delta is None:
            tz_delta_seconds = 0.0
        else:
            tz_delta_seconds = tz_delta.total_seconds()
        tz_delta_gsm = int(str(int(abs(tz_delta_seconds) / 60 / 15)), 16)
        if tz_delta_seconds < 0:
            tz_delta_gsm |= 0x80
        result += f'{tz_delta_gsm:02x}'
        return swap_nibbles(result)


class Number:
    """
    Telephone number representation.
    """
    @classmethod
    def decode(cls, data: str) -> str:
        """
        Decodes a telephone number from PDU hex string.

        Example:

        >>> Number.decode('5155214365F7')
        '15551234567'
        >>> Number.decode('1032547698')
        '0123456789'
        """
        data = swap_nibbles(data)
        if data[-1:].lower() == 'f':
            data = data[:-1]
        return data

    @classmethod
    def encode(cls, data: str) -> str:
        """
        Encodes a telephone number as a PDU hex string.

        Example:

        >>> Number.encode('15551234567')
        '5155214365F7'
        >>> Number.encode('0123456789')
        '1032547698'
        """
        if len(data) % 2:
            data += 'F'
        return swap_nibbles(data)


class TypeOfAddress:
    """
    Type Of Address representation.
    """
    TON = {
        0b000: 'unknown',
        0b001: 'international',
        0b010: 'national',
        0b011: 'specific',
        0b100: 'subscriber',
        0b101: 'alphanumeric',
        0b110: 'abbreviated',
        0b111: 'extended',
    }
    TON_INV = dict([(v[1], v[0]) for v in TON.items()])

    NPI = {
        0b0000: 'unknown',
        0b0001: 'isdn',
        0b0011: 'data',
        0b0100: 'telex',
        0b0101: 'specific1',
        0b0110: 'specific2',
        0b1000: 'national',
        0b1001: 'private',
        0b1010: 'ermes',
        0b1111: 'extended',
    }
    NPI_INV = dict([(v[1], v[0]) for v in NPI.items()])

    @classmethod
    def decode(cls, data: str) -> Dict[str, str]:
        """
        Decodes the Type Of Address octet. Returns a dictionary.

        Example:

        >>> TypeOfAddress.decode('91')
        {'ton': 'international', 'npi': 'isdn'}
        """
        io_data = BitStream(hex=data)
        first_bit = io_data.read('bool')
        if not first_bit:
            raise ValueError("Invalid first bit of the Type Of Address octet")
        # Type Of Number
        ton = cls.TON.get(io_data.read('bits:3').uint)
        if ton is None:
            assert False, "Type-Of-Number bits should be exaustive"
            raise ValueError("Invalid Type Of Number bits")
        # Numbering Plan Identification
        npi =  cls.NPI.get(io_data.read('bits:4').uint)
        if npi is None:
            raise ValueError("Invalid Numbering Plan Identification bits")
        return {
            'ton': ton,
            'npi': npi,
        }

    @classmethod
    def encode(cls, data: Dict[str, str]) -> str:
        """
        Encodes the Type Of Address dictionary, and returns a PDU hex string.

        Example:

        >>> TypeOfAddress.encode({'ton': 'international', 'npi': 'isdn'})
        '91'
        """
        ton = cls.TON_INV.get(data.get('ton'))
        npi = cls.NPI_INV.get(data.get('npi'))
        if ton is None:
            raise ValueError("Invalid Type Of Address")
        if npi is None:
            raise ValueError("Invalid Numbering Plan Identification")
        return f'{0x80 | (ton << 4) | npi:02x}'
