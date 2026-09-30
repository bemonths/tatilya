"""Small HTML tree for source-owned structures; no JavaScript execution."""
from html.parser import HTMLParser


class Node:
    def __init__(self, tag='', attrs=(), parent=None):
        self.tag, self.attrs, self.parent, self.children = tag, dict(attrs), parent, []
    def find(self, tag=None, cls=None, **attrs):
        result = []
        for child in self.children:
            if isinstance(child, Node):
                if (tag is None or child.tag == tag) and (cls is None or cls in child.attrs.get('class', '').split()) and all(child.attrs.get(k) == v for k,v in attrs.items()):
                    result.append(child)
                result.extend(child.find(tag, cls, **attrs))
        return result
    def text(self):
        if self.tag in ('script', 'style'): return ''
        if self.tag == 'br': return '\n'
        content = ''.join(c.text() if isinstance(c, Node) else c for c in self.children)
        return '\n' + content + '\n' if self.tag in ('p', 'div', 'li') else content


class Tree(HTMLParser):
    VOID = {'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}
    def __init__(self, content):
        super().__init__(convert_charrefs=True)
        self.root = Node(); self.stack = [self.root]
        self.feed(content); self.close()
    def handle_starttag(self, tag, attrs):
        # The live site omits closing li/option tags. Apply their HTML implied ends.
        if tag in ('li', 'option'):
            boundary = ('ul','ol') if tag == 'li' else ('select',)
            for i in range(len(self.stack)-1,0,-1):
                if self.stack[i].tag in boundary: break
                if self.stack[i].tag == tag:
                    self.stack = self.stack[:i]; break
        n=Node(tag,attrs,self.stack[-1]);self.stack[-1].children.append(n)
        if tag not in self.VOID: self.stack.append(n)
    def handle_startendtag(self,tag,attrs):
        self.handle_starttag(tag,attrs)
        if tag not in self.VOID:self.handle_endtag(tag)
    def handle_endtag(self, tag):
        if tag == 'br':
            self.handle_starttag('br',());return
        for i in range(len(self.stack)-1,0,-1):
            if self.stack[i].tag == tag:
                self.stack=self.stack[:i];break
    def handle_data(self,data):self.stack[-1].children.append(data)
