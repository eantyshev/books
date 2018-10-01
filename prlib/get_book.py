#!/usr/bin/python3

import aiohttp
import asyncio
import logging

import urllib.request
import sys,re
from PIL import Image
import json
import math
import os
from bs4 import BeautifulSoup
from zipfile import ZipFile, ZIP_DEFLATED
import shutil

#logging.basicConfig(level=logging.INFO)

main_url = sys.argv[1]

page = urllib.request.urlopen(main_url).read()
soup = BeautifulSoup(page, 'html.parser')

if len(sys.argv) > 2:
    book_name = sys.argv[2]
else:
    book_name = soup.find('h1', attrs={'class': 'page-title'}).text
zip_name = "{}.zip".format(book_name)
if os.path.exists(zip_name):
    print("File is downloaded: {}".format(zip_name))
    sys.exit(0)

script = soup.head.find_all('script')[-1].text
ptrn = re.compile('{"iipServerURL":"([^"]+)","imageDir":"([^"]+)",'
                  '"objectData":"([^"]+)"')
cgi_url, server_path, info_json_url = [x.replace("\\", "")
                       for x in ptrn.findall(script)[0]]

page_url = ("%(cgi_url)s?FIF=%(server_path)s/%(file)s&JTL=%(zoom)d,%(tile)d")

HEADERS = {
'Accept': '*/*',
'Accept-Encoding': 'gzip, deflate, br',
'Referer': main_url,
'Origin': 'https://www.prlib.ru'
}

f_info = urllib.request.urlopen(info_json_url).read().decode()
j = json.loads(f_info)


def tile_img(page, tile):
    return "page%d/%d.jpg" % (page, tile)


for page, p_info in enumerate(j['pgs']):
    if os.path.exists("page%d.jpg" % page):
        print("Already downloaded page %d" % page)
        continue
    #    break
    print("Download page %d" % page)
    if not os.path.isdir("page%d" % page):
        os.mkdir("page%d" % page)
    WID = int(p_info['d'][-1]['w'])
    HEI = int(p_info['d'][-1]['h'])
    tiles_wid = math.ceil(WID/256)
    tiles_hei = math.ceil(HEI/256)
    print("%dx%d px, %dx%d tiles" % (WID, HEI, tiles_wid, tiles_hei))
    filename = p_info['f']
    zoom = p_info['m']


    async def fetch_tile_async(session, sema, i):
        page_expanded_url = page_url % {'cgi_url': cgi_url,
                                        'server_path': server_path,
                                        'file': filename,
                                        'tile': i, 'zoom': zoom}
        #print("Download page %d, tile %d: %s" % (page, i, page_expanded_url))
        async with sema, session.get(page_expanded_url, headers=HEADERS) as resp:
            sz = 0
            with open(tile_img(page, i), 'wb') as fd:
                while True:
                    chunk = await resp.content.read(1024)
                    sz += len(chunk)
                    if not chunk:
                        break
                    fd.write(chunk)
            return sz

    async def load_page(loop):
        sema = asyncio.Semaphore(5)
        async with aiohttp.ClientSession(loop=loop) as session:
            tasks = [fetch_tile_async(session, sema, i) for i in range(tiles_hei * tiles_wid)]
            results = await asyncio.gather(*tasks)
            return results

    loop = asyncio.get_event_loop()
    results = loop.run_until_complete(load_page(loop))
    #loop.close()
    #for r in results:
    #    print('size %d' % r)
    #until_complete(
    #    tasks
        # asyncio.wait(tasks)
    #)

    new_img = Image.new("RGB", (WID, HEI))
    for row in range(tiles_hei):
        for col in range(tiles_wid):
            i = row * tiles_wid + col
            img = Image.open(tile_img(page, i))
            new_img.paste(img, (256*col, 256*row))

    new_img.save("page%d.jpg" % page)
    shutil.rmtree("page%d" % page)        


print("Creating {} ...".format(zip_name))
with ZipFile(zip_name, 'w', ZIP_DEFLATED) as z:
    for page in os.listdir("."):
        if not page.endswith(".jpg"):
            continue
        z.write(page)
        os.remove(page)
