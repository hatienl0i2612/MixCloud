# ***MixCloud***

***Mix_Cloud - A tool for download track of [`MIX CLOUD`](https://www.mixcloud.com/).***

```
$ python mixcloud.py -h
usage: mixcloud.py [-h] [-s] [-j] url

Mixcloud - A tool for download track mixcloud.

positional arguments:
  url           Url.

optional arguments:
  -h, --help    show this help message and exit

Options:
  -s , --save   Path to save
  -j, --json    Show json of info media.
```

# ***Module***
- ***Colorama***
- ***pycryptodome***
- ***Requests***
     ```
     pip install -r requirements.txt
     ```  
 
# ***Usage***
- ***Install module***
  ```
  pip install -r requirements.txt
  ```
- ***Run*** 
  ```
  python mix_cloud.py -u [url]
  ```

- ***All the track downloaded in folder DOWNLOAD at the same path***

# ***Url Supported***
- Track url : ```https://www.mixcloud.com/<uploader>/<slug>```
- Playlist tracks of user : 
    ```
    https://www.mixcloud.com/<name user>
    https://www.mixcloud.com/<name user>/stream
    https://www.mixcloud.com/<name user>/uploads
    https://www.mixcloud.com/<name user>/favorites
    https://www.mixcloud.com/<name user>/listens
    ``` 

# ***Options***
- ***`-s` or `--saved` : Saved file name.***
- ***`-j` or `--json`  : Print json info.***
- ***Some url is hls, need setup [ffmpeg](https://www.ffmpeg.org/)***


# ***Note***
  - ***[`facebook`](https://www.facebook.com/hatien.l0i261299/)***
  - ***`hatienloi261299@gmail.com`***
