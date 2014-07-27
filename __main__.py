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

from lxml import etree


parser = argparse.ArgumentParser()
parser.add_argument('-V', '--version', action='version',
                    version="%(prog)s (version " + __version__ + ")")
parser.add_argument("url", help="URL to WS book")
args = parser.parse_args()


def main():
    cf = urllib2.urlopen(args.url)
    # doc = html.parse(content)
    content = cf.read()
    with open("raw.txt", "w") as text_file:
        text_file.write(content)
    content = re.sub(r'(\s+[a-z0-9]+)=([\'|\"]{0})([a-z0-9]+)([\'|\"]{0})',
                     r'\1="\3"',
                     content)
    with open("raw-changed.txt", "w") as text_file:
        text_file.write(content)
    # parser = etree.XMLParser(recover=True)
    # doc = etree.parse(content, parser)
    tree = etree.fromstring(content)

    # print(content.read())

    # alltexts = tree.xpath('//body//text()')
    for s in tree.xpath('//script'):
        s.getparent().remove(s)
    # alltext = ' '.join(alltexts)
    # print(alltext)
    for s in tree.xpath('//div[@id="mw-navigation"]'):
        s.getparent().remove(s)
    for s in tree.xpath('//div[@id="catlinks"]'):
        s.getparent().remove(s)
    for s in tree.xpath('//div[@id="footer"]'):
        s.getparent().remove(s)
    for s in tree.xpath('//div[@id="Template_law"]'):
        s.getparent().remove(s)
    # for s in tree.xpath('//img[@alt="Przypis własny Wikiźródeł"]'):
        # s.getparent().remove(s)
    # for s in tree.xpath('//a[@href="/wiki/Pomoc:Przypisy"]'):
        # s.getparent().remove(s)
    for s in tree.xpath('//span/span[@class="PageNumber"]'):
        s.getparent().remove(s)
    with open("raw-changed.html", "w") as text_file:
        text_file.write(etree.tostring(
            tree,
            pretty_print=True,
            xml_declaration=True, encoding='utf-8', standalone=False
        ))
    # print(etree.tostring(tree))
    if len(sys.argv) == 1:
        print("* * *")
        print("* At least one of above optional arguments is required.")
        print("* * *")
    return 0

if __name__ == '__main__':
    sys.exit(main())
