#!/usr/bin/env python3.9
import functools, os, sys, re
from operator import xor

def m(pattern, string):
    match = re.match(pattern, string)
    if not match:
        return None
    if(match.group(0) != string):
        die(f'Pattern /{pattern}/ matched only part of string')
    ret = []
    for index in range((match.lastindex or 0)+1):
        ret.append(match.group(index))
    return ret

def die(reason):
    sys.stderr.write(reason+'\n')
    sys.exit(1)

def getInputLines():
    while True:
        line = sys.stdin.readline()
        if not line:
            break
        yield line

def nextOrDie(inputGenerator, message='Unexpected stop of generator'):
    try:
        return next(inputGenerator)
    except StopIteration:
        die(message)

def parseDiff(inputLines):
    filePrefix=None
    fileFormat=None
    fileKey=None
    betweenHeaderAndFirstHunk=False
    for line in inputLines:
        linem = m(r'^(\|?)@@ +-([0-9]+)(,[0-9]+)? +(\^*[0-9]+\\? +)?\+([0-9]+)(,[0-9]+)? +@@(.*)\n$', line)
        if(linem):
            prefix = linem[1]
            if prefix!=filePrefix: die('[HDF31] Hunk header prefix did not match previous line')
            leftstartlineraw = linem[2]
            leftlinecountraw = linem[3]
            hintfulextensionraw = linem[4]
            rightstartlineraw = linem[5]
            rightlinecountraw = linem[6]
            comment = linem[7]
            leftstartline = int(leftstartlineraw)
            rightstartline = int(rightstartlineraw)
            leftlinecount = int(leftlinecountraw[1:] if leftlinecountraw else '1')
            rightlinecount = int(rightlinecountraw[1:] if rightlinecountraw else '1')
            [snippetcolumncountraw, hunklinecountraw, newlinemarkersraw] = [None, None, None]
            if hintfulextensionraw:
                [_, snippetcolumncountraw, hunklinecountraw, newlinemarkersraw] = m(r'(\^*)([0-9]+)(\\?) +', hintfulextensionraw)
            hunklinecount = int(hunklinecountraw) if hunklinecountraw else None
            hunktype = 'hintful' if hunklinecountraw else 'unified'
            snippetcolumncount = len(snippetcolumncountraw) if snippetcolumncountraw else 0
            newlinemarkers = bool(newlinemarkersraw)
            hunkKey = (fileKey, leftstartline, leftlinecount, rightstartline, rightlinecount)
            extraFields = {'fileformat': fileFormat, 'filekey': fileKey, 'hunkkey': hunkKey}
            hunkheader = {
                'op': 'beginhunk',
                'prefix': prefix,
                **extraFields,
                'leftstartlineraw': leftstartlineraw,
                'leftlinecountraw': leftlinecountraw,
                'hunklinecountraw': hunklinecountraw,
                'rightstartlineraw': rightstartlineraw,
                'rightlinecountraw': rightlinecountraw,
                'comment': comment,
                'leftstartline': leftstartline,
                'rightstartline': rightstartline,
                'leftlinecount': leftlinecount,
                'rightlinecount': rightlinecount,
                'hunklinecount': hunklinecount,
                'hunktype': hunktype,
                'snippetcolumncount': snippetcolumncount,
                'newlinemarkers': newlinemarkers,
            }
            yield hunkheader
            if(hunktype=='hintful'):
                yield from parseHintfulHunk(hunkheader, inputLines, extraFields)
            else:
                yield from parseUnifiedHunk(hunkheader, inputLines, extraFields)
            betweenHeaderAndFirstHunk=False
            continue
        linem = m(r'^(\|?)--- ([^\r]*)\r*\n$', line)
        if(linem):
            if linem[1]!=filePrefix: die('[HDF31] Prefix for --- line did not match previous line')
            line2 = nextOrDie(inputLines, '[HDF22] Expected a +++ line but got end of file')
            line2m = m(r'^(\|?)\+\+\+ ([^\r]*)\r*\n$', line2)
            if not line2 or not line2m:
                die('[HDF22] Expected a +++ line')
            if not (linem[1]==line2m[1]):
                die('[HDF31] Prefix for +++ line did not match previous line')
            yield {
                'op': 'labels',
                'prefix': linem[1],
                'filekey': fileKey,
                'left': linem[2],
                'right': line2m[2],
                }
            continue
        linem = m(r'^(\|?)similarity index ([0-9]+%)\r*\n$', line)
        if(linem):
            if linem[1]!=filePrefix: die('[HDF31] Prefix for similarity line did not match previous line')
            yield {
                'op': 'similarity-index',
                'prefix': linem[1],
                'filekey': fileKey,
                'similarity-index': linem[2],
                }
            continue
        linem = m(r'^(\|?)rename from ([^\r]*)\r*\n$', line)
        if(linem):
            if linem[1]!=filePrefix: die('[HDF31] Prefix for rename from line did not match previous line')
            line2 = nextOrDie(inputLines, '[HDF22] Expected "rename to" line but got end of file')
            line2m = m(r'^(\|?)rename to ([^\r]*)\r*\n$', line2)
            if not line2 or not line2m:
                die('[HDF22] Expected "rename to" line')
            if not (linem[1]==line2m[1]):
                die('[HDF31] Prefix for "rename to" line must match that of "rename from" line')
            yield {
                'op': 'rename',
                'prefix': linem[1],
                'filekey': fileKey,
                'left': linem[2],
                'right': line2m[2],
                }
            continue
        if(m(r'^\|?([.=]*[-+ _#]|[,^$]+:).*\n$', line)):
            die(f'[HDF21] Hunk content without header: {line}')
        linem = m(r'^(\|?)index ([0-9a-f]{7,})\.\.([0-9a-f]{7,})( +[0-7]{6})?\r*\n$', line)
        if(linem):
            if linem[1]!=filePrefix: die('[HDF31] Prefix for index line did not match previous line')
            yield {
                'op': 'index',
                'prefix': linem[1],
                'filekey': fileKey,
                'left': linem[2],
                'right': linem[3],
                'mode': linem[4] if len(linem)==5 else None,
                }
            continue
        linem = m(r'^(\|?)(new|deleted) file mode ([^\r]*)\r*\n$', line)
        if(linem):
            if linem[1]!=filePrefix: die(f'[HDF31] Prefix for {linem[2]} file mode line did not match previous line')
            side={'deleted': 'left', 'new': 'right'}[linem[2]]
            yield {
                'op': f'{side}filemode',
                'prefix': linem[1],
                'filekey': fileKey,
                'mode': linem[3],
            }
            continue
        linem = m(r'^(\|?)diff --(git|hintful) ([^ ]+) +([^ \r]+)\r*\n$', line)
        if(linem):
            if(filePrefix!=None):
                yield {
                    'op': 'endfile',
                    'prefix': filePrefix,
                    'filekey': fileKey,
                }
            filePrefix=linem[1]
            fileFormat=linem[2]
            fileKey=(linem[3], linem[4])
            yield {
                'op': 'beginfile',
                'prefix': filePrefix,
                'filekey': fileKey,
                'fileformat': fileFormat,
                'leftfile': linem[3],
                'rightfile': linem[4],
            }
            betweenHeaderAndFirstHunk=True
            continue
        if(betweenHeaderAndFirstHunk):
            die(f"[HDF22] Cannot parse extended header line '{line}'")
        else:
            die(f"[HDF21] Cannot parse line '{line}'")
    if(filePrefix!=None):
        yield {
            'op': 'endfile',
            'prefix': filePrefix,
            'filekey': fileKey,
        }

def glueNonewline(inputLines):
    prevLine = ''
    for line in inputLines:
        linem = m(r'^(\|?)\\.*\n$', line)
        if(linem):
            prevLinem = m(r'^(\|?).*\n$', prevLine)
            if(prevLinem[1]!=linem[1]):
                die(r'[HDF31] Prefix before "\ No newline at end of file" must match the previous line')
            yield prevLine + line
            prevLine = ''
        else:
            if prevLine:
                yield prevLine
            prevLine = line
    if prevLine:
        yield prevLine

def parseUnifiedHunk(header, inputLines, extraFields):
    leftlinecount = header['leftlinecount']
    rightlinecount = header['rightlinecount']
    leftcontent = ''
    rightcontent = ''
    while(0 < leftlinecount or 0 < rightlinecount):
        if(leftlinecount < 0 or rightlinecount < 0):
            die('[HDF11] Corrupt hunk line count')
        line = nextOrDie(inputLines, '[HDF11] End of file inside unified hunk')
        linem = m(r'^(\|?)([-+ ])(.*)\n\|?\\ .*\n$', line) or m(r'^(\|?)([-+ ])(.*\n)$', line)
        if linem:
            prefix = linem[1]
            if prefix!=header['prefix']:
                die(f'[HDF31] Expected prefix for unified content line to match previous line')
            opchar = linem[2]
            content = linem[3]
            yield {
                'op': {'-': 'leftcontent', '+': 'rightcontent', ' ': 'bothcontent'}[opchar],
                'prefix': prefix,
                'content': content,
                'snippetshavecontent': [],
                **extraFields,
            }
            if(opchar in '- '):
                leftlinecount-=1
                leftcontent+=content
            if(opchar in '+ '):
                rightlinecount-=1
                rightcontent+=content
            continue
        die(f'[HDF12] Corrupt hunk, contained line: {line}')
    yield {
        'op': 'endhunk',
        'prefix': header['prefix'],
        'leftcontent': leftcontent,
        'rightcontent': rightcontent,
        **extraFields,
    }

def parseHintfulHunk(header, inputLines, extraFields):
    state={
        'leftcontent': '',
        'rightcontent': '',
        'snippets': [{'name':'', 'content':'', 'index':x} for x in range(header['snippetcolumncount'])],
    }
    cc=header['snippetcolumncount']
    nlm=header['newlinemarkers']
    for _ in range(header['hunklinecount']):
        line = nextOrDie(inputLines, '[HDF11] End of file inside hintful hunk')
        if m(r'^(\|?)([.=]{'+str(cc)+r'})([-+ _#])(.*)\n\|?\\ .*\n$', line):
            die('[HDF17] Encountered `\ No newline at end of file` syntax in hintful hunk')
        linem = m(r'^(\|?)([.=]{'+str(cc)+r'})([-+ _#])(.*)('+(r'[$\\]' if nlm else '')+')(\r*\n)$', line)
        if(linem):
            prefix = linem[1]
            if prefix!=header['prefix']:
                die(f'[HDF31] Expected prefix for hintful content line to match previous line')
            snippetindicators = linem[2]
            opchar = linem[3]
            content = linem[4]
            nlmarker = linem[5]
            crlf = linem[6]
            if(nlmarker=='$'):
                if(content.endswith('\r')):
                    die('[HDF16] CR character not allowed before $ newline marker')
                content += crlf
            if(nlmarker==''):
                content += crlf
            op = {'-': 'leftcontent', '+': 'rightcontent', ' ': 'bothcontent', '_': 'bothlowprioritycontent', '#': 'ignorecontent'}[opchar]
            snippetshavecontent = [ x=='=' for x in snippetindicators ]
            yield {
                'op': op,
                'prefix': prefix,
                'content': content,
                'snippetshavecontent': snippetshavecontent,
                **extraFields,
            }
            for side in ['left', 'right']:
                if(op in [f'{side}content', 'bothcontent', 'bothlowprioritycontent']):
                    if(state[f'{side}content'].endswith('\r') and m(r'^\r*\n', content)):
                        die(r'[HDF16] \r*\n sequence must not be split.')
                    state[f'{side}content']+=content
            for snippet in state['snippets']:
                if(snippetshavecontent[snippet['index']]):
                    if(not snippet['name']):
                        die('[HDF14] Equals sign (`=`) in inactive snippet column.')
                    if(snippet['content'].endswith('\r') and m(r'^\r*\n', content)):
                        die(r'[HDF16] \r*\n sequence must not be split.')
                    snippet['content']+=content
            continue
        linem = m(r'^(\|?)([,^]{'+str(cc)+r'}):([^\r]*)\r*\n$', line)
        if(linem):
            prefix = linem[1]
            if prefix!=header['prefix']:
                die(f'[HDF31] Expected prefix for hintful snippet line to match previous line')
            snippetindicators = linem[2]
            name = linem[3]
            if(m(r',{'+str(cc)+r'}', snippetindicators)):
                if(name==''):
                    die('[HDF12] Snippet deactivation line must have at least one dollar sign.')
                else:
                    die('[HDF12] Snippet activation line must have at least one caret sign.')
            if(name==''):
                die('[HDF12] Snippet activation line must have a non-empty snippet name.')
            for snippet in state['snippets']:
                if(snippetindicators[snippet['index']]=='^'):
                    if snippet['name']:
                        yield {
                            'op': f'endsnippet',
                            'prefix': prefix,
                            'name': snippet['name'],
                            'content': snippet['content'],
                            **extraFields,
                        }
                    snippet['name']=name
                    snippet['content']=''
            yield {
                'op': 'activatesnippets',
                'prefix': prefix,
                'name': name,
                'snippetcolumns': [ x=='^' for x in snippetindicators ],
                **extraFields,
            }
            continue
        linem = m(r'^(\|?)([,$]{'+str(cc)+r'}):\r*\n$', line)
        if(linem):
            prefix = linem[1]
            snippetindicators = linem[2]
            for snippet in state['snippets']:
                if(snippetindicators[snippet['index']]=='$'):
                    if snippet['name']:
                        yield {
                            'op': f'endsnippet',
                            'prefix': prefix,
                            'name': snippet['name'],
                            'content': snippet['content'],
                            **extraFields,
                        }
                    snippet['name']=''
                    snippet['content']=''
            yield {
                'op': 'deactivatesnippets',
                'prefix': prefix,
                'name': name,
                'snippetcolumns': [ x=='$' for x in snippetindicators ],
                **extraFields,
            }
            continue
        die(f'[HDF12] Corrupt hunk: Strange line: {line}')
    for snippet in state['snippets']:
        if snippet['name']:
            yield {
                'op': f'endsnippet',
                'prefix': prefix,
                'name': snippet['name'],
                'snippetcolumn': snippet['index'],
                'content': snippet['content'],
                **extraFields,
            }
    yield {
        'op': 'endhunk',
        'prefix': header['prefix'],
        **extraFields,
        'leftcontent': state['leftcontent'],
        'rightcontent': state['rightcontent'],
    }

def formatDiffHelper(inputObjs, task="raw"):
    if(task not in ["raw", "highlight", "visualize"]):
        die(f"Bad task {task} in formatDiffHelper")
    def interpretAndColorize(inputObjs):
        hunktype=None
        seenPrefixedHunks=set()
        suppressed=False
        fileKey=None
        cc=None
        nlm=None
        palette=[None, "black", "red", "yellow", "green", "blue", "magenta", "grey", "lightred", "lightyellow", "lightgreen", "lightblue", "lightmagenta", "lightgrey"]
        snippetcolors=["lightyellow", "lightblue"]
        bar='' if task=="raw" else {'op': 'bar'}
        def colorize(fg=None, bold=False, bg=None, bg2=None):
            if(task=="raw"): return ''
            if(suppressed):
                return {
                    'op': 'colorize',
                    'fg': "lightgrey",
                    'bold': False,
                    'bg': None,
                    'bg2': None,
                }
            if(fg not in palette): die(f'Illegal fg color {fg}')
            if(bg not in palette): die(f'Illegal bg color {bg}')
            if(bg2 not in palette): die(f'Illegal bg2 color {bg2}')
            if(bold not in [True, False]): die(f'Illegal bold value {bold}')
            return {
                'op': 'colorize',
                'fg': fg,
                'bold': bold,
                'bg': bg,
                'bg2': bg2,
            }
        for obj in inputObjs:
            op=obj['op']
            prefix=[colorize(fg="grey"), obj['prefix'], colorize()] if obj['prefix'] else []
            if(op=='beginhunk'):
                hunkKey=(*fileKey,
                         obj['leftstartline'],
                         obj['leftlinecount'],
                         obj['rightstartline'],
                         obj['rightlinecount'],
                         )
                hunktype=obj['hunktype']
                if(obj['prefix']):
                    seenPrefixedHunks.add(hunkKey)
                    suppressed=False
                elif(hunkKey in seenPrefixedHunks):
                    suppressed=True
                else:
                    suppressed=False
                cc=obj['snippetcolumncount']
                nlm=obj['newlinemarkers']
                yield from [
                    *prefix,
                    colorize(fg="magenta", bold=True),
                    '@@ -',
                    obj['leftstartlineraw'],
                    obj['leftlinecountraw'] or '',
                ]
                if(hunktype=='hintful'):
                    yield from [
                        ' ',
                        '^' * obj['snippetcolumncount'],
                        str(obj['hunklinecount']),
                        '\\' if obj['newlinemarkers'] else '',
                    ]
                yield from [
                    ' +',
                    obj['rightstartlineraw'],
                    obj['rightlinecountraw'] or '',
                    ' @@',
                    obj['comment'],
                    '\n',
                ]
            elif(op.endswith('content')):
                yield from prefix
                if not(task=="visualize" and hunktype=="hintful"):
                    for snippetindex in range(cc):
                        if obj['snippetshavecontent'][snippetindex]:
                            yield from [
                                colorize(fg=['yellow', 'blue'][snippetindex]),
                                '=',
                            ]
                        else:
                            yield from [
                                colorize(fg='grey'),
                                '.'
                            ]
                [                              char,    charfgcolor, barcolor, contentfgcolor, contentbgcolor]={
                    'leftcontent':            ['-',     "red",       "red",    None,           "lightred"],
                    'rightcontent':           ['+',     "green",     "green",  None,           "lightgreen"],
                    'bothcontent':            [' ',     None,        "grey",   None,           None],
                    'bothlowprioritycontent': ['_',     "grey",      "grey",   "grey",         None],
                    'ignorecontent':          ['#',     "grey",      "grey",   None,           "lightgrey"],
                }[op]
                if not(task=="visualize" and hunktype=="hintful"):
                    yield colorize(fg=charfgcolor)
                    yield char
                    if not suppressed:
                        yield colorize(fg=barcolor)
                        yield bar
                content = obj['content']
                if(hunktype=='unified'):
                    yield colorize(fg=contentfgcolor, bg=contentbgcolor)
                    yield obj['content']
                    if not obj['content'].endswith('\n'):
                        yield from [
                            '\n',
                            colorize(fg="grey"),
                            '\\',
                            bar,
                            colorize(fg="grey", bg=contentbgcolor),
                            ' No newline at end of file\n',
                            ]
                elif(hunktype=='hintful'):
                    underlinecolor=None
                    for idx, x in enumerate(obj['snippetshavecontent']):
                        if(x):
                            if(op=="ignorecontent" and contentbgcolor=="lightgrey"):
                                contentbgcolor=snippetcolors[idx]
                            elif(underlinecolor==None):
                                underlinecolor=snippetcolors[idx]
                            else:
                                die('Cannot highlight or visualize content for more than two targets.')
                    yield colorize(fg=contentfgcolor, bg=contentbgcolor, bg2=underlinecolor)
                    if nlm:
                        if content.endswith('\n'):
                            contentm = m(r'^(.*[^\r])?(\r*\n)$', content)
                            yield from [
                                contentm[1] or '',
                                colorize(fg="magenta", bold=True, bg=contentbgcolor, bg2=underlinecolor),
                                '$',
                                contentm[2],
                                ]
                        else:
                            yield content
                            if not(task=="visualize" and hunktype=="hintful"):
                                yield from [
                                    colorize(fg="magenta", bold=True, bg=contentbgcolor, bg2=underlinecolor),
                                    '\\\n',
                                ]
                    else:
                        if contents.endswith('\n'):
                            yield content
                        else:
                            die('Content must end with newline in hintful mode without newline marker')
                else:
                    die('Unexpected hunk type')
            elif(op=='activatesnippets'):
                if(task=="visualize" and hunktype=="hintful"):
                    for idx, x in enumerate(obj['snippetcolumns']):
                        if(x):
                            yield from [
                                colorize(fg=snippetcolors[idx], bg="black", bold=True),
                                ':',
                                obj['name'],
                            ]
                else:
                    yield from prefix
                    onecolor=None
                    for idx, x in enumerate(obj['snippetcolumns']):
                        if(x):
                            yield from [
                                colorize(fg=snippetcolors[idx], bg="black", bold=True),
                                '^',
                            ]
                            if(onecolor):
                                onecolor="too many"
                            else:
                                onecolor=snippetcolors[idx]
                        else:
                            yield from [
                                colorize(fg="grey", bg="black"),
                                ',',
                            ]
                    yield from [
                        colorize(fg="lightgrey" if onecolor in [None, "too many"] else onecolor, bg="black", bold=True),
                        ':',
                        bar,
                        obj['name'],
                        '\n',
                    ]
            elif(op=='deactivatesnippets'):
                if(task=="visualize" and hunktype=="hintful"):
                    yield { 'op': 'beginGlueContent' }
                    for idx, x in enumerate(obj['snippetcolumns']):
                        if(x):
                            yield from [
                                colorize(fg=snippetcolors[idx], bg="black", bold=True),
                                ':',
                            ]
                    yield { 'op': 'endGlueContent' }
                else:
                    yield from prefix
                    onecolor=None
                    for idx, x in enumerate(obj['snippetcolumns']):
                        if(x):
                            yield from [
                                colorize(fg=snippetcolors[idx], bg="black", bold=True),
                                '$',
                            ]
                            if(onecolor):
                                onecolor="too many"
                            else:
                                onecolor=snippetcolors[idx]
                        else:
                            yield from [
                                colorize(fg="grey", bg="black"),
                                ',',
                            ]
                    yield from [
                        colorize(fg="lightgrey" if onecolor in [None, "too many"] else onecolor, bg="black", bold=True),
                        ':',
                        bar,
                        '\n',
                    ]
            elif(op=='endsnippet'):
                pass
            elif(op=='endhunk'):
                hunktype=None
                cc=None
                nlm=None
            elif(op=='endfile'):
                pass
            elif(op in ['labels']):
                yield from [
                    *prefix,
                    colorize(fg="red", bold=True),
                    f"--- {obj['left']}\n",
                    *prefix,
                    colorize(fg="green", bold=True),
                    f"+++ {obj['right']}\n",
                ]
            elif(op=='beginfile'):
                suppressed=False
                fileKey=(obj['leftfile'], obj['rightfile'])
                yield from [
                    *prefix,
                    colorize(bold=True),
                    f"diff --{obj['fileformat']} {obj['leftfile']} {obj['rightfile']}\n",
                ]
            elif(op=='index'):
                yield from [
                    *prefix,
                    colorize(bold=True),
                    f"index {obj['left']}..{obj['right']}",
                    obj['mode'] if obj['mode'] else '',
                    '\n',
                ]
            elif(op.endswith('filemode')):
                yield from [
                    *prefix,
                    colorize(fg={'leftfilemode': 'red', 'rightfilemode': 'green'}[op], bold=True),
                    {'leftfilemode': 'deleted', 'rightfilemode': 'new'}[op],
                    ' file mode ',
                    obj['mode'],
                    '\n',
                ]
            elif(op=='similarity-index'):
                yield from [
                    *prefix,
                    f"similarity index {obj['similarity-index']}\n",
                ]
            elif(op=='rename'):
                yield from [
                    *prefix,
                    colorize(bold=True),
                    f"rename from {obj['left']}\n",
                    *prefix,
                    colorize(bold=True),
                    f"rename to {obj['right']}\n",
                ]
            else:
                die(f'formatDiffHelper cannot process operation {op}')
    def separateNewlines(inputObjs):
        for obj in inputObjs:
            if(type(obj)==str and '\n' in obj):
                while('\n' in obj):
                    i=obj.index('\n')
                    yield obj[:i]
                    yield '\n'
                    obj=obj[i+1:]
            yield obj
    def processNewlineDeferment(inputObjs):
        gluecontent=False
        deferred=""
        prevObj=None
        for obj in inputObjs:
            if(obj==''):
                continue
            elif(type(obj)==dict and obj['op']=='beginGlueContent'):
                if(type(prevObj)==dict and prevObj['op']=='endGlueContent'):
                    prevObj=None
                elif(prevObj=='\n'):
                    deferred+=prevObj
                    prevObj=None
                    gluecontent=True
                else:
                    gluecontent=True
            else:
                if(type(prevObj)==dict and prevObj['op']=='endGlueContent'):
                    yield deferred
                    deferred=""
                elif(prevObj):
                    yield prevObj
                prevObj=obj
        if(type(prevObj)==dict and prevObj['op']=='endGlueContent'):
            yield deferred
            deferred=""
        elif(prevObj):
            yield prevObj
        if(deferred):
            die('processNewlineDeferment ended before inserting deferred newlines')
    def processColorizationEndAtNewline(inputObjs):
        for obj in inputObjs:
            if(obj=='\n' and task!="raw"):
                yield {
                    'op': 'colorize',
                    'fg': None,
                    'bold': False,
                    'bg': None,
                    'bg2': None,
                }
            yield obj
    yield from processColorizationEndAtNewline(processNewlineDeferment(separateNewlines(interpretAndColorize(inputObjs))))

def formatDiff(inputObjs):
    yield from formatDiffHelper(inputObjs, "raw")

def removeSnippets(inputObjs):
    for obj in inputObjs:
        op=obj['op']
        if(op=='ignorecontent' and True in obj['snippetshavecontent']):
            pass
        elif(op.endswith('content')):
            yield {
                **obj,
                'snippetshavecontent': [],
            }
        elif(op in ['activatesnippets', 'deactivatesnippets', 'endsnippet']):
            pass
        elif(op in ['beginfile', 'endfile', 'index', 'labels', 'leftfilemode', 'rightfilemode', 'similarity-index', 'rename', 'beginhunk', 'endhunk']):
            yield obj
        else:
            die(f'removeSnippets cannot process operation {op}')

def convertUnprefixedHunksToUnified(inputObjs):
    state={
        'leftcontent': '',
        'rightcontent': '',
        'bothcontent': '',
        'leftended': False,
        'rightended': False,
    }
    def checkInvariants():
        error1 = (state['bothcontent'] and (state['leftcontent'] or state['rightcontent']))
        error2 = (state['leftended'] and (state['leftcontent'] or state['bothcontent']))
        error3 = (state['rightended'] and (state['rightcontent'] or state['bothcontent']))
        if (error1 or error2 or error3):
            die('Broken invariant in convertUnprefixedHunksToUnified')
    for obj in inputObjs:
        if(obj['prefix']):
            yield obj
            continue
        op=obj['op']
        content=obj['content'] if op.endswith('content') else None
        checkInvariants()
        for var in ['leftcontent', 'rightcontent', 'bothcontent']:
            while('\n' in state[var]):
                lines=state[var].split('\n')
                yield {
                    'op': var,
                    'prefix': '',
                    'content': lines[0]+'\n',
                    'snippetshavecontent': [],
                }
                state[var]='\n'.join(lines[1:])
        checkInvariants()
        if(op=='beginhunk'):
            yield {**obj, 'fileformat': 'git', 'hunktype': 'unified', 'snippetcolumncount': 0}
        elif(op=='beginfile'):
            yield {**obj, 'fileformat': 'git'}
        elif(op in ['activatesnippets', 'deactivatesnippets', 'endsnippet']):
            pass
        elif(op.endswith('content')):
            l=(op in ['leftcontent', 'bothcontent', 'bothlowprioritycontent'])
            r=(op in ['rightcontent', 'bothcontent', 'bothlowprioritycontent'])
            if(state['bothcontent'] and xor(l, r)):
                state['leftcontent']=state['bothcontent']
                state['rightcontent']=state['bothcontent']
                state['bothcontent']=''
            if(l and r and not (state['leftcontent'] or state['rightcontent'])):
                state['bothcontent']+=content
            else:
                if l:
                    state['leftcontent']+=content
                if r:
                    state['rightcontent']+=content
        elif(op=='endhunk'):
            for var in ['leftcontent', 'rightcontent', 'bothcontent']:
                if(state[var]):
                    yield {
                        'op': var,
                        'prefix': '',
                        'content': state[var],
                    }
                    state[var]=''
                    if(var in ['leftcontent', 'bothcontent']):
                        state['leftended']=True
                    if(var in ['rightcontent', 'bothcontent']):
                        state['rightended']=True
            yield obj
        elif(op=='endfile'):
            state['leftended']=False
            state['rightended']=False
            yield obj
        elif(op in ['index', 'labels', 'leftfilemode', 'rightfilemode', 'similarity-index', 'rename']):
            yield obj
        else:
            die(f'convertUnprefixedHunksToUnified cannot process operation {op}')

def switchleftright(text):
    if(text.startswith('left')): return 'right'+text[4:]
    if(text.startswith('right')): return 'left'+text[5:]
    return text

def reverse(inputObjs):
    for obj in inputObjs:
        yield {
            switchleftright(key):
            switchleftright(obj['op']) if key=='op' else obj[key]
            for key in obj
        }

def validateSnippets(inputObjs):
    snippetcache={}
    for obj in inputObjs:
        op=obj['op']
        if(op=='endsnippet'):
            name=obj['name']
            content=obj['content']
            if(name in snippetcache and snippetcache[name]!=content):
                die(f"[HDF15] Content of snippet '{name}' did not match previous use")
            snippetcache[name]=content
        yield obj

def groupHunks(inputObjs):
    for obj in inputObjs:
        if(obj['op']=='beginhunk'):
            beginHunk=obj
            contents=[]
            endHunk=None
            while True:
                contentObj=nextOrDie(inputObjs)
                if(contentObj['prefix']!=beginHunk['prefix']):
                    die('[HDF31] Prefix mismatch')
                if(contentObj['op']=='endhunk'):
                    endHunk=contentObj
                    break
                contents.append(contentObj)
            yield {**beginHunk, 'op': 'hunk', 'contents': contents, 'endhunk': endHunk}
        else:
            yield obj

def ungroupHunks(inputObjs):
    for obj in inputObjs:
        if(obj['op']=='hunk'):
            beginHunk={**obj, 'op': 'beginhunk'}
            del beginHunk['contents']
            del beginHunk['endhunk']
            yield beginHunk
            prefix=beginHunk['prefix']
            for contentObj in obj['contents']:
                yield {**contentObj, 'prefix': prefix}
            yield {**obj['endhunk'], 'prefix': prefix}
        else:
            yield obj

def groupFiles(inputObjs):
    for obj in inputObjs:
        if(obj['op']=='beginfile'):
            beginFile=obj
            contents=[]
            while True:
                contentObj=nextOrDie(inputObjs)
                if(contentObj['prefix']!=beginFile['prefix']):
                    die('[HDF31] Prefix mismatch')
                if(contentObj['op']=='endfile'):
                    break
                contents.append(contentObj)
            yield {**beginFile, 'op': 'file', 'contents': contents}
        else:
            yield obj

def ungroupFiles(inputObjs):
    for obj in inputObjs:
        if(obj['op']=='file'):
            beginFile={**obj, 'op': 'beginfile'}
            del beginFile['contents']
            yield beginFile
            prefix=beginFile['prefix']
            fileFormat=beginFile['fileformat']
            for contentObj in obj['contents']:
                yield {**contentObj, 'prefix': prefix, 'fileformat': fileFormat}
            yield {'op': 'endfile', 'prefix': prefix}
        else:
            yield obj

def duplicateFilesForCompat(inputObjs):
    for obj in inputObjs:
        if(obj['op']!='file'):
            die(f'duplicateFilesForCompat expects only file objects, got unexpected {obj["op"]}')
        if(obj['prefix']):
            die('duplicateFilesForCompat expects only unprefixed files')
        yield {**obj, 'prefix': '|', 'fileformat': 'hintful'}
        yield {**obj, 'fileformat': 'git'}

def convertHunksToHintful(inputObjs, onlyPrefixed=False):
    for obj in inputObjs:
        if(obj['op']=='beginfile' and (not onlyPrefixed or obj['prefix'])):
            yield {**obj, 'fileformat': 'hintful'}
        elif(obj['op']=='hunk' and (not onlyPrefixed or obj['prefix'])):
            hunklinecount = len(obj['contents'])
            yield {
                **obj,
                'fileformat': 'hintful',
                'hunklinecount': hunklinecount,
                'hunklinecountraw': str(hunklinecount),
                'hunktype': 'hintful',
                'newlinemarkers': bool(filter(lambda x: x['op'].endswith('content') and not x['content'].endswith('\n'),
                                              obj['contents'])),
            }
        else:
            yield obj
def convertPrefixedHunksToHintful(inputObjs):
    yield from convertHunksToHintful(inputObjs, True)

def removeEverythingPrefixed(inputObjs):
    for obj in inputObjs:
        if not obj['prefix']:
            yield obj

def validateFilesAndHunks(inputObjs):
    state={}
    fileCache={}
    hunkCache={}
    endHunkCache={}
    indexCache={}
    labelsCache={}
    lastHunk={}
    for obj in inputObjs:
        op=obj['op']
        if(op=='beginfile'):
            state['leftallowed']=True
            state['rightallowed']=True
            k=obj['filekey']
            if k in fileCache:
                oldObj=fileCache[k]
                if not oldObj['prefix'] or obj['prefix']:
                    die('[HDF33] Duplicate files can only be first a prefixed and then an unprefixed.')
            fileCache[k]=obj
        if(op=='index'):
            k=obj['filekey']
            if k in indexCache:
                oldObj=indexCache[k]
                if (oldObj['left'], oldObj['right'], oldObj['mode'])!=(obj['left'], obj['right'], obj['mode']):
                    die('[HDF35] Index line mismatch between prefixed and unprefixed file')
            indexCache[k]=obj
        if(op=='labels'):
            k=obj['filekey']
            if k in labelsCache:
                oldObj=labelsCache[k]
                if (oldObj['left'], oldObj['right'])!=(obj['left'], obj['right']):
                    die('[HDF35] Labels mismatch between prefixed and unprefixed file')
            labelsCache[k]=obj
        if(op=='beginhunk'):
            if(not ((obj['fileformat']=='hintful' and (obj['hunktype']=='hintful' or obj['hunktype']=='unified')) or
                    (obj['fileformat']=='git' and obj['hunktype']=='unified'))):
                die(f"[HDF23] Illegal combination of fileformat={obj['fileformat']}, hunktype={obj['hunktype']}")
            k=obj['hunkkey']
            if k in hunkCache:
                oldObj=hunkCache[k]
                if not oldObj['prefix'] or obj['prefix']:
                    die('Duplicate hunks can only be first a prefixed and then an unprefixed.')
            hunkCache[k]=obj
            if lastHunk and lastHunk['filekey']==obj['filekey'] and lastHunk['prefix']==obj['prefix']:
                for side in ['left', 'right']:
                    if not lastHunk[f'{side}startline']+lastHunk[f'{side}linecount']<=obj[f'{side}startline']:
                        die(f'[HDF24] Hunk begins on {side} side before the previous one ended')
            lastHunk=obj
        if(op=='endhunk'):
            k=obj['hunkkey']
            beginhunk=hunkCache[k]
            for side in ['left', 'right']:
                if k in endHunkCache:
                    if endHunkCache[k][f'{side}content']!=obj[f'{side}content']:
                        die(f'[HDF37] Content mismatch on {side} side in duplicate hunk')
                content=obj[f'{side}content']
                nonl=content and not content.endswith('\n')
                if(content and not state[f'{side}allowed']):
                    die(f'[HDF18] Content on {side} side after a hunk ending without newline')
                if(nonl):
                    state[f'{side}allowed']=False
                linecount = len(content.split('\n')) - (0 if nonl else 1)
                if(linecount!=beginhunk[f'{side}linecount']):
                    die(f"[HDF11] Line count on {side} side declared as {beginhunk[f'{side}linecount']} but is really {linecount}")
            endHunkCache[k]=obj
        yield obj
    for fileKey in fileCache:
        if(fileCache[fileKey]['prefix']):
            die('[HDF32] Prefixed file comparison not followed by unprefixed file comparison')
    for hunkKey in hunkCache:
        if(hunkCache[hunkKey]['prefix']):
            die('[HDF36] Prefixed hunk not followed by unprefixed hunk')
    for fileKey in indexCache:
        if(indexCache[fileKey]['prefix']):
            die('[HDF34] Index line present for prefixed file but missing for unprefixed file')
    for fileKey in labelsCache:
        if(labelsCache[fileKey]['prefix']):
            die('[HDF34] Labels line present for prefixed file but missing for unprefixed file')

def assertNoUnprefixedHintfulFileComparisons(inputObjs):
    for obj in inputObjs:
        if(obj['op']=='beginfile' and not obj['prefix'] and obj['fileformat']=='hintful'):
            die('[HDF41] Unexpected unprefixed hintful file comparison in compat diff file')
        yield obj

def applyPrefixedFiles(inputObjs):
    fileCache={}
    def hunkKey(hunk):
        return (
            hunk['leftstartline'],
            hunk['leftlinecount'],
            hunk['rightstartline'],
            hunk['rightlinecount'],
        )
    for obj in inputObjs:
        op=obj['op']
        if not op=='file':
            die('Weird object in applyPrefixedFiles')
        fileKey=(obj['leftfile'], obj['rightfile'])
        if(obj['prefix']):
            fileCache[fileKey]=obj
            continue
        if(fileKey in fileCache):
            oldFile=obj
            appliedFile=fileCache[fileKey]
            hunkCache={}
            for hunkObj in appliedFile['contents']:
                op2=hunkObj['op']
                if(op2=='hunk'): hunkCache[hunkKey(hunkObj)]=hunkObj
                elif(op2 in ['index', 'labels']): pass
                else: die(f'Unexpected op {op2} in applyPrefixedFiles')
            newContents=[]
            for hunkObj in oldFile['contents']:
                op2=hunkObj['op']
                if(op2=='hunk' and hunkKey(hunkObj) in hunkCache): newContents.append(hunkCache[hunkKey(hunkObj)])
                elif(op2 in ['index', 'hunk', 'labels']): newContents.append(hunkObj)
                else: die(f'Unexpected op {op2} in applyPrefixedFiles')
            yield {
                **oldFile,
                'fileformat': appliedFile['fileformat'],
                'contents': newContents
            }
            continue
        yield obj

def output(inputStrings):
    for text in inputStrings:
        print(text, sep='', end='')

def sink(inputObjs):
    for __ignored in inputObjs:
        pass

def getProcStack():
    procStack={
        'convert-compat-diff-to-hintful-diff': [
            groupHunks,
            groupFiles,
            applyPrefixedFiles,
            ungroupFiles,
            ungroupHunks,
            formatDiff,
            output,
        ],
        'convert-compat-diff-to-unified-diff': [
            removeEverythingPrefixed,
            formatDiff,
            output,
        ],
        'convert-hintful-diff-to-compat-diff': [
            removeEverythingPrefixed, # Correct but inelegant
            groupHunks,
            groupFiles,
            duplicateFilesForCompat,
            ungroupFiles,
            ungroupHunks,
            convertUnprefixedHunksToUnified,
            formatDiff,
            output,
        ],
        'convert-hintful-diff-to-unified-diff': [
            removeEverythingPrefixed,
            removeSnippets,
            convertUnprefixedHunksToUnified,
            formatDiff,
            output,
        ],
        'convert-unified-diff-to-compat-diff': [
            removeEverythingPrefixed,
            groupHunks,
            groupFiles,
            duplicateFilesForCompat,
            ungroupFiles,
            convertPrefixedHunksToHintful,
            ungroupHunks,
            formatDiff,
            output,
        ],
        'convert-unified-diff-to-hintful-diff': [
            removeEverythingPrefixed,
            groupHunks,
            convertHunksToHintful,
            ungroupHunks,
            formatDiff,
            output,
        ],
        'reverse-compat-diff': [
            reverse,
            formatDiff,
            output,
        ],
        'reverse-hintful-diff': [
            reverse,
            formatDiff,
            output,
        ],
        'reverse-unified-diff': [
            reverse,
            formatDiff,
            output,
        ],
        'validate-compat-diff': [
            assertNoUnprefixedHintfulFileComparisons,
            validateSnippets,
            validateFilesAndHunks,
            sink,
        ],
        'validate-hintful-diff': [
            validateSnippets,
            validateFilesAndHunks,
            sink,
        ],
        'validate-unified-diff': [
            removeEverythingPrefixed,
            validateFilesAndHunks,
            sink,
        ],
    }[os.path.basename(sys.argv[0])]
    return procStack
def main(procStack):
    # Abusing latin1 encoding lets us handle several encodings and also binary the same way
    sys.stdin.reconfigure(encoding='latin1')
    sys.stdout.reconfigure(encoding='latin1')
    def reducer(reduced, next_generator):
        return next_generator(reduced)
    fullProcStack=[
        glueNonewline,
        parseDiff,
        *procStack,
    ]
    functools.reduce(reducer, fullProcStack, getInputLines())
if __name__ == "__main__":
    main(getProcStack())
