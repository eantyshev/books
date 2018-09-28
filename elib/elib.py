#!/usr/bin/python2

import os, sys
import requests
import lxml.html as lh
import re
import zipfile

JPG_URL_PATTERN = "http://elib.shpl.ru/pages/%d/zooms/8"

def get_pages(url):
    r = requests.get(url)
    if not r.ok:
        raise Exception("Failed to download %s: code %d" %
                        (url, r.status_code))

    h_obj = lh.fromstring(r.text)

    # dirty JS parsing
    s = lh.tostring(h_obj)

    pages = []
    for m in re.finditer("\"(\d+)\"\:\"\/system\/pages[/0-9]*images\/small",
                         s, re.M):
        pages.append(int(m.group(1)))

    return pages

def get_dir_name(url):
    return url.split("/")[-1]

def download_jpg(url, fname):
    r = requests.get(url)
    if r.ok:
        with open(fname, 'wb') as f:
            for chunk in r:
                f.write(chunk)
    else:
        print "Failed to download %s: code %s" % (url, r.status_code)

def zip(archive, path):
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED, False) as z:
        for f in os.listdir(path):
            print "Add to archive %s: %s" % (archive, f)
            z.write(os.path.join(path, f), f)
        

def main():
    URL = sys.argv[1]
    pages = get_pages(URL)
    if len(sys.argv) > 2:
        dirname = sys.argv[2]
    else:
        dirname = get_dir_name(URL)

    if not os.path.isdir(dirname):
        os.mkdir(dirname)
    for i in pages:
        jpg_url = JPG_URL_PATTERN % i
        jpg_file = os.path.join(dirname, "%s.jpg" % i)
        print "downloading %s to %s" % (jpg_url, jpg_file)
        download_jpg(jpg_url, jpg_file)
    zip(dirname + ".zip", dirname)

if __name__ == '__main__':
    main()
