import argparse
import io
import itertools
import json
import os
import sys
import time
import requests
import re
from colorama import Style, init, Fore, Back
from download_http import Downloader
from download_hls import Download_m3u8
from progress_bar import ProgressBar
from http import client
from urllib.parse import urljoin,urlparse,unquote
from base64 import b64decode
import datetime

ACCENT_CHARS = dict(zip('ÂÃÄÀÁÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖŐØŒÙÚÛÜŰÝÞßàáâãäåæçèéêëìíîïðñòóôõöőøœùúûüűýþÿ',
                        itertools.chain('AAAAAA', ['AE'], 'CEEEEIIIIDNOOOOOOO', ['OE'], 'UUUUUY', ['TH', 'ss'],
                                        'aaaaaa', ['ae'], 'ceeeeiiiionooooooo', ['oe'], 'uuuuuy', ['th'], 'y')))


def duration_to_length(duration):
    if duration:
        length = datetime.timedelta(seconds=duration)
        if length:
            return length
    return None


def removeCharacter_filename(s, restricted=False, is_id=False):
    def replace_insane(char):
        if restricted and char in ACCENT_CHARS:
            return ACCENT_CHARS[char]
        if char == '?' or ord(char) < 32 or ord(char) == 127:
            return ''
        elif char == '"':
            return '' if restricted else '\''
        elif char == ':':
            return '_-' if restricted else ' -'
        elif char in '\\/|*<>':
            return '_'
        if restricted and (char in '!&\'()[]{}$;`^,#' or char.isspace()):
            return '_'
        if restricted and ord(char) > 127:
            return '_'
        return char

    s = re.sub(r'[0-9]+(?::[0-9]+)+', lambda m: m.group(0).replace(':', '_'), s)
    result = ''.join(map(replace_insane, s))
    if not is_id:
        while '__' in result:
            result = result.replace('__', '_')
        result = result.strip('_')
        if restricted and result.startswith('-_'):
            result = result[2:]
        if result.startswith('-'):
            result = '_' + result[len('-'):]
        result = result.lstrip('.')
        if not result:
            result = '_'
    return result


another_user = 'Mozilla/5.0 (compatible; MSIE 10.0; Windows Phone 8.0; Trident/6.0; IEMobile/10.0; ARM; Touch; NOKIA; Lumia 920)'
HEADERS = {
    # 'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/48.0.2564.97 Safari/537.36',
    # 'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    # 'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.7',
    # 'Accept-Encoding': 'gzip, deflate',
    # 'Accept-Language': 'en-us,en;q=0.5',
    # 'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/48.0.2564.97 Safari/537.36',
    # 'sec-fetch-mode': 'cors',
    # 'sec-fetch-site': 'same-origin',
    # 'pragma': 'no-cache',
    # 'content-type': 'application/json; charset=utf-8',
    'user-agent':'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/48.0.2564.97 Safari/537.36',

}
session = requests.Session()
CURRENT_DIR = os.getcwd()


def parse_json(json_string, transform_source=None, fatal=True):
    if transform_source:
        json_string = transform_source(json_string)
    try:
        return json.loads(json_string)
    except ValueError as ve:
        errmsg = '%s: Failed to parse JSON '
        raise ErrorException(errmsg)


def search_regex(pattern, string, flags=0, group=None):
    mobj = re.search(pattern, string, flags)

    if mobj:
        if group is None:
            # return the first matching group
            return next(g for g in mobj.groups() if g is not None)
        else:
            return mobj.group(group)


def findAll_regex(pattern, string, index=0, text_find=None):
    mobj = re.findall(pattern, string)

    if mobj:
        try:
            if text_find:
                for i in mobj:
                    if text_find in i:
                        return i
            return mobj[index]
        except IndexError as e:
            return None
    else:
        return None


KNOWN_EXTENSIONS = (
    'mp4', 'm4a', 'm4p', 'm4b', 'm4r', 'm4v', 'aac',
    'flv', 'f4v', 'f4a', 'f4b',
    'webm', 'ogg', 'ogv', 'oga', 'ogx', 'spx', 'opus',
    'mkv', 'mka', 'mk3d',
    'avi', 'divx',
    'mov',
    'asf', 'wmv', 'wma',
    '3gp', '3g2',
    'mp3',
    'flac',
    'ape',
    'wav',
    'f4f', 'f4m', 'm3u8', 'smil')
def dict_get(d, key_or_keys, default=None, skip_false_values=True):
    if isinstance(key_or_keys, (list, tuple)):
        for key in key_or_keys:
            if key not in d or d[key] is None or skip_false_values and not d[key]:
                continue
            return d[key]
        return default
    return d.get(key_or_keys, default)

def try_get(src, getter, expected_type=None):
    if not isinstance(getter, (list, tuple)):
        getter = [getter]
    for get in getter:
        try:
            v = get(src)
        except (AttributeError, KeyError, TypeError, IndexError):
            pass
        else:
            if expected_type is None or isinstance(v, expected_type):
                return v


def mimetype2ext(mt):
    if mt is None:
        return None

    ext = {
        'audio/mp4': 'm4a',
        'audio/mpeg': 'mp3',
    }.get(mt)
    if ext is not None:
        return ext

    _, _, res = mt.rpartition('/')
    res = res.split(';')[0].strip().lower()

    return {
        '3gpp': '3gp',
        'smptett+xml': 'tt',
        'ttaf+xml': 'dfxp',
        'ttml+xml': 'ttml',
        'x-flv': 'flv',
        'x-mp4-fragmented': 'mp4',
        'x-ms-sami': 'sami',
        'x-ms-wmv': 'wmv',
        'mpegurl': 'm3u8',
        'x-mpegurl': 'm3u8',
        'vnd.apple.mpegurl': 'm3u8',
        'dash+xml': 'mpd',
        'f4m+xml': 'f4m',
        'hds+xml': 'f4m',
        'vnd.ms-sstr+xml': 'ism',
        'quicktime': 'mov',
        'mp2t': 'ts',
    }.get(res, res)


def is_url(url):
    if not url or not isinstance(url, str):
        return None
    url = url.strip()
    return url if re.match(r'^(?:[a-zA-Z][\da-zA-Z.+-]*:)?//', url) else None


def is_int(v, scale=1, default=None, get_attr=None, invscale=1):
    if get_attr:
        if v is not None:
            v = getattr(v, get_attr, None)
    if v == '':
        v = None
    if v is None:
        return default
    try:
        return int(v) * invscale // scale
    except (ValueError, TypeError):
        return default


def is_float(v, scale=1, invscale=1, default=None):
    if v is None:
        return default
    try:
        return float(v) * invscale / scale
    except (ValueError, TypeError):
        return default

def js_to_json(code):
    COMMENT_RE = r'/\*(?:(?!\*/).)*?\*/|//[^\n]*'
    SKIP_RE = r'\s*(?:{comment})?\s*'.format(comment=COMMENT_RE)
    INTEGER_TABLE = (
        (r'(?s)^(0[xX][0-9a-fA-F]+){skip}:?$'.format(skip=SKIP_RE), 16),
        (r'(?s)^(0+[0-7]+){skip}:?$'.format(skip=SKIP_RE), 8),
    )

    def fix_kv(m):
        v = m.group(0)
        if v in ('true', 'false', 'null'):
            return v
        elif v.startswith('/*') or v.startswith('//') or v == ',':
            return ""

        if v[0] in ("'", '"'):
            v = re.sub(r'(?s)\\.|"', lambda m: {
                '"': '\\"',
                "\\'": "'",
                '\\\n': '',
                '\\x': '\\u00',
            }.get(m.group(0), m.group(0)), v[1:-1])

        for regex, base in INTEGER_TABLE:
            im = re.match(regex, v)
            if im:
                i = int(im.group(1), base)
                return '"%d":' % i if v.endswith(':') else '%d' % i

        return '"%s"' % v

    return re.sub(r'''(?sx)
        "(?:[^"\\]*(?:\\\\|\\['"nurtbfx/\n]))*[^"\\]*"|
        '(?:[^'\\]*(?:\\\\|\\['"nurtbfx/\n]))*[^'\\]*'|
        {comment}|,(?={skip}[\]}}])|
        (?:(?<![0-9])[eE]|[a-df-zA-DF-Z_])[.a-zA-Z_0-9]*|
        \b(?:0[xX][0-9a-fA-F]+|0+[0-7]+)(?:{skip}:)?|
        [0-9]+(?={skip}:)
        '''.format(comment=COMMENT_RE, skip=SKIP_RE), fix_kv, code)
class ErrorException(Exception):
    """Raise when have a bug"""
