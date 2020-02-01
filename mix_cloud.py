from color import *
from session import get_req
from utils import *


class ExtractMixCloud(ProgressBar):
    def __init__(self, *args, **kwargs):
        self._url = kwargs.get('url')
        self._file_save = kwargs.get('file_save') or os.getcwd()
        self._show_all_info = kwargs.get('show_all_info') or False
        self._playlist = kwargs.get('playlist') or None
        self._headers = HEADERS
        self._base_https = 'https://www.mixcloud.com/'
        self._base_api = 'https://www.mixcloud.com/graphql'
        self._string_regex_url = r'https?://(?:(?:www|beta|m)\.)?mixcloud\.com/([^/]+)/(?!stream|uploads|favorites|listens|playlists)([^/]+)'
        self._guest_token = None
        self._type_url = ['dashUrl', 'hlsUrl', 'url']
        self._decryption_key = 'IFYOUWANTTHEARTISTSTOGETPAIDDONOTDOWNLOADFROMMIXCLOUD'

    def run(self):
        if self._playlist:
            list_urls = self._playlist.split(',')
            for url in list_urls:
                self._url = str(url).strip()
                self._extract_mix_cloud()
        else:
            return self._extract_mix_cloud()

    def _extract_mix_cloud(self):
        sys.stdout.write('\n')
        username, slug = re.match(self._string_regex_url, self._url).groups()
        username, slug = unquote(username), unquote(slug)
        self.t = fg + '\r[' + fc + '*' + fg + '] : Extracting info of track %s ... ' % slug
        self.spinner(text=self.t)
        track_id = '%s_%s' % (username, slug)
        json_cloudcast = self._download_json_from_api(type='cloudcast', fields='''
    audioLength
    comments(first: 100) {
        edges {
            node {
                comment
                created
                user {
                    displayName
                    username
                    picture(width: 1024, height: 1024) {
                        url
                    }
                }
            }
        }
        totalCount
    }
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
    }
    tags {
        tag {
            name
        }
    }''', username=username, slug=slug)

        title = json_cloudcast.get('name')
        description = json_cloudcast.get('description')
        plays = is_int(try_get(json_cloudcast, lambda x: x['plays']))

        get_count = lambda x: is_int(try_get(json_cloudcast, lambda y: y[x]['totalCount']))

        reposts = get_count('reposts')
        favorites = get_count('favorites')
        comments = []
        comments.append({'comment_count': get_count('comments')})
        for comment in json_cloudcast.get('comments', {}).get('edges', []):
            node = comment.get('node') or {}
            text = node.get('comment')
            user = node.get('user') or {}
            self.spinner(text=self.t)
            if not text or not user:
                continue
            else:
                comments.append({
                    'username': user.get('username'),
                    'displayName': user.get('displayName'),
                    'pictureProfile': user.get('picture', {}).get('url', str),
                    'text': text,
                    'created': node.get('created'),
                })
        tags = []
        for tag in json_cloudcast.get('tags', []):
            name = try_get(tag, lambda x: x['tag']['name'], str)
            if name:
                self.spinner(text=self.t)
                tags.append(name)

        stream_info = json_cloudcast.get('streamInfo') or ErrorException('Cant extract url stream of video.')
        tracks = []
        for type in self._type_url:
            url_encripted = stream_info.get(type)
            if not url_encripted:
                continue
            self.spinner(text=self.t)
            url_decrypted = self._decrypt_xor_cipher(key=self._decryption_key, url_encripted=url_encripted)
            if type == 'hlsUrl':
                url_hls = self._decrypt_url_hls(url_m3u8=url_decrypted)
                tracks.append({
                    'type': 'hls',
                    'url': url_hls,
                    'ext': 'm4a'
                })
            elif type == 'dashUrl':
                tracks.append(self._extract_info_mpd(url_decrypted))
            else:
                tracks.append({
                    'type': 'http',
                    'url': url_decrypted,
                    'ext': 'm4a'
                })
        info_track = {
            'title': title,
            'track_id': track_id,
            'description': description,
            'plays': plays,
            'reposts': reposts,
            'favorites': favorites,
            'tracks': tracks,
            'comments': comments,
            'featuringArtistList': json_cloudcast.get('featuringArtistList') or None,
            'isExclusive': json_cloudcast.get('isExclusive'),
            'publishDate': json_cloudcast.get('publishDate'),
            'tags': tags
        }
        sys.stdout.write(fg + '\r[' + fc + '*' + fg + '] : Extracting info of track %s ... (done)\n' % slug)
        return self._download_track(dict_info_track=info_track)

    def _download_track(self, dict_info_track):
        title = removeCharacter_filename(dict_info_track.get('title'))
        path_save = '%s/%s' % (self._file_save, 'DOWNLOAD')
        if not os.path.exists(path_save):
            os.mkdir(path_save)
        if self._show_all_info:
            io_path = '%s/%s.txt' % (path_save, title)
            with io.open(io_path, 'w', encoding='utf-8') as f:
                for k, v in dict_info_track.items():
                    if k == 'comments':
                        f.writelines(' - %s : \n' % (k))
                        for i in v:
                            if isinstance(i, dict):
                                for i_k, i_v in i.items():
                                    f.writelines('\t + %s : %s\n' % (i_k, i_v))
                                f.writelines('\n\n')
                    else:
                        f.writelines(' - %s : %s\n' % (k, v))
        else:
            tracks = dict_info_track.get('tracks')
            for track in tracks:
                track_type = track.get('type')
                if track_type == 'hls':
                    # down = Download_m3u8(urlM3u8=track.get('url'), name=title, callback=self.show_progress,
                    #                      DirDownload=path_save, ext=track.get('ext'))
                    # down.run()
                    pass
                elif track_type == 'dash':
                    pass
                elif track_type == 'http':
                    pass
                    down = Downloader(url=track.get('url'))
                    down.download(filepath='%s/%s.m4a' % (path_save, title), callback=self.show_progress)

    def _extract_info_mpd(self, url):
        text = get_req(url=url, headers=HEADERS, type='text')
        text = text.replace('\n', '').replace(' ', '')
        string_regex_mpd = r'''\<Period\>.*?media=\"(?P<media>(.*?))fragment.*?mimeType=\"(?P<minetype>(.*?)\").*?codecs=\"(?P<codecs>(.*?)\").*?audioSamplingRate=\"(?P<samplingrate>(.*?)\").*?bandwidth=\"(?P<bandwidth>(.*?)\")'''
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

    def _decrypt_url_hls(self, url_m3u8):
        r = get_req(url_m3u8)
        streamInfo = re.findall(r"#EXT-X-STREAM-INF:.*?BANDWIDTH=(\d+).*?\n([\w\d$-_.+!*\'\(\),]+)",
                                str(r.text))
        if streamInfo:
            BandWidth = list(map(int, [x[0] for x in streamInfo]))
            if BandWidth:
                return urljoin(url_m3u8, streamInfo[BandWidth.index(max(BandWidth))][1])

    def _decrypt_xor_cipher(self, key, url_encripted):
        dataout = ''
        d = b64decode(url_encripted)
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
        }, type='json')
        return _json['data'].get(lookup_key)


class ExtractMixCloudPLaylist(ExtractMixCloud):
    def __init__(self, *args, **kwargs):
        super(ExtractMixCloudPLaylist, self).__init__(*args, **kwargs)
        self._string_regex = r'https?://(?:www\.)?mixcloud\.com/(?P<id>[^/]+)/(?P<type>uploads|favorites|listens|stream)?/?$'
        self._title_key = 'displayName'
        self._description_key = 'biog'
        self._root_type = 'user'
        self._node_template = '''slug
                  url'''

    def run(self):
        return self._extract_playlist()

    def _extract_playlist(self):
        username, slug = re.match(self._string_regex, self._playlist).groups()
        username = unquote(username)
        if not slug:
            slug = 'uploads'
        else:
            slug = unquote(slug)
        playlist_id = '%s_%s' % (username, slug)
        is_playlist_type = self._root_type == 'playlist'
        playlist_type = 'items' if is_playlist_type else slug
        list_filter = ''
        t = fg + '\r[' + fc + '*' + fg + '] : Extracting info %s of %s ... ' % (slug, username)
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
        }''' % (self._title_key, self._description_key, playlist_type, list_filter, self._node_template), username,
                slug if is_playlist_type else None)
            items = playlist.get(playlist_type) or {}
            for edge in items.get('edges', list):
                self.spinner(text=t)
                entries.append({
                    'url': edge.get('node', dict).get('url', str),
                    'slug': edge.get('node', dict).get('slug', str)
                })
            page_info = items['pageInfo']
            has_next_page = page_info['hasNextPage']
            list_filter = ', after: "%s"' % page_info['endCursor']
        for ent in entries:
            self._url = ent.get('url') or None
            if self._url:
                self._extract_mix_cloud()
        return


def main(argv):
    parser = argparse.ArgumentParser(description='MixCloud - A tool for download track.')
    parser.add_argument('-u', '--url', type=str, help='Download url.', dest='url')
    parser.add_argument('-s', '--saved', type=str, default=os.getcwd(), help='Saved file name.', dest='file_name')
    parser.add_argument('-i', '--info', default=False, action='store_true', help='Show all info of video.',
                        dest='show_all_info')
    parser.add_argument('-l', '--playlist', type=str, help='Download playlist of user.',
                        dest='play_list')
    args = parser.parse_args()
    if args.url:
        extract = ExtractMixCloud(url=args.url, file_save=args.file_name,
                                  show_all_info=args.show_all_info, playlist=args.play_list)
        extract.run()
    elif args.play_list:
        extract = ExtractMixCloudPLaylist(file_save=args.file_name, show_all_info=args.show_all_info,
                                          playlist=args.play_list)
        extract.run()


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
