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
import zipfile
import unicodedata
import shutil
from urllib import unquote
from urllib import urlretrieve

from lxml import etree
SFENC = sys.getfilesystemencoding()
DTD = ('<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" '
       '"http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">')
OPFNS = {'opf': 'http://www.idpf.org/2007/opf'}
XHTMLNS = {'xhtml': 'http://www.w3.org/1999/xhtml'}
DCNS = {'dc': 'http://purl.org/dc/elements/1.1/'}
NCXNS = {'ncx': 'http://www.daisy.org/z3986/2005/ncx/'}

parser = argparse.ArgumentParser()
parser.add_argument('-V', '--version', action='version',
                    version="%(prog)s (version " + __version__ + ")")
parser.add_argument("url", help="URL to WS book")
args = parser.parse_args()


def pack_epub(output_filename, source_dir):
    the_file = '.DS_Store'
    try:
        os.unlink(os.path.join(source_dir, the_file))
    except:
        pass
    for root, dirs, files in os.walk(source_dir):
        for d in dirs:
            try:
                os.unlink(os.path.join(root, d, the_file))
            except:
                pass
    with zipfile.ZipFile(output_filename, "w") as zip:
        zip.writestr("mimetype", "application/epub+zip")
    relroot = source_dir
    with zipfile.ZipFile(output_filename, "a", zipfile.ZIP_DEFLATED) as zip:
        for root, dirs, files in os.walk(source_dir):
            for file in files:
                filename = os.path.join(root, file)
                if os.path.isfile(filename):
                    arcname = os.path.join(os.path.relpath(root, relroot),
                                           file)
                    if sys.platform == 'darwin':
                        arcname = unicodedata.normalize(
                            'NFC', unicode(arcname, 'utf-8')
                        ).encode('utf-8')
                    zip.write(filename, arcname.decode(SFENC))


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


def download_images(tree, btitle, bauthor):
    num = 1
    parser = etree.XMLParser(remove_blank_text=True)
    opftree = etree.parse(os.path.join('WSepub/OPS/content.opf'), parser)
    ncxtree = etree.parse(os.path.join('WSepub/OPS/toc.ncx'), parser)
    manifest = opftree.xpath('//opf:manifest', namespaces=OPFNS)[0]
    if not isinstance(unquote(args.url), unicode):
        url = unquote(args.url).decode('utf-8')
    opftree.xpath('//dc:source', namespaces=DCNS)[0].text = url
    opftree.xpath('//dc:identifier', namespaces=DCNS)[0].text = url
    opftree.xpath('//dc:title', namespaces=DCNS)[0].text = btitle
    opftree.xpath('//dc:creator', namespaces=DCNS)[0].text = bauthor
    # print(etree.tostring(ncxtree.xpath('//ncx:docTitle/ncx:text', namespaces=NCXNS)[0]))
    # sys.exit()
    ncxtree.xpath(
        '//ncx:meta', namespaces=NCXNS
    )[0].attrib['content'] = url
    ncxtree.xpath(
        '//ncx:docTitle/ncx:text', namespaces=NCXNS
    )[0].text = btitle
    ncxtree.xpath(
        '//ncx:docAuthor/ncx:text', namespaces=NCXNS
    )[0].text = bauthor
    for i in tree.xpath('//img'):
        filext = os.path.splitext(i.get('src').split("/")[-1])[1]
        urlretrieve('https:' + i.get('src'), os.path.join(
            'WSepub', 'OPS', 'Images', 'img_' + str(num) + filext
        ))
        i.attrib['src'] = '../Images/img_' + str(num) + filext
        opfitem = etree.fromstring(
            '<item id="img_%s" href="Images/img_%s%s" media-'
            'type="image/jpeg"/>' % (num, num, filext))
        manifest.append(opfitem)
        num += 1
    with open(os.path.join('WSepub/OPS/content.opf'), 'w') as f:
        f.write(etree.tostring(opftree.getroot(), pretty_print=True,
                standalone=False, xml_declaration=True, encoding='utf-8'))
    with open(os.path.join('WSepub/OPS/toc.ncx'), 'w') as f:
        f.write(etree.tostring(ncxtree.getroot(), pretty_print=True,
                standalone=False, xml_declaration=True, encoding='utf-8'))


def main():
    if os.path.exists('WSepub'):
        shutil.rmtree('WSepub')
    shutil.copytree(os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        'resources'), 'WSepub')
    cf = urllib2.urlopen(args.url)
    # doc = html.parse(content)
    content = cf.read()
    # with open("raw.txt", "w") as text_file:
    #     text_file.write(content)
    content = content.replace('&#160;', ' ')
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
    # bauthor = tree.xpath('//tr[td/text() = "Autor"]/td/a/text()')[0]
    # tytul = 'Tytuł'.decode('utf-8')
    # btitle = tree.xpath('//tr[td/text() = "' + tytul + '"]/td/a/text()')[0]
    if tree.xpath('//table[@class="infobox"]/tr[2]/td[1]')[0].text == 'Autor':
        bauthor = tree.xpath('//table[@class="infobox"]/tr[2]/td[2]/a')[0].text
    if tree.xpath('//table[@class="infobox"]/tr[3]/td[1]')[0].text == u'Tytuł':
        btitle = tree.xpath('//table[@class="infobox"]/tr[3]/td[2]/a')[0].text
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
    for s in tree.xpath('//div[@class="refsection"]'):
        del s.attrib['style']
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

    download_images(tree, btitle, bauthor)
    bs = etree.tostring(
        tree,
        pretty_print=True,
        xml_declaration=True, encoding='utf-8', standalone=False, doctype=DTD
    )
    bs = bs.replace('<span/>', '')
    bs = bs.replace('href="#', 'href="text.xhtml#')
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
    bs = re.sub(
        r'\[(\d+)\]</a></sup>',
        r'\1</a></sup>',
        bs
    )
    bs = bs.replace('</p>', '</div>')
    tree = etree.fromstring(bs)
    # print(tree.xpath('//xhtml:div[@class="thumb tright"]', namespaces=XHTMLNS))
    for i, s in enumerate(tree.xpath('///xhtml:div[@class="thumb tright"]', namespaces=XHTMLNS)):
        # print(s.tail)
        # print(etree.tostring(s.getparent()[s.getparent().index(s)-1]))
        s.getparent()[s.getparent().index(s)-1].tail = s.getparent()[s.getparent().index(s)-1].tail + s.tail
        s.tail = ''
        # print(s.getparent()[s.getparent().index(s)+1].tag)
        if s.getparent()[s.getparent().index(s)+1].tag == '{http://www.w3.org/1999/xhtml}br':
            s.getparent().insert(s.getparent().index(s), etree.fromstring('<br/>'))
            remove_node(s.getparent()[s.getparent().index(s)+1])
        # s.getparent().insert(s.getparent().index(s)-1, s)
        # a = tree.xpath('//xhtml:div[@class="thumb tright"][' + str(i+1) + ']/preceding-sibling::xhtml:div', namespaces=XHTMLNS)[-1]
        # print(etree.tostring(a))
        # print('#### ', i)
    # for i, s in enumerate(tree.xpath('//div[@class="thumb tleft"]')):
    #     a = tree.xpath('//div[@class="thumb tleft"][' + str(i+1) + ']/preceding-sibling::div')[-1]
    #     print(etree.tostring(a))
    # for s in tree.xpath('//xhtml:div[@class="thumbcaption"]/xhtml:div', namespaces=XHTMLNS):
    #     print(etree.tostring(s))
    #     print(s.text)
    #     s.getparent().text = s.text
    #     remove_node(s)
    bs = etree.tostring(
        tree,
        pretty_print=True,
        xml_declaration=True, encoding='utf-8', standalone=False, doctype=DTD
    )
    bs = re.sub(
        r'\n<div class="para">'
        '<span style="padding-left:18px; text-align:left;">\s{1}</span>'
        '(.+)<br/>',
        r'\n<div class="para"><p>\1</p>',
        bs
    )
    bs = re.sub(
        r'\n<span style="padding-left:18px; text-align:left;">\s{1}</span>'
        '(.+)<br/>',
        r'\n<p>\1</p>',
        bs
    )
    bs = re.sub(
        r'\n<span style="padding-left:18px; text-align:left;">\s{1}</span>'
        '(.+)\n\n(.+)<br/>',
        r'\n<p>\1\2</p>',
        bs
    )
    bs = bs.replace(
        'id="Template_law" class="toccolours" style="border-width:1px 0 0 0"',
        'class="Template_law"'
    )
    with open(os.path.join("WSepub/OPS/Text/text.xhtml"), "w") as text_file:
        text_file.write(bs)
    # print(etree.tostring(tree))

    pack_epub(bauthor + ' - ' + btitle + '.epub', 'WSepub')
    if len(sys.argv) == 1:
        print("* * *")
        print("* At least one of above optional arguments is required.")
        print("* * *")
    return 0

if __name__ == '__main__':
    sys.exit(main())
