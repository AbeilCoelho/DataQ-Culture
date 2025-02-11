import csv

from chardet.universaldetector import UniversalDetector
from flask import session


def detect_encoding(file_path):
    """Detects the encoding of a given file using chardet."""
    try:
        detector = UniversalDetector()
        with open(file_path, "rb") as file:
            for line in file:
                detector.feed(line)
                if detector.done:
                    break

        detector.close()
        encoding = detector.result.get("encoding")
        session["encoding"] = encoding
        print("Encoding detected:", encoding)
        return encoding
    except Exception as e:
        print(f"Error detecting encoding: {e}")
        return None


def detect_delimiter(file_path, encoding):
    """Detects the delimiter of a CSV-like file using csv.Sniffer."""
    delimiters = ["\x00", "\x01", "^", ":", ",", "\t", ";", "|", "~", " "]
    try:
        with open(file_path, encoding=encoding) as file:
            first_line = next(file)
            dialect = csv.Sniffer().sniff(first_line, delimiters)
            delimiter = dialect.delimiter
            session["delimitador"] = delimiter
            print("Delimiter detected:", delimiter)
            return delimiter
    except Exception as e:
        print(f"Error detecting delimiter: {e}")
        return None
