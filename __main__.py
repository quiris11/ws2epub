#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of ws2epub, licensed under GNU Affero GPLv3 or later.
# Copyright © Robert Błaut. See NOTICE for more information.
#

from __future__ import print_function

__license__ = 'GNU Affero GPL v3'
__copyright__ = '2014, Robert Błaut listy@blaut.biz'
__appname__ = u'ws2epub'
numeric_version = (0, 1)
__version__ = u'.'.join(map(unicode, numeric_version))
__author__ = u'Robert Błaut <listy@blaut.biz>'

import argparse
import sys
import urllib2
import re
import os
from urllib import urlretrieve

from lxml import etree
DTD = ('<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" '
       '"http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">')

parser = argparse.ArgumentParser()
parser.add_argument('-V', '--version', action='version',
                    version="%(prog)s (version " + __version__ + ")")
parser.add_argument("url", help="URL to WS book")
args = parser.parse_args()


def remove_node(node):
    parent = node.getparent()
    index = parent.index(node)
    if node.tail is not None:
        if index == 0:
            try:
                parent.text += node.tail
            except TypeError:
                parent.text = node.tail
        else:
            try:
                parent[index - 1].tail += node.tail
            except TypeError:
                parent[index - 1].tail = node.tail
    parent.remove(node)


def download_images(tree):
    num = 1
    for i in tree.xpath('//img'):
        filext = os.path.splitext(i.get('src').split("/")[-1])[1]
        urlretrieve('https:' + i.get('src'), os.path.join('WSepub',
                                                          'Images',
                                                          str(num) + filext))
        i.attrib['src'] = '../Images/' + str(num) + filext
        num += 1


def create_link_css():
    css = '.small { font-size: 94%; }\n' \
        '.thumbcaption {text-align:center;font-size:90%;font-style:italic;}\n'\
        '.tright { float: right; clear: right; margin: 0.5em 0 0.5em 1em; }\n'\
        '.tleft { float: left; clear: left; margin: 0.5em 1em 0.5em 0; }\n' \
        '.poem { display: table; margin: 0 auto; }\n' \
        '.center { display: table; margin: 0 auto; }\n' \
        '.center, .center * {text-align: center;}\n' \
        'p { text-align: justify; margin: 0; text-indent: 1.2em; }\n' \
        'h1, h2, h3, h4, h5, h6 {text-align: center;}\n'
    # '.center { width : 100%; text-align: center; }\n' \
    # '.center * { margin-left: auto; margin-right: auto; }\n' \
    with open("WSepub/Styles/style.css", "w") as text_file:
        text_file.write(css)


def main():
    if not os.path.isdir('WSepub'):
        os.makedirs('WSepub')
    if not os.path.isdir(os.path.join('WSepub', 'Text')):
        os.makedirs(os.path.join('WSepub', 'Text'))
    if not os.path.isdir(os.path.join('WSepub', 'Images')):
        os.makedirs(os.path.join('WSepub', 'Images'))
    if not os.path.isdir(os.path.join('WSepub', 'Styles')):
        os.makedirs(os.path.join('WSepub', 'Styles'))
    cf = urllib2.urlopen(args.url)
    # doc = html.parse(content)
    content = cf.read()
    # with open("raw.txt", "w") as text_file:
    #     text_file.write(content)
    content = re.sub(r'(\s+[a-z0-9]+)=([\'|\"]{0})([a-z0-9]+)([\'|\"]{0})',
                     r'\1="\3"',
                     content)
    # with open("raw-changed.txt", "w") as text_file:
    #     text_file.write(content)
    # parser = etree.XMLParser(recover=True)
    # doc = etree.parse(content, parser)
    tree = etree.fromstring(content)

    # print(content.read())
    # alltexts = tree.xpath('//body//text()')
    # alltext = ' '.join(alltexts)
    # print(alltext)
    book = tree.xpath('//div[@id="mw-content-text"]')[0]
    title = tree.xpath('//title')[0]
    del tree.xpath('//html')[0].attrib['lang']
    del tree.xpath('//html')[0].attrib['dir']
    del tree.xpath('//html')[0].attrib['class']
    remove_node(tree.xpath('//head')[0])
    remove_node(tree.xpath('//body')[0])
    tree.xpath('//html')[0].append(etree.Element('head'))
    tree.xpath('//head')[0].append(title)
    tree.xpath('//head')[0].append(etree.fromstring(
        '<link rel="stylesheet" type="text/css" href="../Styles/style.css" />'
    ))
    tree.xpath('//html')[0].append(etree.Element('body'))
    tree.xpath('//body')[0].append(book)
    for s in tree.xpath('//table[@class="infobox"]'):
        remove_node(s)
    for s in tree.xpath('//comment()'):
        remove_node(s)
    for s in tree.xpath('//a[@href="/wiki/Pomoc:Przypisy"]'):
        remove_node(s)
    for s in tree.xpath('//span/span[@class="PageNumber"]'):
        remove_node(s)
    for s in tree.xpath('//span[@class="mw-editsection"]'):
        remove_node(s)
    for s in tree.xpath('//div[@class="magnify"]'):
        remove_node(s)
    for s in tree.xpath('//noscript'):
        remove_node(s)
    for s in tree.xpath(
        '//div[@id="Template_law"]/div/div[@style="float: left;"]'
    ):
        remove_node(s)
    for s in tree.xpath('//a[@class="image"]/img'):
        at = s
        app = s.getparent().getparent()
        remove_node(s.getparent())
        app.insert(0, at)
    for s in tree.xpath('//hr'):
        try:
            s.attrib['style'] = 'width: ' + s.attrib['width'] + 'px'
            del s.attrib['width']
        except:
            pass
    for s in tree.xpath('//img'):
        try:
            del s.attrib['srcset']
        except:
            pass
        try:
            del s.attrib['data-file-width']
        except:
            pass
        try:
            del s.attrib['data-file-height']
        except:
            pass
    # for s in tree.xpath('//script'):
    #     remove_node(s)
    # # for s in tree.xpath('//div[@id="content"]'):
    #     # remove_node(s)
    # for s in tree.xpath('//div[@id="mw-head-base"]'):
    #     remove_node(s)
    # for s in tree.xpath('//div[@id="mw-page-base"]'):
    #     remove_node(s)
    # for s in tree.xpath('//div[@id="mw-navigation"]'):
    #     remove_node(s)
    # for s in tree.xpath('//div[@id="catlinks"]'):
    #     remove_node(s)
    # for s in tree.xpath('//div[@id="footer"]'):
    #     remove_node(s)
    # for s in tree.xpath('//div[@id="Template_law"]'):
    #     remove_node(s)
    # for s in tree.xpath('//div[@class="printfooter"]'):
    #     remove_node(s)
    # for s in tree.xpath('//div[@class="visualClear"]'):
    #     remove_node(s)
    # # for s in tree.xpath('//img[@alt="Przypis własny Wikiźródeł"]'):
    #     # remove_node(s)
    download_images(tree)
    create_link_css()
    bs = etree.tostring(
        tree,
        pretty_print=True,
        xml_declaration=True, encoding='utf-8', standalone=False, doctype=DTD
    )
    bs = bs.replace('<span/>', '')
    bs = bs.replace('href="#', 'href="text.html#')
    bs = bs.replace('href="/wiki', 'href="https://pl.wikisource.org/wiki')
    bs = bs.replace('src="//upload', 'src="https://upload')
    bs = bs.replace('<html>', '<html xmlns="http://www.w3.org/1999/xhtml">')
    bs = bs.replace('<center>', '<div class="center">')
    bs = bs.replace('</center>', '</div>')
    bs = bs.replace('<p>', '<div class="para">')
    bs = re.sub(
        r'<p (.+?)>',
        r'<div \1>',
        bs
    )
    bs = bs.replace('</p>', '</div>')
    bs = re.sub(
        r'\n<div class="para">'
        '<span style="padding-left:18px; text-align:left;">.+</span>(.+)<br/>',
        r'\n<div class="para"><p>\1</p>',
        bs
    )
    bs = re.sub(
        r'\n<span style="padding-left:18px; text-align:left;">.+</span>'
        '(.+)<br/>',
        r'\n<p>\1</p>',
        bs
    )
    bs = bs.replace(
        'id="Template_law" class="toccolours" style="border-width:1px 0 0 0"',
        'class="Template_law"'
    )
    with open("WSepub/Text/text.html", "w") as text_file:
        text_file.write(bs)
    # print(etree.tostring(tree))
    if len(sys.argv) == 1:
        print("* * *")
        print("* At least one of above optional arguments is required.")
        print("* * *")
    return 0

if __name__ == '__main__':
    sys.exit(main())
