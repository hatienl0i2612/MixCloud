from .progress_bar import *
from .utils import to_screen

class ConnectionError(RequestException):
    """A Connection error occurred."""


early_py_version = sys.version_info[:2] < (2, 7)

def use_ffmpeg(url, filename, DirDownload,ext):
    """
    - use ffmpeg to download with url and user_agent and convert them to .mp4 and put them to path download
    :param url: url m3u8 decripted in GetM3u8
    :param filename: name lesson want to convert
    :param DirDownload: path download to put all video downloaded in there
    :return: a processbar in terminal
    """
    if os.path.exists(r'{}\{}.{}'.format(DirDownload, filename,ext)) is True:
        sys.stdout.write(fg + '[' + fc + '*' + fg + '] : Already downloaded\n')
    else:
        bar_length=25
        try:
            cmd = 'ffmpeg -i "{}" -c copy "{}\{}.{}" -y'.format(url, DirDownload, filename,ext)
            x = 0
            duration = []
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                encoding='utf-8-sig'
            )
            for line in process.stdout:
                line = str(line)

                try:
                    if 'Duration' in line:
                        duration = re.findall(r':\s(.*?)\,', line)
                        h = int(duration[0][0:2])
                        m = int(duration[0][3:5])
                        s = int(duration[0][6:8])
                        x = h + m / 60 + s / 60 / 60
                    if re.findall(r'time=(.*?)\s', line):
                        time = re.findall(r'time=(.*?)\s', line)
                        hh = int(time[0][0:2])
                        mm = int(time[0][3:5])
                        ss = int(time[0][6:8])
                        y = hh + mm / 60 + ss / 60 / 60
                        percent = int((y / x) * bar_length)
                        sys.stdout.write(fg + sb + '\r[' + fc + '*' + fg + f'''] : Duration: {duration[0]} ╢{fc + percent * "#" }{fg + (bar_length-percent) * "-"}╟ {round((y / x) * 100, 2)} % Time: {time[0]}        ''')
                        sys.stdout.flush()
                    if line.startswith('video:'):
                        y = x
                        percent = int((y / x) * bar_length)
                        sys.stdout.write(fg + sb + '\r[' + fc + '*' + fg + f'''] : Duration: {duration[0]} ╢{fc + percent * "#"}{fg + (bar_length - percent) * "-"}╟ 100 % Time: {duration[0]}        ''')
                        sys.stdout.flush()
                except Exception as e:
                    pass
            sys.stdout.write("\n")
        except FileNotFoundError:
            to_screen("This url need ffmpeg\n\tPls download and setup ffmpeg https://www.ffmpeg.org")
            sys.exit()
        except KeyboardInterrupt:
            dir = r'{}\{}.{}'.format(DirDownload, filename,ext)
            if os.path.exists(path=dir):
                if os.path.isfile(dir):
                    os.remove(dir)
            sys.stdout.write(fc + sd + '\n[' + fr + sd + '*' + fc + sd + '] : User Interrupt.\n')
            sys.exit(0)