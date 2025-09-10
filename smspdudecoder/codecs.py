# Copyright (c) Qotto, 2018-2023
# Open-source software, see LICENSE file for details

"""
Implementation of different codecs used in SMS PDUs, according to the GSM 03.38 specification.
"""

from binascii import hexlify
from binascii import unhexlify
from bitstring import BitStream

__all__ = ['GSM', 'UCS2']


class GSM:
    """
    GSM 7-bit SMS codec
    """
    ALPHABET = (
        '@£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞ\x1BÆæßÉ !"#¤%&\'()*+,-./0123456789:;<=>?'
        '¡ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ§¿abcdefghijklmnopqrstuvwxyzäöñüà'
    )

    ALPHABET_EXT = {
        10: '\f',
        20: '^',
        40: '{',
        41: '}',
        47: '\\',
        60: '[',
        61: '~',
        62: ']',
        64: '|',
        101: '€',
    }
    ALPHABET_EXT_INV = dict([(v[1], v[0]) for v in ALPHABET_EXT.items()])

    CHAR_EXT = 0x1B

    @classmethod
    def decode(cls, data: str, strip_padding: bool = False) -> str:
        r"""
        Returns decoded message from PDU string.

        When strip_padding argument equals True, checks if the last symbol is a padding character (CR) and removes it.

        For more details, read the ETSI GSM 03.38 specification (version 5.6.1) that can be found at:
        https://www.etsi.org/deliver/etsi_i_ets/300900_300999/300900/03_60/ets_300900e03p.pdf

        Some examples:

        >>> GSM.decode('C8F71D14969741F977FD07')
        'How are you?'

        >>> GSM.decode('32D0A60C8287E5A0F63B3D07')
        '2 € par mois'

        Decodes without stripping the padding character:

        >>> GSM.decode('AA58ACA6AA8D1A')
        '*115*5#\r'

        Decodes the same PDU, and strips the padding character:

        >>> GSM.decode('AA58ACA6AA8D1A', True)
        '*115*5#'
        """
        reversed_bits = BitStream(hex=cls.reversed_octets(data)).bin
        septets = [int(reversed_bits[k:k+7], 2) for k in range(len(reversed_bits)-7, -1, -7)]
        res = ''
        is_extended = False
        for char_index in septets:
            if char_index == cls.CHAR_EXT:
                is_extended = True
                continue
            if is_extended:
                is_extended = False
                res += cls.ALPHABET_EXT.get(char_index, ' ')
            else:
                res += cls.ALPHABET[char_index]

        if strip_padding and len(septets) % 8 == 0 and res.endswith('\r'):
            return res[:-1]
        return res

    @classmethod
    def encode(cls, data: str, with_padding: bool = False) -> str:
        """
        Returns an encoded PDU string.

        If the total number of characters to be sent equals to 8n + 7 where n ≥ 0, then there are 7 spare bits at the
        end of the last octet. To avoid the situation where the receiving entity confuses these 7 zero bits as the @
        character, a padding character (CR) can replace these empty bits.

        If CR is intended to be the last character and the message (including the wanted <CR>) ends on an
        octet boundary, then another CR can be added together with a padding bit 0.

        For more details, read the ETSI GSM 03.38 specification (version 5.6.1) that can be found at:
        https://www.etsi.org/deliver/etsi_i_ets/300900_300999/300900/03_60/ets_300900e03p.pdf

        Set with_paddign to True in order to enable the use of this padding character.

        Example:

        >>> GSM.encode("hellohello")
        'E8329BFD4697D9EC37'

        You can also use characters from the extended table:

        >>> GSM.encode("2 € par mois")
        '32D0A60C8287E5A0F63B3D07'

        Encodes 7 characters without padding:

        >>> GSM.encode('1234567')
        '31D98C56B3DD00'

        Encodes 7 characters and uses padding:

        >>> GSM.encode('1234567', with_padding=True)
        '31D98C56B3DD1A'
        """
        chars = list()
        for char in data:
            try:
                # tries the standard alphabet
                char_index = cls.ALPHABET.index(char)
            except ValueError:
                chars.append(cls.CHAR_EXT)
                # tries the extended alphabet
                try:
                    char_index = cls.ALPHABET_EXT_INV[char]
                except KeyError:
                    char_index = cls.CHAR_EXT
            if char_index == cls.CHAR_EXT:
                raise ValueError(f"Char \"{char}\" can not be encoded with the GSM 7-bit codec")
            chars.append(char_index)

        if with_padding:
            if len(chars) % 8 == 0 and data[-1:] == '\r':
                chars.append(cls.ALPHABET.index('\r'))
            if len(chars) % 8 == 7:
                chars.append(cls.ALPHABET.index('\r'))

        res = '0' * (len(chars) % 8) + ''.join([f'{char:07b}' for char in chars][::-1])
        return cls.reversed_octets(BitStream(bin=res).hex.upper())

    @classmethod
    def reversed_octets(cls, data: str) -> str:
        """
        Reverses octets in a PDU string.

        >>> GSM.reversed_octets("00F1F2F3")
        'F3F2F100'
        """
        return ''.join([data[k:k+2] for k in range(0, len(data), 2)][::-1])


class UCS2:
    """
    UCS-2 SMS codec.

    This codec actually uses the UTF-16 extension, and doesn't warn if
    some characters are out of the pure UCS-2 charset range.
    """
    @classmethod
    def encode(cls, data: str) -> str:
        """
        Returns an encoded PDU string.

        Example:

        >>> UCS2.encode("Je pompe donc je suis.")
        '004A006500200070006F006D0070006500200064006F006E00630020006A006500200073007500690073002E'
        """
        return hexlify(data.encode('utf-16be')).decode('ascii').upper()

    @classmethod
    def decode(cls, data: str) -> str:
        """
        Returns decoded message from PDU string.

        Example:

        >>> UCS2.decode('004C006F00720065006D00200049007000730075006D')
        'Lorem Ipsum'
        """
        return unhexlify(data).decode('utf-16be')
