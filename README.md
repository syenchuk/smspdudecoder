# SMS-PDU Decoder

[![PyPI version](https://badge.fury.io/py/smspdudecoder.svg)](https://badge.fury.io/py/smspdudecoder)

This library will help you to decode raw SMS data you can get from a GSM modem (generally by using AT commands).

It has some encoding primitives as well, but full encoding support is not available, since this is not the main purpose of this library.

It is recommended to read the [GSM 03.40](https://en.wikipedia.org/wiki/GSM_03.40) specification to better understand the components this library works wtih.

## How to install

This library has been successfully tested and works with Python versions ranging from 3.7 up to 3.10.

```
pip install smspdudecoder
```

## How to use

Please take a look at the source code, which comes with documentation and examples.

For instance, if you need to work with text, you can use GSM and UCS2 encodings just like that:

```python
>>> from smspdudecoder.codecs import GSM, UCS2
>>> GSM.decode('C8F71D14969741F977FD07')
'How are you?'
>>> UCS2.decode('004C006F00720065006D00200049007000730075006D')
'Lorem Ipsum'
```

If you need to decode a full incoming SMS PDU, you can use the `SMSDeliver` class:

```python
from io import StringIO
from smspdudecoder.fields import SMSDeliver

deliver_pdu = StringIO('07916407058099F9040B916407950303F100008921222140140004D4E2940A')
sms_data = SMSDeliver.decode(deliver_pdu)
```

If you execute this example, the `sms_data` variable will contain a dictionary with the following data:

```python
{
  'smsc': {
    'length': 7,
    'toa': {
      'ton': 'international', 'npi': 'isdn'
    },
    'number': '46705008999'
  },
  'header': {
    'rp': False,
    'udhi': False,
    'sri': False,
    'lp': False,
    'mms': False,
    'mti': 'deliver'
  },
  'sender': {
    'length': 11,
    'toa': { 'ton': 'international', 'npi': 'isdn' },
    'number': '46705930301'
  },
  'pid': 0,
  'dcs': { 'encoding': 'gsm' },
  'scts': datetime.datetime(2098, 12, 22, 12, 4, 41, tzinfo = datetime.timezone.utc),
  'user_data': { 'header': None, 'data': 'TEST' }
}
```

If you don't need all the technical details, you can use the `easy` module to get a simple representation of the SMS:

```python
from smspdudecoder.easy import read_incoming_sms

sms = read_incoming_sms('07916407058099F9040B916407950303F100008921222140140004D4E2940A')
```

Which will produce the following result:

```python
{
  'sender': '+46705930301',
  'content': 'TEST',
  'date': datetime.datetime(2098, 12, 22, 12, 4, 41, tzinfo=datetime.timezone.utc),
  'partial': False
}
```

## How to test and contribute

First, clone this repository:

```sh
git clone git@github.com:qotto/smspdudecoder.git
# or use HTTPS if you are unauthenticated:
# git clone https://github.com/qotto/smspdudecoder.git
cd smspdudecoder
```

### Using Docker

The easiest way to test this library against all supported Python versions is to use Docker.

```sh
make docker-test
```

Behinds the scenes, this will build a Docker image with all supported Python versions and run the tests with [tox](https://tox.wiki/).

### Using your existing Python installation

If you want to simply run the test suite, make sure that you have dependencies installed with:

```sh
pip install -r requirements.txt
```

And use the following command:

```sh
make test
```
