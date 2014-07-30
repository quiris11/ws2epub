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
from StringIO import StringIO
from urllib import unquote, quote
from urllib import urlretrieve
from cover import DefaultEbookCover


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
parser.add_argument("-f", "--force",
                    help="overwrite previously generated epub files",
                    action="store_true")
parser.add_argument("url", help="URL to WS book or TXT file with URLs")
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


def generate_cover(bauthor, btitle):
    cover = DefaultEbookCover
    cover_file = StringIO()
    bound_cover = cover(bauthor, btitle)
    bound_cover.save(cover_file)
    with open(os.path.join("WSepub/OPS/Images/cover.jpg"), "w") as coverf:
        coverf.write(cover_file.getvalue())


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
    lauthor = bauthor.split(' ')
    bauthorinv = lauthor[-1] + ', ' + ' '.join(lauthor[:-1])
    opftree.xpath(
        '//dc:creator',
        namespaces=DCNS
    )[0].attrib['{http://www.idpf.org/2007/opf}file-as'] = bauthorinv
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


def move_law(tree):
    parser = etree.XMLParser(remove_blank_text=True)
    infotree = etree.parse(os.path.join('WSepub/OPS/Text/info.xhtml'), parser)
    for l in tree.xpath('//xhtml:div[@class="Template_law"]',
                        namespaces=XHTMLNS):
        infotree.xpath('//xhtml:div[@id="law"]',
                       namespaces=XHTMLNS)[0].append(l)
    for l in infotree.xpath('//xhtml:div[@class="Template_law"]/xhtml:div',
                            namespaces=XHTMLNS):
        del l.attrib['style']
    for l in tree.xpath('//xhtml:div[@class="Template_law"]',
                        namespaces=XHTMLNS):
        remove_node(l)
    with open(os.path.join('WSepub/OPS/Text/info.xhtml'), 'w') as f:
        f.write(etree.tostring(infotree.getroot(), pretty_print=True,
                standalone=False, xml_declaration=True, encoding='utf-8'))


def process_toc(url):
    url = '/'.join(url.split('/')[:-1])
    title = url.split('/')[-1]
    title = quote(title)
    print('####', title)
    cf = urllib2.urlopen(url)
    content = cf.read()
    content = content.replace('&#160;', ' ')
    content = re.sub(r'(\s+[a-z0-9]+)=([\'|\"]{0})([a-z0-9]+)([\'|\"]{0})',
                     r'\1="\3"',
                     content)
    tree = etree.fromstring(content)
    rozlist = []
    roz_f = True
    for a in tree.xpath('//a[@href]'):
        if (a.get('href').startswith('/wiki/' + title + '/') and
                not a.get('href').endswith('a%C5%82o%C5%9B%C4%87')):
            roz = a.get('href').split('/')[-1]
            if not isinstance(unquote(roz), unicode):
                roz = unquote(roz).decode('utf-8')
            roz = roz.replace('_', ' ')
            if not roz_f:
                rozlist.append(roz)
            roz_f = False
    return rozlist


def build_toc_ncx(tree, rozlist):
    parser = etree.XMLParser(remove_blank_text=True)
    ncxtree = etree.parse(os.path.join('WSepub/OPS/toc.ncx'), parser)
    num = 0
    # print(rozlist)
    for r in rozlist:
        num += 1
        # print(r.encode('utf8'))
        for s in tree.xpath('//xhtml:body/xhtml:div/xhtml:div/xhtml:div'
                            '/xhtml:div[@class="center"]',
                            namespaces=XHTMLNS):
            a = ''.join(s.itertext())
            # print(num, repr(r.encode('utf8').lower()), repr(a.lower()))
            # if a is None:
            #     continue
            # print(num, repr(r.encode('utf8').lower()), repr(a.lower()))
            # print(a.encode('utf8'))
            if r.lower().encode('utf8') in a.lower().encode('utf8'):
                print('#', num, r, s.text)
                s.getparent().insert(
                    s.getparent().index(s),
                    etree.fromstring(
                        '<div class="wsrozdzial" '
                        'id="wsrozdzial_' + str(num) + '"/>'
                    )
                )
                break
        nm = ncxtree.xpath('//ncx:navMap', namespaces=NCXNS)[0]
        nm.insert(
            num+1,
            etree.fromstring(
                '<navPoint id="wsrozdzial_' + str(num) + '">'
                '<navLabel><text>'
                '' + r + ''
                '</text></navLabel><content src="Text/text.xhtml#'
                'wsrozdzial_' + str(num) + '" /></navPoint>'
            )
        )
    try:
        tree.xpath('//xhtml:hr[not(@*)]',
                   namespaces=XHTMLNS)[0].attrib['class'] = 'wsrozdzial'
    except:
        pass
    with open(os.path.join('WSepub/OPS/toc.ncx'), 'w') as f:
        f.write(etree.tostring(ncxtree.getroot(), pretty_print=True,
                standalone=False, xml_declaration=True, encoding='utf-8'))


def generate_inline_toc():
    parser = etree.XMLParser(remove_blank_text=True)
    ncxtree = etree.parse(os.path.join('WSepub/OPS/toc.ncx'), parser)
    transform = etree.XSLT(etree.parse(os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        'xsl', 'ncx2end-0.2.xsl'
    )))
    result = transform(ncxtree)
    for h in result.xpath('//xhtml:a', namespaces=XHTMLNS):
        h.attrib['href'] = h.get('href').replace('Text/', '')
    with open(os.path.join("WSepub/OPS/Text/toc.xhtml"), "w") as f:
        f.write(etree.tostring(
            result,
            pretty_print=True,
            xml_declaration=True,
            standalone=False,
            encoding="utf-8",
            doctype=DTD
        ))


def process_url(url):
    rozlist = process_toc(url)
    if os.path.exists('WSepub'):
        shutil.rmtree('WSepub')
    shutil.copytree(os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        'resources'), 'WSepub')
    cf = urllib2.urlopen(url)
    content = cf.read()
    content = content.replace('&#160;', ' ')
    content = re.sub(r'(\s+[a-z0-9]+)=([\'|\"]{0})([a-z0-9]+)([\'|\"]{0})',
                     r'\1="\3"',
                     content)
    tree = etree.fromstring(content)
    book = tree.xpath('//div[@id="mw-content-text"]')[0]
    if tree.xpath('//table[@class="infobox"]/tr[2]/td[1]')[0].text == 'Autor':
        try:
            bauthor = tree.xpath(
                '//table[@class="infobox"]/tr[2]/td[2]/a'
            )[0].text
        except:
            sys.exit('ERROR! Unable to find book author!')
    if tree.xpath('//table[@class="infobox"]/tr[3]/td[1]')[0].text == u'Tytuł':
        try:
            btitle = tree.xpath(
                '//table[@class="infobox"]/tr[3]/td[2]/a'
            )[0].text
        except:
            sys.exit('ERROR! Unable to find book title!')
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
        try:
            del s.attrib['style']
        except:
            pass
    font_size = {'1': '.63em', '2': '.82em', '3': '1em',
                 '4': '1.13em', '5': '1.5em', '6': '2em', '7': '3em'}
    for s in tree.xpath('//font'):
        if s.get('color'):
            if s.get('style'):
                s.attrib['style'] = s.attrib['style'] + ';color:' + \
                    s.attrib['color']
            else:
                s.attrib['style'] = 'color:' + s.attrib['color']
            del s.attrib['color']
        if s.get('size'):
            if s.get('style'):
                s.attrib['style'] = s.attrib['style'] + ';font-size:' + \
                    font_size[s.attrib['size']]
            else:
                s.attrib['style'] = 'font-size:' + font_size[s.attrib['size']]
            del s.attrib['size']
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
            s.attrib['style'] = 'width: ' + str(int(s.attrib['width'])/4) + \
                '%; margin-left:' + str((100-int(s.attrib['width'])/4)/2) + '%'
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
    bs = bs.replace(
        'id="Template_law" class="toccolours" style="border-width:1px 0 0 0"',
        'class="Template_law"'
    )
    bs = bs.replace('</p>', '</div>')
    tree = etree.fromstring(bs)
    for s in tree.xpath(
        '//xhtml:div[@class="thumb tright"]', namespaces=XHTMLNS
    ):
        s.getparent()[
            s.getparent().index(s)-1
        ].tail = s.getparent()[s.getparent().index(s)-1].tail + s.tail
        s.tail = ''
        if s.getparent()[
            s.getparent().index(s)+1
        ].tag == '{http://www.w3.org/1999/xhtml}br':
            s.getparent().insert(s.getparent().index(s), etree.fromstring(
                '<br/>'
            ))
            remove_node(s.getparent()[s.getparent().index(s)+1])
    for s in tree.xpath(
        '//xhtml:div[@class="thumb tleft"]', namespaces=XHTMLNS
    ):
        s.getparent()[
            s.getparent().index(s)-1
        ].tail = s.getparent()[s.getparent().index(s)-1].tail + s.tail
        s.tail = ''
        if s.getparent()[
            s.getparent().index(s)+1
        ].tag == '{http://www.w3.org/1999/xhtml}br':
            s.getparent().insert(s.getparent().index(s), etree.fromstring(
                '<br/>'
            ))
            remove_node(s.getparent()[s.getparent().index(s)+1])
    move_law(tree)
    build_toc_ncx(tree, rozlist)
    generate_inline_toc()
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
    bs = bs.replace('<font', '<span')
    bs = bs.replace('</font>', '</span>')
    bs = bs.replace('<div id="mw-content-text" lang="pl" dir="ltr" '
                    'class="mw-content-ltr">',
                    '<div id="mw-content-text">')
    with open(os.path.join("WSepub/OPS/Text/text.xhtml"), "w") as text_file:
        text_file.write(bs)
    generate_cover(bauthor, btitle)
    pack_epub(bauthor + ' - ' + btitle + '.epub', 'WSepub')


def main():
    if args.url.endswith('.txt'):
        with open(os.path.join(args.url), 'r') as f:
            urls = f.read().splitlines()
        for u in urls:
            print('Processing: ' + u)
            process_url(u)
    else:
        process_url(args.url)
    if len(sys.argv) == 1:
        print("* * *")
        print("* At least one of above optional arguments is required.")
        print("* * *")
    return 0

if __name__ == '__main__':
    sys.exit(main())
