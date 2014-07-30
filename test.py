from lxml import etree

a = '<font style="display:block">test</font>'
tree = etree.fromstring(a)
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

print(etree.tostring(tree))
