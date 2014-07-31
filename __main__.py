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
from urllib import unquote
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
parser.add_argument("url", help="URL to WS book or TXT file with URLs")
args = parser.parse_args()


def strip_accents(text):
    return ''.join(c for c in unicodedata.normalize(
        'NFKD', text
    ) if unicodedata.category(c) != 'Mn')


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


def prepare_dir():
    if os.path.exists(os.path.join('WSepub')):
        shutil.rmtree(os.path.join('WSepub'))
    shutil.copytree(os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        'resources'), 'WSepub')


def get_dc_data(tree):
    for a in tree.xpath('//table[@class="infobox"]//a[@title]'):
        if 'całość' in a.get('title').encode('utf8').lower():
            all_url = a.get('href')
            break
        else:
            all_url = None
    # print(all_url)
    if tree.xpath(
        '//table[@class="infobox"]/tr[2]/td[1]'
    )[0].text == 'Autor':
        try:
            bauthor = tree.xpath(
                '//table[@class="infobox"]/tr[2]/td[2]/a'
            )[0].text
        except:
            sys.exit('ERROR! Unable to find book author!')
    if tree.xpath(
        '//table[@class="infobox"]/tr[3]/td[1]'
    )[0].text == u'Tytuł':
        try:
            btitle = tree.xpath(
                '//table[@class="infobox"]/tr[3]/td[2]'
            )[0].text
        except:
            sys.exit('ERROR! Unable to find book title!')
    return bauthor, btitle, all_url


def get_title_page_tree(fragment_url):
    tree = url_to_tree('https://pl.wikisource.org' + fragment_url)
    for s in tree.xpath('//div[contains(@style, "position:static")]'):
        remove_node(s)
    for s in tree.xpath('//div[@class="refsection"]'):
        remove_node(s)
    for s in tree.xpath('//h2/*[@id="Przypisy"]'):
        remove_node(s.getparent())
    return tree


def generate_cover(bauthor, btitle):
    cover = DefaultEbookCover
    cover_file = StringIO()
    bound_cover = cover(bauthor, btitle)
    bound_cover.save(cover_file)
    with open(os.path.join("WSepub/OPS/Images/cover.jpg"), "w") as coverf:
        coverf.write(cover_file.getvalue())


def write_dc_data(bauthor, btitle, url):
    parser = etree.XMLParser(remove_blank_text=True)
    opftree = etree.parse(os.path.join('WSepub/OPS/content.opf'), parser)
    ncxtree = etree.parse(os.path.join('WSepub/OPS/toc.ncx'), parser)
    if not isinstance(unquote(url), unicode):
        url = unquote(url).decode('utf-8')
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
    with open(os.path.join('WSepub/OPS/content.opf'), 'w') as f:
        f.write(etree.tostring(opftree.getroot(), pretty_print=True,
                standalone=False, xml_declaration=True, encoding='utf-8'))
    with open(os.path.join('WSepub/OPS/toc.ncx'), 'w') as f:
        f.write(etree.tostring(ncxtree.getroot(), pretty_print=True,
                standalone=False, xml_declaration=True, encoding='utf-8'))


def write_law(tree):
    parser = etree.XMLParser(remove_blank_text=True)
    infotree = etree.parse(os.path.join('WSepub/OPS/Text/info.xhtml'), parser)
    for s in tree.xpath(
        '//div[@id="Template_law"]/div/div[@style="float: left;"]'
    ):
        remove_node(s)
    for l in tree.xpath('//div[@id="Template_law"]'):
        infotree.xpath('//xhtml:div[@id="law"]',
                       namespaces=XHTMLNS)[0].append(l)
    for l in infotree.xpath('//div[@id="Template_law"]/div'):
        del l.attrib['style']
    for a in infotree.xpath('//div[@id="Template_law"]//a[@href]'):
        a.attrib['href'] = 'https://pl.wikisource.org' + a.get('href')
    for l in infotree.xpath('//div[@id="Template_law"]'):
        del l.attrib['style']
        del l.attrib['class']
        del l.attrib['id']
    with open(os.path.join('WSepub/OPS/Text/info.xhtml'), 'w') as f:
        f.write(etree.tostring(infotree.getroot(), pretty_print=True,
                standalone=False, xml_declaration=True, encoding='utf-8'))
    return tree


def split_hr(tree):
    for s in tree.xpath('//hr'):
        try:
            s.attrib['class'] = 'wsrozdzial'
        except:
            pass
    for s in tree.xpath('//table//hr'):
        try:
            del s.attrib['class']
        except:
            pass
    try:
        tree.xpath('//hr')[-1].attrib['class'] = 'hidden'
    except:
        print('Warning! No HR on title page.')
        pass
    return tree


def set_text_reference(doc):
    parser = etree.XMLParser(remove_blank_text=True)
    opftree = etree.parse(os.path.join('WSepub/OPS/content.opf'), parser)
    guide = opftree.xpath('//opf:guide', namespaces=OPFNS)[0]
    guide.append(etree.fromstring(
        '<reference type="text" title="Text" href="Text/text_%s.xhtml" />' %
        (doc)
    ))
    with open(os.path.join('WSepub/OPS/content.opf'), 'w') as f:
        f.write(etree.tostring(opftree.getroot(), pretty_print=True,
                standalone=False, xml_declaration=True, encoding='utf-8'))


def url_to_tree(url):
    content = urllib2.urlopen(url).read()
    content = content.replace('&#160;', ' ')
    content = re.sub(r'(\s+[a-z0-9]+)=([\'|\"]{0})([a-z0-9]+)([\'|\"]{0})',
                     r'\1="\3"',
                     content)
    return etree.fromstring(content)


def download_images(tree, url):
    doc = url.split('/')[-1]
    num = 1
    parser = etree.XMLParser(remove_blank_text=True)
    opftree = etree.parse(os.path.join('WSepub/OPS/content.opf'), parser)
    manifest = opftree.xpath('//opf:manifest', namespaces=OPFNS)[0]
    for i in tree.xpath('//img'):
        filext = os.path.splitext(i.get('src').split("/")[-1])[1]
        if filext == '.jpg':
            mime = 'image/jpeg'
        elif filext == '.png':
            mime = 'image/png'
        else:
            sys.exit('ERROR! Unrecognized image extension: ' + filext)
        urlretrieve('https:' + i.get('src'), os.path.join(
            'WSepub', 'OPS', 'Images', 'img_' + doc + '_' + str(num) + filext
        ))
        i.attrib['src'] = '../Images/img_' + doc + '_' + str(num) + filext
        opfitem = etree.fromstring(
            '<item id="img_%s_%s" href="Images/img_%s_%s%s" media-'
            'type="%s"/>' % (doc, num, doc, num, filext, mime))
        manifest.append(opfitem)
        num += 1
    with open(os.path.join('WSepub/OPS/content.opf'), 'w') as f:
        f.write(etree.tostring(opftree.getroot(), pretty_print=True,
                standalone=False, xml_declaration=True, encoding='utf-8'))


def next_url(tree):
    nurl = None
    for s in tree.xpath('//table[@class="infobox"]/tr[1]/td[1]//a[@href]'):
        if s.text == '>>>':
            nurl = 'https://pl.wikisource.org' + s.get('href')
    return nurl


def process_dirty_tree(tree):
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
    for s in tree.xpath('//div[@id="Template_law"]'):
        remove_node(s)
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

    return tree


def replace_align_attribute(tree):
    for t in tree.xpath('//xhtml:*[@align]', namespaces=XHTMLNS):
        if t.get('style'):
            t.attrib['style'] = t.attrib['style'] + ';text-align:' + \
                t.get('align')
        else:
            t.attrib['style'] = 'text-align:' + t.get('align')
        del t.attrib['align']
    return tree


def replace_width_attribute(tree):
    for t in tree.xpath('//xhtml:*[@width]', namespaces=XHTMLNS):
        if t.get('style'):
            t.attrib['style'] = t.attrib['style'] + ';width:' + \
                t.get('width')
        else:
            t.attrib['style'] = 'width:' + t.get('width')
        del t.attrib['width']
    return tree


def process_tree(string):
    tree = etree.fromstring(string)
    # for s in tree.xpath(
    #     '//xhtml:div[@class="thumb tright"]', namespaces=XHTMLNS
    # ):
    #     s.getparent()[
    #         s.getparent().index(s)-1
    #     ].tail = s.getparent()[s.getparent().index(s)-1].tail + s.tail
    #     s.tail = ''
    #     if s.getparent()[
    #         s.getparent().index(s)+1
    #     ].tag == '{http://www.w3.org/1999/xhtml}br':
    #         s.getparent().insert(s.getparent().index(s), etree.fromstring(
    #             '<br/>'
    #         ))
    #         remove_node(s.getparent()[s.getparent().index(s)+1])
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
    # build_toc_ncx(tree, rozlist)
    # generate_inline_toc()
    return tree


def regex_dirty_tree(tree, doc):
    bs = etree.tostring(
        tree,
        pretty_print=True,
        xml_declaration=True, encoding='utf-8', standalone=False, doctype=DTD
    )
    bs = bs.replace('<span/>', '')
    bs = bs.replace('href="#', 'href="text_%s.xhtml#' % (doc.encode('utf8')))
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
    return bs


def regex_tree(tree):
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
    return bs


def write_text_file(string, doc):
    with open(
            os.path.join("WSepub/OPS/Text/text_" + doc + ".xhtml"), "w"
    ) as text_file:
        text_file.write(string)


def write_ncx_opf_entry(doc, docu):
    parser = etree.XMLParser(remove_blank_text=True)
    opftree = etree.parse(os.path.join('WSepub/OPS/content.opf'), parser)
    ncxtree = etree.parse(os.path.join('WSepub/OPS/toc.ncx'), parser)
    manifest = opftree.xpath('//opf:manifest', namespaces=OPFNS)[0]
    spine = opftree.xpath('//opf:spine', namespaces=OPFNS)[0]
    nm = ncxtree.xpath('//ncx:navMap', namespaces=NCXNS)[0]
    nm.append(
        etree.fromstring(
            '<navPoint id="text_' + doc + '">'
            '<navLabel><text>' + docu.replace('_', ' ') + '</text></navLabel>'
            '<content src="Text/text_' + doc + '.xhtml" />'
            '</navPoint>'
        )
    )
    opfitem = etree.fromstring(
        '<item id="text_%s" href="Text/text_%s.xhtml" media-'
        'type="application/xhtml+xml"/>' % (doc, doc))
    manifest.append(opfitem)
    refitem = etree.fromstring('<itemref idref="text_%s"/>' % (doc))
    spine.append(refitem)
    with open(os.path.join('WSepub/OPS/content.opf'), 'w') as f:
        f.write(etree.tostring(opftree.getroot(), pretty_print=True,
                standalone=False, xml_declaration=True, encoding='utf-8'))
    with open(os.path.join('WSepub/OPS/toc.ncx'), 'w') as f:
        f.write(etree.tostring(ncxtree.getroot(), pretty_print=True,
                standalone=False, xml_declaration=True, encoding='utf-8'))


def move_info_toc_spine_ncx():
    parser = etree.XMLParser(remove_blank_text=True)
    opftree = etree.parse(os.path.join('WSepub/OPS/content.opf'), parser)
    ncxtree = etree.parse(os.path.join('WSepub/OPS/toc.ncx'), parser)
    nm = ncxtree.xpath('//ncx:navMap', namespaces=NCXNS)[0]
    spine = opftree.xpath('//opf:spine', namespaces=OPFNS)[0]
    spine.append(opftree.xpath('//opf:itemref[@idref="info"]',
                 namespaces=OPFNS)[0])
    spine.append(opftree.xpath('//opf:itemref[@idref="toc"]',
                 namespaces=OPFNS)[0])
    nm.append(ncxtree.xpath('//ncx:navPoint[@id="info"]',
              namespaces=NCXNS)[0])
    nm.append(ncxtree.xpath('//ncx:navPoint[@id="toc"]',
              namespaces=NCXNS)[0])
    with open(os.path.join('WSepub/OPS/content.opf'), 'w') as f:
        f.write(etree.tostring(opftree.getroot(), pretty_print=True,
                standalone=False, xml_declaration=True, encoding='utf-8'))
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


def pack_epub(bauthor, btitle):
    output_filename = bauthor + ' - ' + btitle + '.epub'
    source_dir = 'WSepub'
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


def normalize_doc_name(url):
    doc = url.split('/')[-1]
    docu = unquote(doc).decode('utf8')
    doc = strip_accents(unicode(docu))
    doc = doc.encode('utf8').replace('ł', 'l')
    doc = doc.replace('\xe2\x80\x94', '-')
    doc = re.sub(r'\W+', '', doc)
    return doc, docu


def main():
    prepare_dir()
    tree = url_to_tree(args.url)
    bauthor, btitle, all_url = get_dc_data(tree)
    print(bauthor, btitle)
    nurl = next_url(tree)
    if all_url:
        tree = get_title_page_tree(all_url)
    tree = split_hr(tree)
    doc, docu = normalize_doc_name(args.url)
    set_text_reference(doc)
    print(nurl)
    write_dc_data(bauthor, btitle, args.url)
    tree = write_law(tree)
    generate_cover(bauthor, btitle)
    tree = process_dirty_tree(tree)
    download_images(tree, doc)
    string = regex_dirty_tree(tree, doc)
    tree = process_tree(string)
    tree = replace_align_attribute(tree)
    tree = replace_width_attribute(tree)
    string = regex_tree(tree)
    write_text_file(string, doc)
    write_ncx_opf_entry(doc, docu)
    while nurl is not None:
        tree = url_to_tree(nurl)
        doc, docu = normalize_doc_name(nurl)
        nurl = next_url(tree)
        tree = process_dirty_tree(tree)
        download_images(tree, doc)
        string = regex_dirty_tree(tree, doc)
        tree = process_tree(string)
        tree = replace_align_attribute(tree)
        tree = replace_width_attribute(tree)
        string = regex_tree(tree)
        write_text_file(string, doc)
        write_ncx_opf_entry(doc, docu)
        print(nurl)
    move_info_toc_spine_ncx()
    generate_inline_toc()
    pack_epub(bauthor, btitle)
    if os.path.exists(os.path.join('WSepub')):
        shutil.rmtree(os.path.join('WSepub'))
    if len(sys.argv) == 1:
        print("* * *")
        print("* At least one of above optional arguments is required.")
        print("* * *")
    return 0

if __name__ == '__main__':
    sys.exit(main())
