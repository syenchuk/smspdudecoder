# Release notes

## 2.2.0 (2025-09-10)

- Added robust handling for truncated UCS-2 PDUs.
- The library now logs a warning and returns an ellipsis at the end of the decoded string to indicate that the data was incomplete.
- The decoded result now contains a `warning` field when a truncation occurs.

## 2.1.1 (2025-01-21)

- Added tests for Python 3.7 up to 3.12
- Fixed bug with lowercase hex strings

## 2.1.0 (2023-04-12)

- Added basic support for SMS-SUBMIT messages

## 2.0.0 (2022-02-07)

- Package smspdu renamed to `smspdudecoder` for consistency.
- Added tests for Python 3.7, 3.8, 3.9 and 3.10.

## 1.2.1  (2019-07-22)

- Added support for Python 3.6 and 3.7.
