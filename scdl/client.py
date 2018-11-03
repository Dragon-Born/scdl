import urllib.request as Request
import urllib
import demjson
import xmltodict
import dateutil.parser as dateutil
import json
import requests
from urllib.parse import quote
import datetime
import re
import os
import time
import urllib3
urllib3.disable_warnings()


def _req(url, proxies, auth=None):
    if auth:
        headers = {"Authorization": "OAuth {}".format(auth)}
    else:
        headers = {}
    request = requests.get(url, headers=headers, proxies=proxies)
    return request


def _fix_name(i):
    i = i[0]
    if '-' in i['title']:
        d = i['title'].split('-')
        i['artist'] = d[0]
        i['title'] = d[1]
        artist = i['artist']
    else:
        artist = i['publisher_metadata']['artist'] if 'artist' in i['publisher_metadata'] else i['user']['username']

    i['title'] = fix(i['title'])
    return artist, i['title'],


def _download_file(url, file_name=None, auth=None, path=None):
    local_filename = url.split('/')[-1] if not file_name else file_name
    if os.name == 'nt':
        v = "\\"
    else:
        v = "/"
    if path:
        if path.endswith("\\") or path.endswith("/"):
            path += local_filename
        else:
            path += v + local_filename
    else:
        path = os.getcwd() + v + local_filename
    # NOTE the stream=True parameter
    if auth:
        headers = {"Authorization": "OAuth {}".format(auth)}
    else:
        headers = {}
    r = requests.get(url, stream=True, headers=headers,
                     verify=False)
    with open(path, 'wb') as f:
        for chunk in r.iter_content(chunk_size=1024):
            if chunk:  # filter out keep-alive new chunks
                f.write(chunk)
    if r.status_code != 200:
        raise requests.HTTPError(r.status_code)
    return path


def fix(title):
    title = re.sub(r' [(\[].+ Remix[)\]]', '', title)
    title = re.sub(r' [(\[]By .+[)\]]', '', title)
    title = re.sub(r' [(\[].+ Track[)\]]', '', title)
    return title


class Client:
    url = {
        "search": "https://api-v2.soundcloud.com/search/{}?q={}&sc_a_id=b7859ae8-b56d-482e-8e6f-86bdb3a1ce18&variant_ids=&facet=genre&user_id=986313-378597-775923-395166&client_id={}&limit={}&offset=0&linked_partitioning=1&app_version=1518689071&app_locale=en",
        "download": "https://api.soundcloud.com/i1/tracks/{}/streams?client_id={}",
        "plus": "https://api-v2.soundcloud.com/search/{}?q={}&sc_a_id=b7859ae8-b56d-482e-8e6f-86bdb3a1ce18&variant_ids=&filter.content_tier=SUB_HIGH_TIER&facet=genre&user_id=986313-378597-775923-395166&client_id={}&limit={}&offset=0&linked_partitioning=1&app_version=1518689071&app_locale=en",
        "last_new": "https://api-v2.soundcloud.com/charts?kind=trending&high_tier_only=true&client_id=g7pmPAwAmWJ8oGICV7nnp8VpdF2GdVca&limit=20&offset=0",
        "track_info": "https://api-v2.soundcloud.com/tracks?ids={}&client_id={}"
    }

    def __init__(self, **kwargs):
        """Create a client instance with the provided options. Options should
        be passed in as kwargs.
        """
        self.db = []
        self.client_id = kwargs.get('client_id')
        if 'client_id' not in kwargs:
            raise TypeError("At least a client_id must be provided.")

        self.auth = kwargs.get('auth', None)
        self.proxies = kwargs.get('proxies', {})

    def last_new(self):
        url = self.url['last_new']
        request = _req(url, self.proxies)
        if request.status_code != 200:
            return self.db
        request = request.json()
        self.reformat(request, collection='new')
        return self.db

    def download(self, track_id, path=None):
        get_links_url = self.url['download'].format(track_id, self.client_id)
        get_track = _req(self.url['track_info'].format(track_id, self.client_id), self.proxies)
        if get_track.status_code != 200:
            raise requests.HTTPError(get_track.status_code)

        get_track = get_track.json()
        get_track = _fix_name(get_track)
        filename = "{} - {}.mp3".format(get_track[0], get_track[1])

        get_links = _req(get_links_url, self.proxies, self.auth)
        if get_links.status_code != 200:
            raise requests.HTTPError(get_links.status_code)
        get_links = get_links.json()
        if 'http_mp3_128_url' in get_links:
            url_to_download = get_links['http_mp3_128_url']
        else:
            url_to_download = get_links['preview_mp3_128_url']
        path = _download_file(url_to_download, filename, self.auth, path=path)
        return path

    def search(self, **kwargs):
        in_kwargs = False
        for i in kwargs:
            if i in ('tracks',):
                in_kwargs = True
        if not in_kwargs:
            raise AttributeError("Available Args: tracks, albums, playlist")
        limit = kwargs.get('limit', 25)
        if 'tracks' in kwargs:
            method = 'tracks'
            name = kwargs['tracks']
        else:
            return
        if 'plus' in kwargs and kwargs['plus']:
            url = self.url['plus'].format(method, quote(name), self.client_id, limit)
            request = _req(url, self.proxies)
            if request.status_code != 200:
                return None
            request = request.json()
            self.reformat(request)
        url = self.url['search'].format(method, quote(name), self.client_id, limit)
        request = _req(url, self.proxies)
        if request.status_code != 200:
            return self.db
        request = request.json()
        self.reformat(request, collection='normal')
        return self.db

    def reformat(self, data, collection=None):
        for i in data['collection']:
            i = i['track'] if collection == 'new' else i
            if i['kind'] == 'track':
                try:
                    if collection and collection == 'normal' and i['playback_count'] < 1000000:
                        continue
                    photo = i['artwork_url'].replace("large.jpg", "t500x500.jpg")
                    if '-' in i['title'] and collection and collection == 'normal':
                        d = i['title'].split('-')
                        i['artist'] = d[0]
                        i['title'] = d[1]
                        artist = i['artist']
                    else:
                        artist = i['publisher_metadata']['artist'] if 'artist' in i['publisher_metadata'] else \
                            i['user']['username']
                    date = dateutil.parse(i['release_date']).date() if i['release_date'] \
                        else dateutil.parse(i['display_date']).date()
                    if 'Remix' in artist or 'Remix' in i['title']:
                        continue
                    genre = i['genre']
                    duration = i['full_duration'] // 1000 if i['full_duration'] else None
                    i['title'] = fix(i['title'])
                    self.db.append({"id": i['id'], "name": i['title'], "artist": artist, 'image': photo,
                                    "duration": duration, "release_date": date, 'genre': genre})
                except:
                    continue
        return
