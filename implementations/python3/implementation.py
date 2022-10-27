#!/usr/bin/env python3.9
import functools, os, sys, re
from operator import xor

def m(pattern, string):
    match = re.match(pattern, string)
    if not match:
        return None
    if(match.group(0) != string):
        die(f'Pattern /{pattern}/ matched only part of string', None)
    ret = []
    for index in range((match.lastindex or 0)+1):
        ret.append(match.group(index))
    return ret

def die(reason, lineNr):
    if(type(lineNr)==int):
        sys.stderr.write(f"On input line {lineNr}: {reason}\n")
        sys.exit(1)
    elif(type(lineNr)==list):
        sys.stderr.write(f"On input lines {', '.join([str(x) for x in lineNr])}: {reason}\n")
        sys.exit(1)
    elif(lineNr==None):
        sys.stderr.write(f"Possible implementatation bug.\n{reason}\n")
        sys.exit(2)
    else:
        sys.stderr.write(f"Weird lineNr {repr(lineNr)}\n{reason}\n")
        sys.exit(2)

def getInputLines():
    while True:
        line = sys.stdin.readline()
        if not line:
            break
        yield line

def nextOrDie(inputGenerator, message, lineNr):
    try:
        return next(inputGenerator)
    except StopIteration:
        die(message, lineNr)

def parseDiff(inputLines):
    filePrefix=None
    fileFormat=None
    fileKey=None
    betweenHeaderAndFirstHunk=False
    maxLineNr=0
    for [lineNr, line] in inputLines:
        maxLineNr=lineNr
        linem = m(r'^(\|?)@@ +-([0-9]+)(,[0-9]+)? +(\([0-9]+\) +)?\+([0-9]+)(,[0-9]+)? +@@(.*)\n$', line)
        if(linem):
            prefix = linem[1]
            if prefix!=filePrefix: die('[HDF31] Hunk header prefix did not match previous line', lineNr)
            leftstartlineraw = linem[2]
            leftlinecountraw = linem[3]
            hunklinecountraw = linem[4]
            rightstartlineraw = linem[5]
            rightlinecountraw = linem[6]
            comment = linem[7]
            leftstartline = int(leftstartlineraw)
            rightstartline = int(rightstartlineraw)
            leftlinecount = int(leftlinecountraw[1:] if leftlinecountraw else '1')
            rightlinecount = int(rightlinecountraw[1:] if rightlinecountraw else '1')
            hunklinecount = int(m(r'^\(([0-9]+)\) +$', hunklinecountraw)[1]) if hunklinecountraw else None
            hunktype = 'hintful' if hunklinecountraw else 'unified'
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
                'lineNr': lineNr,
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
            if not betweenHeaderAndFirstHunk: die('[HDF21] `---` line can only appear between file comparison header and first hunk', lineNr)
            if linem[1]!=filePrefix: die('[HDF31] Prefix for `---` line did not match previous line', lineNr)
            [lineNr2, line2] = nextOrDie(inputLines, '[HDF22] Expected a `+++` line but got end of file', lineNr+1)
            maxLineNr=lineNr2
            line2m = m(r'^(\|?)\+\+\+ ([^\r]*)\r*\n$', line2)
            if not line2 or not line2m:
                die('[HDF22] Expected a `+++` line', lineNr2)
            if not (linem[1]==line2m[1]):
                die('[HDF31] Prefix for `+++` line did not match previous line', lineNr2)
            yield {
                'op': 'labels',
                'prefix': linem[1],
                'filekey': fileKey,
                'left': linem[2],
                'right': line2m[2],
                'lineNr': lineNr,
                }
            continue
        linem = m(r'^(\|?)similarity index ([0-9]+%)\r*\n$', line)
        if(linem):
            if not betweenHeaderAndFirstHunk: die('[HDF21] `similarity index` line can only appear between file comparison header and first hunk', lineNr)
            if linem[1]!=filePrefix: die('[HDF31] Prefix for `similarity` line did not match previous line', lineNr)
            yield {
                'op': 'similarity-index',
                'prefix': linem[1],
                'filekey': fileKey,
                'similarity-index': linem[2],
                'lineNr': lineNr,
                }
            continue
        linem = m(r'^(\|?)rename from ([^\r]*)\r*\n$', line)
        if(linem):
            if not betweenHeaderAndFirstHunk: die('[HDF21] `rename from` line can only appear between file comparison header and first hunk', lineNr)
            if linem[1]!=filePrefix: die('[HDF31] Prefix for `rename from` line did not match previous line', lineNr)
            [lineNr2, line2] = nextOrDie(inputLines, '[HDF22] Expected `rename to` line but got end of file', lineNr+1)
            maxLineNr=lineNr2
            line2m = m(r'^(\|?)rename to ([^\r]*)\r*\n$', line2)
            if not line2 or not line2m:
                die('[HDF22] Expected `rename to` line', lineNr2)
            if not (linem[1]==line2m[1]):
                die('[HDF31] Prefix for `rename to` line must match that of `rename from` line', lineNr2)
            yield {
                'op': 'rename',
                'prefix': linem[1],
                'filekey': fileKey,
                'left': linem[2],
                'right': line2m[2],
                'lineNr': lineNr,
                }
            continue
        if(m(r'^\|?[-+ _#<>].*\n$', line)):
            die(f'[HDF21] Hunk content without header: {line}', lineNr)
        linem = m(r'^(\|?)index ([0-9a-f]{7,})\.\.([0-9a-f]{7,})( +[0-7]{6})?\r*\n$', line)
        if(linem):
            if not betweenHeaderAndFirstHunk: die('[HDF21] `index` line can only appear between file comparison header and first hunk', lineNr)
            if linem[1]!=filePrefix: die('[HDF31] Prefix for `index` line did not match previous line', lineNr)
            yield {
                'op': 'index',
                'prefix': linem[1],
                'filekey': fileKey,
                'left': linem[2],
                'right': linem[3],
                'mode': linem[4] if len(linem)==5 else None,
                'lineNr': lineNr,
                }
            continue
        linem = m(r'^(\|?)(new|deleted) file mode ([^\r]*)\r*\n$', line)
        if(linem):
            if not betweenHeaderAndFirstHunk: die(f'[HDF21] `{linem[2]} file mode` line can only appear between file comparison header and first hunk', lineNr)
            if linem[1]!=filePrefix: die(f'[HDF31] Prefix for `{linem[2]} file mode` line did not match previous line', lineNr)
            side={'deleted': 'left', 'new': 'right'}[linem[2]]
            yield {
                'op': f'{side}filemode',
                'prefix': linem[1],
                'filekey': fileKey,
                'mode': linem[3],
                'lineNr': lineNr,
            }
            continue
        linem = m(r'^(\|?)diff --(git|hintful) ([^ ]+) +([^ \r]+)\r*\n$', line)
        if(linem):
            if(filePrefix!=None):
                yield {
                    'op': 'endfile',
                    'prefix': filePrefix,
                    'filekey': fileKey,
                    'lineNr': lineNr-1,
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
                'lineNr': lineNr,
            }
            betweenHeaderAndFirstHunk=True
            continue
        if(betweenHeaderAndFirstHunk):
            die(f"[HDF22] Cannot parse extended header line '{line}'", lineNr)
        else:
            die(f"[HDF21] Cannot parse line '{line}'", lineNr)
    if(filePrefix!=None):
        yield {
            'op': 'endfile',
            'prefix': filePrefix,
            'filekey': fileKey,
            'lineNr': maxLineNr,
        }

def glueNonewline(inputLines):
    prevLine = ''
    lineNr = 0
    for line in inputLines:
        lineNr += 1
        linem = m(r'^(\|?)\\.*\n$', line)
        if(linem):
            prevLinem = m(r'^(\|?).*\n$', prevLine)
            if(prevLinem[1]!=linem[1]):
                die(r'[HDF31] Prefix before `\ No newline at end of file` must match the previous line', lineNr)
            yield [lineNr-1, prevLine + line]
            prevLine = ''
        else:
            if prevLine:
                yield [lineNr-1, prevLine]
            prevLine = line
    if prevLine:
        yield [lineNr, prevLine]

def parseUnifiedHunk(header, inputLines, extraFields):
    leftlinecount = header['leftlinecount']
    rightlinecount = header['rightlinecount']
    leftcontent = ''
    rightcontent = ''
    lineNr=header['lineNr']
    while(0 < leftlinecount or 0 < rightlinecount):
        if(leftlinecount < 0 or rightlinecount < 0):
            die('[HDF11] Corrupt hunk line count', [header['lineNr'], lineNr])
        [lineNr, line] = nextOrDie(inputLines, '[HDF11] End of file inside unified hunk', lineNr+1)
        linem = m(r'^(\|?)([-+ ])(.*)\n\|?\\ .*\n$', line) or m(r'^(\|?)([-+ ])(.*\n)$', line)
        if linem:
            prefix = linem[1]
            if prefix!=header['prefix']:
                die(f'[HDF31] Expected prefix for unified content line to match previous line', lineNr)
            opchar = linem[2]
            content = linem[3]
            yield {
                'op': {'-': 'leftcontent', '+': 'rightcontent', ' ': 'bothcontent'}[opchar],
                'prefix': prefix,
                'content': content,
                'leftsnippetname': '',
                'rightsnippetname': '',
                'lineNr': lineNr,
                **extraFields,
            }
            if(opchar in '- '):
                leftlinecount-=1
                leftcontent+=content
            if(opchar in '+ '):
                rightlinecount-=1
                rightcontent+=content
            continue
        die(f"[HDF12] Corrupt hunk, contained line: '{line}'", lineNr)
    yield {
        'op': 'endhunk',
        'prefix': header['prefix'],
        'leftcontent': leftcontent,
        'rightcontent': rightcontent,
        'lineNr': lineNr,
        **extraFields,
    }

def parseHintfulHunk(header, inputLines, extraFields):
    state={
        'leftcontent': '',
        'rightcontent': '',
        'leftsnippetname': '',
        'rightsnippetname': '',
        'leftsnippetcontent': '',
        'rightsnippetcontent': '',
    }
    lineNr=header['lineNr']
    for _ in range(header['hunklinecount']):
        [lineNr, line] = nextOrDie(inputLines, '[HDF11] End of file inside hintful hunk', lineNr+1)
        if m(r'^(\|?)([-+ _#])(.*)\n\|?\\ .*\n$', line):
            die('[HDF17] Encountered `\ No newline at end of file` syntax in hintful hunk', lineNr+1)
        linem = m(r'^(\|?)([-+ _#])(.*)([$\\])(\r*\n)$', line)
        if(linem):
            prefix = linem[1]
            if prefix!=header['prefix']:
                die(f'[HDF31] Expected prefix for hintful content line to match previous line', lineNr)
            opchar = linem[2]
            content = linem[3]
            nlmarker = linem[4]
            crlf = linem[5]
            if(nlmarker=='$'):
                if(content.endswith('\r')):
                    die('[HDF16] CR character not allowed before $ newline marker', lineNr)
                content += crlf
            op = {'-': 'leftcontent', '+': 'rightcontent', ' ': 'bothcontent', '_': 'bothlowprioritycontent', '#': 'ignorecontent'}[opchar]
            yield {
                'op': op,
                'prefix': prefix,
                'content': content,
                'leftsnippetname': state['leftsnippetname'],
                'rightsnippetname': state['rightsnippetname'],
                'lineNr': lineNr,
                **extraFields,
            }
            for side in ['left', 'right']:
                if(op in [f'{side}content', 'bothcontent', 'bothlowprioritycontent']):
                    target = f'{side}snippetcontent' if state[f'{side}snippetname'] else f'{side}content'
                    if(state[target].endswith('\r') and m(r'^\r*\n', content)):
                        die(r'[HDF16] `\r*\n` sequence must not be split.', lineNr)
                    state[target]+=content
            continue
        linem = m(r'^(\|?)([<>])([^\r]*)\r*\n$', line)
        if(linem):
            prefix = linem[1]
            if prefix!=header['prefix']:
                die(f'[HDF31] Expected prefix for hintful snippet line to match previous line', lineNr)
            opchar = linem[2]
            name = linem[3]
            op = {'<': 'leftsnippet', '>': 'rightsnippet'}[opchar]
            for side in ['left', 'right']:
                if(op==f'{side}snippet'):
                    if state[f'{side}snippetname']:
                        yield {
                            'op': f'end{side}snippet',
                            'prefix': prefix,
                            'name': state[f'{side}snippetname'],
                            'content': state[f'{side}snippetcontent'],
                            'lineNr': lineNr,
                            **extraFields,
                        }
                    state[f'{side}snippetname']=name
                    state[f'{side}snippetcontent']=''
            yield {
                'op': op,
                'prefix': prefix,
                'name': name,
                'lineNr': lineNr,
                **extraFields,
            }
            continue
        die(f"[HDF12] Corrupt hunk: Strange line: '{line}'", lineNr)
    if(state['leftsnippetname'] or state['rightsnippetname']):
        die('[HDF13] Hunk ended inside named snippet', lineNr)
    yield {
        'op': 'endhunk',
        'prefix': header['prefix'],
        **extraFields,
        'leftcontent': state['leftcontent'],
        'rightcontent': state['rightcontent'],
        'lineNr': lineNr,
    }

def formatDiffHelper(inputObjs, task="raw"):
    if(task not in ["raw", "highlight", "visualize"]):
        die(f"Bad task {task} in formatDiffHelper", None)
    def interpretAndColorize(inputObjs):
        hunktype=None
        seenPrefixedHunks=set()
        suppressed=False
        fileKey=None
        palette=["stdfg", "stdbg", "red", "green", "magenta", "grey"]
        snippetcolors={'leftsnippet': 'red', 'rightsnippet': 'green'}
        bar='' if task=="raw" else {'op': 'bar'}
        leftsnippetname=''
        rightsnippetname=''
        def colorize(fg="stdfg", bold=False, bg="stdbg"):
            if(task=="raw"): return ''
            if(suppressed):
                return {
                    'op': 'colorize',
                    'fg': "grey",
                    'bold': False,
                    'bg': "stdbg",
                }
            if(fg not in palette): die(f'Illegal fg color {fg}', None)
            if(bg not in palette): die(f'Illegal bg color {bg}', None)
            if(fg==bg): die(f'Cannot use same fg and bg color.', None)
            # Grey is used to de-emphasize and bold to emphasize.
            if(bold and "grey" in [fg, bg]): die(f'Bold grey is illegal.', None)
            if(bold not in [True, False]): die(f'Illegal bold value {bold}', None)
            return {
                'op': 'colorize',
                'fg': fg,
                'bold': bold,
                'bg': bg,
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
                yield from [
                    *prefix,
                    colorize(fg="magenta", bold=True),
                    '@@ -',
                    obj['leftstartlineraw'],
                    obj['leftlinecountraw'] or '',
                ]
                if(hunktype=='hintful'):
                    yield from [
                        ' (',
                        str(obj['hunklinecount']),
                        ')',
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
                files=""
                if(op in ['leftcontent', 'bothcontent', 'bothlowprioritycontent'] and not leftsnippetname):
                    files+="left"
                if(op in ['rightcontent', 'bothcontent', 'bothlowprioritycontent'] and not rightsnippetname):
                    files+="right"
                charbgcolor={'left': 'red', 'right': 'green', '': 'stdfg', 'leftright': 'stdbg'}[files]
                [                              char, charfgcolor, contentfgcolor, contentbgcolor, nlmfgcolor]={
                    'leftcontent':            ['-',  "stdfg",     "stdfg",        "red",          "red",     ],
                    'rightcontent':           ['+',  "stdfg",     "stdfg",        "green",        "green",   ],
                    'bothcontent':            [' ',  "stdfg",     "stdfg",        "stdbg",        "magenta", ],
                    'bothlowprioritycontent': ['_',  "grey",      "grey",         "stdbg",        "magenta", ],
                    'ignorecontent':          ['#',  "grey",      "stdfg",        "grey",         "grey",    ],
                }[op]
                if charbgcolor=="stdfg" and charfgcolor=="stdfg":
                    charfgcolor="stdbg"
                if not(task=="visualize" and hunktype=="hintful"):
                    yield colorize(fg=charfgcolor, bg=charbgcolor)
                    yield char
                    if not suppressed:
                        yield colorize(fg="grey")
                        yield bar
                content = obj['content']
                yield colorize(fg=contentfgcolor, bg=contentbgcolor)
                nlmColorize=colorize(fg=nlmfgcolor)
                if(hunktype=='unified'):
                    yield obj['content']
                    if not obj['content'].endswith('\n'):
                        yield from [
                            '\n',
                            *prefix,
                            nlmColorize,
                            '\\',
                            colorize(fg="grey"),
                            bar,
                            nlmColorize,
                            ' No newline at end of file\n',
                            ]
                elif(hunktype=='hintful'):
                    if content.endswith('\n'):
                        contentm = m(r'^(.*[^\r])?(\r*\n)$', content)
                        yield from [
                            contentm[1] or '',
                            nlmColorize,
                            '$',
                            contentm[2],
                            ]
                    else:
                        yield content
                        if not(task=="visualize" and hunktype=="hintful"):
                            yield from [
                                nlmColorize,
                                '\\\n',
                            ]
                else:
                    die('Unexpected hunk type', None)
            elif(op in ['leftsnippet', 'rightsnippet']):
                if(op=="leftsnippet"):
                    leftsnippetname=obj['name']
                else:
                    rightsnippetname=obj['name']
                char={'leftsnippet': '<', 'rightsnippet': '>'}[op]
                if(task=="visualize" and hunktype=="hintful"):
                    glue=(task=="visualize" and hunktype=="hintful" and not obj['name'])
                    if glue:
                        yield { 'op': 'beginGlueContent' }
                    yield from [
                        colorize(fg=snippetcolors[op], bg="stdfg", bold=True),
                        char,
                        obj['name'],
                    ]
                    if glue:
                        yield { 'op': 'endGlueContent' }
                else:
                    yield from [
                        *prefix,
                        colorize(fg=snippetcolors[op], bg="stdfg", bold=True),
                        char,
                        colorize(fg="grey"),
                        bar,
                        colorize(fg=snippetcolors[op], bg="stdfg", bold=True),
                        obj['name'],
                        '\n',
                    ]
            elif(op in ['endleftsnippet', 'endrightsnippet']):
                pass
            elif(op=='endhunk'):
                hunktype=None
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
                die(f'formatDiffHelper cannot process operation {op}', None)
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
            die('processNewlineDeferment ended before inserting deferred newlines', None)
    def processColorizationEndAtNewline(inputObjs):
        for obj in inputObjs:
            if(obj=='\n' and task!="raw"):
                yield {
                    'op': 'colorize',
                    'fg': "stdfg",
                    'bold': False,
                    'bg': "stdbg",
                }
            yield obj
    yield from processColorizationEndAtNewline(processNewlineDeferment(separateNewlines(interpretAndColorize(inputObjs))))

def formatDiff(inputObjs):
    yield from formatDiffHelper(inputObjs, "raw")

def removeSnippets(inputObjs):
    leftsnippetname=''
    rightsnippetname=''
    for obj in inputObjs:
        op=obj['op']
        if(op=='leftcontent'):
            if(leftsnippetname==''):
                yield obj
        elif(op=='rightcontent'):
            if(rightsnippetname==''):
                yield obj
        elif(op in ['bothcontent', 'bothlowprioritycontent']):
            if(leftsnippetname=='' and rightsnippetname==''):
                yield obj
            elif(leftsnippetname==''):
                yield {**obj, 'op': 'leftcontent'}
            elif(rightsnippetname==''):
                yield {**obj, 'op': 'rightcontent'}
        elif(op=='ignorecontent'):
            pass
        elif(op=='leftsnippet'):
            leftsnippetname=obj['name']
        elif(op=='rightsnippet'):
            rightsnippetname=obj['name']
        elif(op in ['endleftsnippet', 'endrightsnippet']):
            pass
        elif(op=='endhunk' and
           (leftsnippetname!='' or
            rightsnippetname!='')):
            die('[HDF13] Hunk ended inside named snippet', obj['lineNr'])
        elif(op in ['beginfile', 'endfile', 'index', 'labels', 'leftfilemode', 'rightfilemode', 'similarity-index', 'rename', 'beginhunk', 'endhunk']):
            yield obj
        else:
            die(f'removeSnippets cannot process operation {op}', None)

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
            die('Broken invariant in convertUnprefixedHunksToUnified', None)
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
                    'leftsnippetname': '',
                    'rightsnippetname': '',
                }
                state[var]='\n'.join(lines[1:])
        checkInvariants()
        if(op=='beginhunk'):
            yield {**obj, 'fileformat': 'git', 'hunktype': 'unified'}
        elif(op=='beginfile'):
            yield {**obj, 'fileformat': 'git'}
        elif(op.endswith('snippet')):
            pass
        elif(op.endswith('content')):
            l=(op in ['leftcontent', 'bothcontent', 'bothlowprioritycontent'] and not obj['leftsnippetname'])
            r=(op in ['rightcontent', 'bothcontent', 'bothlowprioritycontent'] and not obj['rightsnippetname'])
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
            die(f'convertUnprefixedHunksToUnified cannot process operation {op}', None)

def switchleftright(text):
    if(text.startswith('left')): return 'right'+text[4:]
    if(text.startswith('right')): return 'left'+text[5:]
    return text

def reverse(inputObjs):
    for obj in inputObjs:
        op=obj['op']
        if(m(r'^(left|right).*$', op)):
            yield {**obj, 'op': switchleftright(op)}
        else:
            sendobj={}
            for key in obj:
                sendobj[switchleftright(key)] = obj[key]
            yield sendobj

def validateSnippets(inputObjs):
    snippetcache={}
    for obj in inputObjs:
        op=obj['op']
        if(op in ['endleftsnippet', 'endrightsnippet']):
            name=obj['name']
            content=obj['content']
            if(name in snippetcache and snippetcache[name]!=content):
                die(f"[HDF15] Content of snippet '{name}' did not match previous use", obj['lineNr'])
            snippetcache[name]=content
        yield obj

def groupHunks(inputObjs):
    for obj in inputObjs:
        if(obj['op']=='beginhunk'):
            beginHunk=obj
            contents=[]
            endHunk=None
            while True:
                contentObj=nextOrDie(inputObjs, 'Unexpected generator end in groupHunks', None)
                if(contentObj['prefix']!=beginHunk['prefix']):
                    die('[HDF31] Prefix mismatch', contentObj['lineNr'])
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
                contentObj=nextOrDie(inputObjs, 'Unexpected generator end in groupFiles', None)
                if(contentObj['prefix']!=beginFile['prefix']):
                    die('[HDF31] Prefix mismatch', contentObj['lineNr'])
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
            die(f'duplicateFilesForCompat expects only file objects, got unexpected {obj["op"]}', None)
        if(obj['prefix']):
            die('duplicateFilesForCompat expects only unprefixed files', None)
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
                'hunktype': 'hintful'
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
                    die('[HDF33] Duplicate files can only be first a prefixed and then an unprefixed.', [oldObj['lineNr'], obj['lineNr']])
            fileCache[k]=obj
        if(op=='index'):
            k=obj['filekey']
            if k in indexCache:
                oldObj=indexCache[k]
                if (oldObj['left'], oldObj['right'], oldObj['mode'])!=(obj['left'], obj['right'], obj['mode']):
                    die('[HDF35] `index` line mismatch between prefixed and unprefixed file', [oldObj['lineNr'], obj['lineNr']])
            indexCache[k]=obj
        if(op=='labels'):
            k=obj['filekey']
            if k in labelsCache:
                oldObj=labelsCache[k]
                if oldObj['left']!=obj['left']:
                    die('[HDF35] `---` line mismatch between prefixed and unprefixed file', [oldObj['lineNr'], obj['lineNr']])
                if oldObj['right']!=obj['right']:
                    die('[HDF35] `+++` line mismatch between prefixed and unprefixed file', [oldObj['lineNr']+1, obj['lineNr']+1])
            labelsCache[k]=obj
        if(op=='beginhunk'):
            for side in ['left', 'right']:
                if(not state[f'{side}allowed']):
                    # If a hunk has ended without a newline on either side, the hunk must be positioned at end of file for that side.
                    # Since all further content on the other side is necessarily changed, the hunk must be positioned at end of file for both sides.
                    # Hence, it must be the last hunk in the current file comparison.
                    die(f'[HDF18] New hunk following a hunk ending without newline on {side} side', obj['lineNr'])
            if(not ((obj['fileformat']=='hintful' and (obj['hunktype']=='hintful' or obj['hunktype']=='unified')) or
                    (obj['fileformat']=='git' and obj['hunktype']=='unified'))):
                die(f"[HDF23] Illegal combination of fileformat={obj['fileformat']}, hunktype={obj['hunktype']}", obj['lineNr'])
            k=obj['hunkkey']
            if k in hunkCache:
                oldObj=hunkCache[k]
                if not oldObj['prefix'] or obj['prefix']:
                    die('Duplicate hunks can only be first a prefixed and then an unprefixed.', [oldObj['lineNr'], obj['lineNr']])
            hunkCache[k]=obj
            if lastHunk and lastHunk['filekey']==obj['filekey'] and lastHunk['prefix']==obj['prefix']:
                for side in ['left', 'right']:
                    if not lastHunk[f'{side}startline']+lastHunk[f'{side}linecount']<=obj[f'{side}startline']:
                        die(f'[HDF24] Hunk begins on {side} side before the previous one ended', obj['lineNr'])
            lastHunk=obj
        if(op=='endhunk'):
            k=obj['hunkkey']
            beginhunk=hunkCache[k]
            for side in ['left', 'right']:
                if k in endHunkCache:
                    if endHunkCache[k][f'{side}content']!=obj[f'{side}content']:
                        die(f'[HDF37] Content mismatch on {side} side in duplicate hunk', obj['lineNr'])
                content=obj[f'{side}content']
                nonl=content and not content.endswith('\n')
                if(nonl):
                    state[f'{side}allowed']=False
                linecount = len(content.split('\n')) - (0 if nonl else 1)
                if(linecount!=beginhunk[f'{side}linecount']):
                    die(f"[HDF11] Line count on {side} side declared as {beginhunk[f'{side}linecount']} but is really {linecount}", [beginhunk['lineNr'], obj['lineNr']])
            endHunkCache[k]=obj
        yield obj
    for fileKey in fileCache:
        if(fileCache[fileKey]['prefix']):
            die('[HDF32] Prefixed file comparison not followed by unprefixed file comparison', fileCache[fileKey]['lineNr'])
    for hunkKey in hunkCache:
        if(hunkCache[hunkKey]['prefix']):
            die('[HDF36] Prefixed hunk not followed by unprefixed hunk', hunkCache[hunkKey]['lineNr'])
    for fileKey in indexCache:
        if(indexCache[fileKey]['prefix']):
            die('[HDF34] `index` line present for prefixed file but missing for unprefixed file', [indexCache[fileKey]['lineNr'], fileCache[fileKey]['lineNr']])
    for fileKey in labelsCache:
        if(labelsCache[fileKey]['prefix']):
            die('[HDF34] `---` and `+++` lines present for prefixed file but missing for unprefixed file',
                [labelsCache[fileKey]['lineNr'], labelsCache[fileKey]['lineNr']+1, fileCache[fileKey]['lineNr']])

def assertNoUnprefixedHintfulFileComparisons(inputObjs, msg):
    for obj in inputObjs:
        if(obj['op']=='beginfile' and not obj['prefix'] and obj['fileformat']=='hintful'):
            die(msg, obj['lineNr'])
        yield obj
def assertNoUnprefixedHintfulFileComparisonsInCompat(inputObjs):
    yield from assertNoUnprefixedHintfulFileComparisons(inputObjs, '[HDF41] Unexpected unprefixed hintful file comparison in compat diff file')
def assertNoUnprefixedHintfulFileComparisonsInUnified(inputObjs):
    yield from assertNoUnprefixedHintfulFileComparisons(inputObjs, '[HDF21] Unexpected unprefixed hintful file comparison in unified diff file')

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
            die('Weird object in applyPrefixedFiles', None)
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
                else: die(f'Unexpected op {op2} in applyPrefixedFiles', None)
            newContents=[]
            for hunkObj in oldFile['contents']:
                op2=hunkObj['op']
                if(op2=='hunk' and hunkKey(hunkObj) in hunkCache): newContents.append(hunkCache[hunkKey(hunkObj)])
                elif(op2 in ['index', 'hunk', 'labels']): newContents.append(hunkObj)
                else: die(f'Unexpected op {op2} in applyPrefixedFiles', None)
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
            assertNoUnprefixedHintfulFileComparisonsInCompat,
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
            assertNoUnprefixedHintfulFileComparisonsInUnified,
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
