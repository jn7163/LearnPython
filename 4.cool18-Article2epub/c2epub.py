#!/usr/bin/python3
import argparse
import configparser
import os
import re
import shutil
import sys
import urllib

import bs4
import html2epub
import requests

# requires: requests bs4 lxml pysocks html2epub

config = {
    "enableProxy": "no",
    "proxy": "socks5://127.0.0.1:1081",
    "minContent": 1000,
    "waitPackage": "no",
    "autoDelete": "yes",
    "verifyCert": "yes"
}

def to_str(bytes_or_str):
    if isinstance(bytes_or_str, bytes):
        value = bytes_or_str.decode('utf-8')
    else:
        value = bytes_or_str
    return value


def to_bytes(bytes_or_str):
    if isinstance(bytes_or_str, str):
        value = bytes_or_str.encode('utf-8')
    else:
        value = bytes_or_str
    return value


def fetch(url):

    if config['enableProxy'] == 'yes':
        proxy = config['proxy']
        proxies = dict(http=proxy, https=proxy)
        try:
            resp = requests.get(url, proxies=proxies, verify=verifySSLCert)
            src = to_str(resp.content)
            return src
        finally:
            pass
    else:
        try:
            resp = requests.get(url)
            src = to_str(resp.content)
            return src
        except:
            return ""


P_START = "<!--bodybegin-->"
P_END = "<!--bodyend-->"
L_START = '''<a name="followups" style=''>'''
L_END = '''<a name="postfp">'''


def extract_title(content, full=False):
    title_left = content.find('<title>')+len('<title>')
    title_right = content.find('</title>')
    title = content[title_left:title_right]

    if (full):
        title = title.replace(" - cool18.com", "").replace("/",
                                                           "-").replace("\\", "-").strip()
    else:
        title_search = re.search('[【《](.*)[】》]', title, re.IGNORECASE)
        if title_search:
            title = title_search.group(1)
        else:
            title = title.replace(
                " - cool18.com", "").replace("/", "-").replace("\\", "-").strip()

    return title


def loadConfig():
    cf = configparser.ConfigParser()
    try:
        cf.read('config.ini')
        config['enableProxy'] = cf.get('network', 'enableProxy')
        config['proxy'] = cf.get('network', 'proxy')
        config['minContent'] = cf.get('config', 'minContent')
        config['waitPackage'] = cf.get('config', 'waitPackage')
        config['verifyCert'] = cf.get('network', 'verifyCert')
    except:
        pass



def download(url):
    if not (config['host'] in url):
        return
    uri = urllib.parse.urlparse(url)
    params = urllib.parse.parse_qs(uri.query)

    tid = params['tid']
    if not tid:
        return

    src = fetch(url)
    title = extract_title(src, full=True)
    print('+%s' % title)

    # REMOVE BLANKS

    raw = str(src)

    try:
        pos_start = raw.find(P_START)+len(P_START)
        pos_end = raw.find(P_END)
        page_content = raw[pos_start:pos_end]
        content_soup = bs4.BeautifulSoup(page_content, "lxml")
        # extract in page chapters
        links = content_soup.find_all('a')
        for a in links:
            _title = a.getText()
            print(_title)
            _url = a.get('href')

            if (_url and len(_url.strip()) > 8):
                hive.append(_url)

            a.extract()
    except ValueError:
        return

    try:
        # extract below links
        lpos_start = raw.find(L_START)+len(L_START)
        lpos_end = raw.find(L_END)
        comments = raw[lpos_start:lpos_end]
        comm_soup = bs4.BeautifulSoup(comments, "lxml")
        for a in comm_soup.find_all('a'):
            _title = a.getText()
            if ('银元奖励' in _title) or ('无内容' in _title) or ('版块基金' in _title) or (' 给 ' in _title) or ('幸运红包' in _title):
                continue
            print('+%s' % _title)
            _u = a.get('href')
            if (_u and _u.startswith("http")):
                hive.append(_u)
            else:
                hive.append(config['host'] + _u)
    except ValueError:
        pass

    # SKIP DOWNLOADED FILES
    if (os.path.exists("%s-%s.html" % (tid, title))):
        print("#%s-%s.html already exists." % (tid, title))
        return

    [s.extract() for s in content_soup('script')]

    page_content = str(content_soup.find('body').getText())
    page_content = page_content.replace("\n", "")
    page_content = page_content.replace(
        'cool18.com', '\n').replace('www.6park.com', '').replace('6park.com', '').replace("\n", "</p><p>").replace("<p></p>", "")
    try:
        last_pos = page_content.rindex('评分完成')
        page_content = page_content[:last_pos]
    except ValueError:
        pass

    if (len(page_content.strip()) > int(config['minContent'])):
        try:
            with open("%s-%s.html" % (tid, title), 'w+', encoding='utf-8', errors='ignore') as file:
                file.write(
                    '<?xml version="1.0" encoding="utf-8"?><!DOCTYPE html><html><head><META HTTP-EQUIV="content-type" CONTENT="text/html; charset=utf-8">  <title>')
                file.write(title)
                file.write("</title></head><body><pre><p>")
                file.write(page_content)
                file.write("</p></pre></body></html>")
                print('>Done')
        except:
            print("Error writing %s" % title)


# Main Logic
if __name__ == '__main__':
    verifySSLCert=True
    parser = argparse.ArgumentParser(
        description="Download articles from cool18.com then generate epub.")
    parser.add_argument("url", type=str, help="a cool18.com article URL.")
    args = parser.parse_args()
    loadConfig()
    if config['verifyCert'] == 'yes':
        verifySSLCert = True
    else:
        verifySSLCert = False
    pypath = sys.argv[0]
    pydir = os.getcwd()

    config['host'] = args.url[:args.url.rindex('/')+1]

    src = fetch(args.url)
    title = extract_title(src)

    if not os.path.exists(title):
        os.mkdir(title)
    os.chdir(title)

    # Init Hive
    hive = [args.url]
    downloaded = set()

    while hive:
        current_url = hive.pop()
        if (current_url in downloaded):
            print("-%s " % current_url)
        else:
            print("~[%d] %s" % (len(hive), current_url))
            downloaded.add(current_url)
            download(current_url)
    if config['waitPackage'] == 'yes':
        input('>Press Enter when ready...')

    print(">Download completed, now packaging epub...")
    epub = html2epub.Epub(title, language="zh-cn",
                          creator="cool18", publisher="cool18")
    for file in os.listdir("."):
        chap = html2epub.create_chapter_from_file(file)
        epub.add_chapter(chap)
    epubpath = epub.create_epub(pydir)
    print(">OK, epub generated at: %s" % epubpath)

    if config['autoDelete'] == 'yes':
        os.chdir("..")
        print(">Deleting Directory: %s" % title)
        shutil.rmtree(title)
