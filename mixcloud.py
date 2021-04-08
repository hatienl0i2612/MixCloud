from setup import *


class ExtractMixcloud(ProgressBar):
    def __init__(self, *args, **kwargs):
        self._url = kwargs.get('url')
        self._path_save = kwargs.get('path_save') or os.getcwd()
        self._show_json_info = kwargs.get('show_json_info') or False
        self._headers = HEADERS
        self._base_https = 'https://www.mixcloud.com/'
        self._base_api = 'https://www.mixcloud.com/graphql'
        self._regex_url = r'https?://(?:(?:www|beta|m)\.)?mixcloud\.com/([^/]+)/(?!stream|uploads|favorites|listens|playlists)([^/]+)'
        self._guest_token = None
        self._type_url = ['dashUrl', 'hlsUrl', 'url']
        self._decryption_key = 'IFYOUWANTTHEARTISTSTOGETPAIDDONOTDOWNLOADFROMMIXCLOUD'

    def run_track(self, url=None):
        if not url:
            url = self._url
        username, slug = re.match(self._regex_url, url).groups()
        username, slug = unquote(username), unquote(slug)
        track_id = '%s_%s' % (username, slug)
        DirDownload = os.path.join(self._path_save, "DOWNLOAD")
        if not os.path.exists(DirDownload):
            os.mkdir(DirDownload)
        json_cloudcast = self._download_json_from_api(type='cloudcast', fields='''
            audioLength
            description
            favorites {
                totalCount
            }
            featuringArtistList
            isExclusive
            name
            owner {
                id
                displayName
                url
                username
            }
            picture(width: 1024, height: 1024) {
                url
            }
            plays
            publishDate
            reposts {
                totalCount
            }
            streamInfo {
                dashUrl
                hlsUrl
                url
            }''', username=username, slug=slug)
        title = json_cloudcast.get("name")
        title = removeCharacter_filename(title)
        to_screen(title)
        stream_info = json_cloudcast.get('streamInfo') or None
        if not stream_info:
            to_screen("Cant extract url stream of video.")
            return
        tracks = []
        for _type in self._type_url:
            url_encripted = stream_info.get(_type)
            if not url_encripted:
                continue
            url_decrypted = self._decrypt_xor_cipher(key=self._decryption_key, url_encripted=url_encripted)
            if _type == 'hlsUrl':
                # url_hls = self._decrypt_url_hls(url_m3u8=url_decrypted)
                tracks.append({
                    'type': 'hls',
                    'url': url_decrypted,
                    'ext': 'm4a'
                })
            elif _type == 'dashUrl':
                # data_dash = self._extract_info_mpd(url_decrypted)
                tracks.append({
                    "type": 'dash',
                    "url": url_decrypted,
                    "ext": "m4a",
                })
            else:
                tracks.append({
                    'type': 'http',
                    'url': url_decrypted,
                    'ext': 'm4a'
                })
        if self._show_json_info:
            sys.stdout.write(json.dumps(tracks,ensure_ascii=False))
            return

        will_down = tracks[-1]
        _type = will_down.get("type")
        url = will_down.get("url")
        ext = will_down.get("ext")
        path_download = os.path.join(DirDownload, "%s.%s" % (title, ext))
        if _type == "http":
            down = Downloader(url=url)
            down.download(filepath=path_download, callback=self.show_progress)
        elif _type == "hls" or _type == "dash":
            use_ffmpeg(
                url=url,
                filename=title,
                DirDownload=DirDownload,
                ext=ext
            )
        sys.stdout.write("\n\n")
        return

    def _decrypt_url_hls(self, url_m3u8):
        r = get_req(url_m3u8)
        streamInfo = re.findall(r"#EXT-X-STREAM-INF:.*?BANDWIDTH=(\d+).*?\n([\w\d$-_.+!*\'\(\),]+)",
                                str(r.text))
        if streamInfo:
            BandWidth = list(map(int, [x[0] for x in streamInfo]))
            if BandWidth:
                return urljoin(url_m3u8, streamInfo[BandWidth.index(max(BandWidth))][1])

    def _extract_info_mpd(self, url):
        text = get_req(url=url, headers=HEADERS, type='text')
        text = text.replace('\n', '').replace(' ', '')
        string_regex_mpd = r'''\<Period\>.*?media=\"(?P<media>(.*?))fragment.*?mimeType=\"(?P<minetype>(.*?))\".*?codecs=\"(?P<codecs>(.*?))\".*?audioSamplingRate=\"(?P<samplingrate>(.*?))\".*?bandwidth=\"(?P<bandwidth>(.*?))\"'''
        item = re.search(string_regex_mpd, text)
        return {
            'media': item.group('media'),
            'url': url,
            'ext': mimetype2ext(mt=item.group('minetype')),
            'codecs': item.group('codecs'),
            'samplingrate': item.group('samplingrate'),
            'bandwidth': item.group('bandwidth'),
            'type': 'dash'
        }

    def _decrypt_xor_cipher(self, key, url_encripted):
        dataout = ''
        d = base64.b64decode(url_encripted)
        for acci, text in zip(d, itertools.cycle(key)):
            dataout += chr(acci ^ ord(text))
        return dataout

    def _download_json_from_api(self, type, fields, username, slug):
        lookup_key = type + 'Lookup'
        _json = get_req(url=self._base_api, headers=self._headers, params={
            'query': '''{
                    %s(lookup: {username: "%s"%s}) {
                        %s
                    }
                }''' % (lookup_key, username, ', slug: "%s"' % slug if slug else '', fields)
        }, type='json', note="Downloading json from api.")
        return _json['data'].get(lookup_key)


class ExtractPlaylistMixcloud(ExtractMixcloud):
    def __init__(self, *args, **kwargs):
        super(ExtractPlaylistMixcloud, self).__init__(*args, **kwargs)
        self._regex_playlist = r'https?://(?:www\.)?mixcloud\.com/(?P<id>[^/]+)/(?P<type>uploads|favorites|listens|stream)?/?$'
        self._title_key = 'displayName'
        self._description_key = 'biog'
        self._root_type = 'user'
        self._node_template = '''slug
                          url'''

    def run_playlist(self,url = None):
        if not url:
            url = self._url

        username, slug = re.match(self._regex_playlist, url).groups()
        username = unquote(username)
        if not slug:
            slug = 'stream'
        else:
            slug = unquote(slug)
        playlist_id = '%s_%s' % (username, slug)
        is_playlist_type = self._root_type == 'playlist'
        playlist_type = 'items' if is_playlist_type else slug
        list_filter = ''
        has_next_page = True
        entries = []
        while has_next_page:
            playlist = self._download_json_from_api(
                self._root_type, '''%s
                %s
                %s(first: 100%s) {
                  edges {
                    node {
                      %s
                    }
                  }
                  pageInfo {
                    endCursor
                    hasNextPage
                  }
                }''' % (self._title_key, self._description_key, playlist_type, list_filter, self._node_template),
                username,
                slug if is_playlist_type else None)
            items = playlist.get(playlist_type) or {}
            for edge in items.get('edges', list):
                entries.append({
                    'url': edge.get('node', dict).get('url', str),
                    'slug': edge.get('node', dict).get('slug', str)
                })
            page_info = items['pageInfo']
            has_next_page = page_info['hasNextPage']
            list_filter = ', after: "%s"' % page_info['endCursor']
        to_screen("Playlist %s found %s tracks" % (playlist_id,len(entries)))
        for ent in entries:
            _url = ent.get('url') or None
            if _url:
                self.run_track(url=_url)
        return


class Base:
    def __init__(self, *args, **kwargs):
        tm = ExtractPlaylistMixcloud(*args, **kwargs)
        url = kwargs.get("url")

        if re.match(tm._regex_url, url):
            tm.run_track()
        if re.match(tm._regex_playlist,url):
            tm.run_playlist()

def main(argv):
    parser = argparse.ArgumentParser(description='Mixcloud - A tool for download track mixcloud.')
    parser.add_argument('url', type=str, help='Url.')

    opts = parser.add_argument_group("Options")
    opts.add_argument('-s', '--save', type=str, default=os.getcwd(), help='Path to save', dest='path_save', metavar='')
    opts.add_argument('-j', '--json', default=False, action='store_true', help="Show json of info media.",
                      dest='show_json_info')
    args = parser.parse_args()
    Base(
        url=args.url,
        path_save=args.path_save,
        show_json_info=args.show_json_info,
    )


if __name__ == '__main__':
    try:
        if sys.stdin.isatty():
            main(sys.argv)
        else:
            argv = sys.stdin.read().split(' ')
            main(argv)
    except KeyboardInterrupt:
        sys.stdout.write(
            fc + sd + "\n[" + fr + sb + "-" + fc + sd + "] : " + fr + sd + "User Interrupted..\n")
        sys.exit(0)
