import time
from http import client

import requests

from utils import ErrorException

session = requests.Session()


def get_req(url, headers = None, params=None, tries=1, timeout=1,type = None):
    tries_count = 0
    success = False
    while success is False:
        try:
            res = session.get(url=url, headers=headers, params=params)
            if res.ok or res.status_code in [502, 503]:
                success = True
                if type == 'json':
                    return res.json()
                elif type == 'text':
                    return res.text
                elif type == 'content':
                    return res.content
                return res
            if not res.ok:
                if res.status_code == 403:
                    raise ErrorException('Error status code %s with url : %s' % (res.status_code, url))
        except (client.IncompleteRead, requests.ConnectionError) as e:
            tries_count += 1
            if tries_count >= tries:
                raise ErrorException(e)
            time.sleep(timeout)
    return

def post_req(url, headers, data = None, tries=1, timeout=3,type= None):
    tries_count = 0
    success = False
    while success is False:
        try:
            res = session.post(url=url, headers=headers, data=data)
            if res.ok or res.status_code in [502, 503]:
                success = True
                if type == 'json':
                    return res.json()
                elif type == 'text':
                    return res.text
                elif type == 'content':
                    return res.content
                return res
            if not res.ok:
                if res.status_code == 403:
                    raise ErrorException('Error status code %s with url : %s' % (res.status_code, url))
        except (client.IncompleteRead, requests.ConnectionError) as e:
            tries_count += 1
            if tries_count >= tries:
                raise ErrorException(e)
            time.sleep(timeout)
    return