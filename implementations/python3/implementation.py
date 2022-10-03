#!/usr/bin/env python3
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

def nextOrDie(inputGenerator):
    try:
        return next(inputGenerator)
    except StopIteration:
        die('Unexpected stop of generator')

def parseDiff(inputLines):
    filePrefix=None
    fileFormat=None
    fileKey=None
    for line in inputLines:
        linem = m(r'^(\|?).*\n$', line)
        if linem[1]!=filePrefix and not m(r'^(\|?)diff --(git|hintful).*\n$', line):
            die('Expected prefix to match previous line')
        linem = m(r'^(\|?)@@ +-([0-9]+)(,[0-9]+)? +(\^*[0-9]+\\? +)?\+([0-9]+)(,[0-9]+)? +@@(.*)\n$', line)
        if(linem):
            prefix = linem[1]
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
            continue
        linem = m(r'^(\|?)--- ([^\r]*)\r*\n$', line)
        if(linem):
            line2 = nextOrDie(inputLines)
            line2m = m(r'^(\|?)\+\+\+ ([^\r]*)\r*\n$', line2)
            if not line2 or not line2m or not (linem[1]==line2m[1]):
                die('Expected a +++ line with same prefix')
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
            yield {
                'op': 'similarity-index',
                'prefix': linem[1],
                'filekey': fileKey,
                'similarity-index': linem[2],
                }
            continue
        linem = m(r'^(\|?)rename from ([^\r]*)\r*\n$', line)
        if(linem):
            line2 = nextOrDie(inputLines)
            line2m = m(r'^(\|?)rename to ([^\r]*)\r*\n$', line2)
            if not line2 or not line2m or not (linem[1]==line2m[1]):
                die('Expected "rename to" line with same prefix')
            yield {
                'op': 'rename',
                'prefix': linem[1],
                'filekey': fileKey,
                'left': linem[2],
                'right': line2m[2],
                }
            continue
        if(m(r'^\|?([.=]*[-+ _#]|[,^$]+:).*\n$', line)):
            die(f'Hunk content without header: {line}')
        linem = m(r'^(\|?)index ([0-9a-f]{7,})\.\.([0-9a-f]{7,})( +[0-7]{6})?\r*\n$', line)
        if(linem):
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
            continue
        die(f'Cannot parse line {line}')
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
                die(r'Prefix before \ No newline must match the previous line')
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
            die('Corrupt hunk line count')
        line = nextOrDie(inputLines)
        linem = m(r'^(\|?).*\n(.*\n)?$', line)
        if linem[1]!=header['prefix']:
            die('Expected prefix to match previous line')
        linem = m(r'^(\|?)([-+ ])(.*)\n\|?\\ .*\n$', line) or m(r'^(\|?)([-+ ])(.*\n)$', line)
        if linem:
            prefix = linem[1]
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
        die(f'Corrupt hunk, contained line: {line}')
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
        line = nextOrDie(inputLines)
        linem = m(r'^(\|?).*\n$', line)
        if linem[1]!=header['prefix']:
            die('Expected prefix to match previous line')
        linem = m(r'^(\|?)([.=]{'+str(cc)+r'})([-+ _#])(.*)('+(r'[$\\]' if nlm else '')+')(\r*\n)$', line)
        if(linem):
            prefix = linem[1]
            snippetindicators = linem[2]
            opchar = linem[3]
            content = linem[4]
            nlmarker = linem[5]
            crlf = linem[6]
            if(nlmarker=='$'):
                if(content.endswith('\r')):
                    die('CR character not allowed before $ newline marker')
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
                        die(r'\r*\n sequence must not be split.')
                    state[f'{side}content']+=content
            for snippet in state['snippets']:
                if(snippetshavecontent[snippet['index']]):
                    if(not snippet['name']):
                        die('= in inactive snippet column')
                    if(snippet['content'].endswith('\r') and m(r'^\r*\n', content)):
                        die(r'\r*\n sequence must not be split.')
                    snippet['content']+=content
            continue
        linem = m(r'^(\|?)([,^]{'+str(cc)+r'}):([^\r]*)\r*\n$', line)
        if(linem):
            prefix = linem[1]
            snippetindicators = linem[2]
            name = linem[3]
            if(m(r',{'+str(cc)+r'}', snippetindicators)):
                if(name==''):
                    die('Snippet deactivation line must have at least one dollar sign.')
                else:
                    die('Snippet activation line must have at least one caret sign.')
            if(name==''):
                die('Snippet activation line must have a non-empty snippet name.')
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
        die(f'Corrupt hunk: Strange line: {line}')
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

def formatDiff(inputObjs):
    hunktype=None
    cc=None
    nlm=None
    for obj in inputObjs:
        op=obj['op']
        prefix=obj['prefix']
        if(op=='beginhunk'):
            hunktype=obj['hunktype']
            cc=obj['snippetcolumncount']
            nlm=obj['newlinemarkers']
            yield from [
                prefix,
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
            yield prefix
            for snippetindex in range(cc):
                yield '=' if obj['snippetshavecontent'][snippetindex] else '.'
            yield {'leftcontent': '-', 'rightcontent': '+', 'bothcontent': ' ', 'bothlowprioritycontent': '_', 'ignorecontent': '#'}[op]
            content = obj['content']
            if(hunktype=='unified'):
                yield obj['content']
                if not obj['content'].endswith('\n'):
                    yield '\n\\ No newline at end of file\n'
            elif(hunktype=='hintful'):
                if nlm:
                    if content.endswith('\n'):
                        contentm = m(r'^(.*[^\r])?(\r*\n)$', content)
                        yield contentm[1] or ''
                        yield '$'
                        yield contentm[2]
                    else:
                        yield content
                        yield '\\\n'
                else:
                    if contents.endswith('\n'):
                        yield content
                    else:
                        die('Content must end with newline in hintful mode without newline marker')
            else:
                die('Unexpected hunk type')
        elif(op=='activatesnippets'):
            yield from [
                prefix,
                *[ '^' if x else ',' for x in obj['snippetcolumns'] ],
                ':',
                obj['name'],
                '\n',
            ]
        elif(op=='deactivatesnippets'):
            yield from [
                prefix,
                *[ '$' if x else ',' for x in obj['snippetcolumns'] ],
                ':\n',
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
            yield f"{prefix}--- {obj['left']}\n{prefix}+++ {obj['right']}\n"
        elif(op=='beginfile'):
            yield f"{prefix}diff --{obj['fileformat']} {obj['leftfile']} {obj['rightfile']}\n"
        elif(op=='index'):
            yield f"{prefix}index {obj['left']}..{obj['right']}"
            if obj['mode']:
                yield obj['mode']
            yield '\n'
        elif(op.endswith('filemode')):
            yield from [
                prefix,
                {'leftfilemode': 'deleted', 'rightfilemode': 'new'}[op],
                ' file mode ',
                obj['mode'],
                '\n',
            ]
        elif(op=='similarity-index'):
            yield f"{prefix}similarity index {obj['similarity-index']}\n"
        elif(op=='rename'):
            yield f"{prefix}rename from {obj['left']}\n"
            yield f"{prefix}rename to {obj['right']}\n"
        else:
            die(f'formatDiff cannot process operation {op}')

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
                die(f'Content of snippet {name} did not match previous use')
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
                    die('Prefix mismatch')
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
                    die('Prefix mismatch')
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
                    die('Duplicate files can only be first a prefixed and then an unprefixed.')
            fileCache[k]=obj
        if(op=='index'):
            k=obj['filekey']
            if k in indexCache:
                oldObj=indexCache[k]
                if (oldObj['left'], oldObj['right'], oldObj['mode'])!=(obj['left'], obj['right'], obj['mode']):
                    die('Index line mismatch between prefixed and unprefixed file')
            indexCache[k]=obj
        if(op=='labels'):
            k=obj['filekey']
            if k in labelsCache:
                oldObj=labelsCache[k]
                if (oldObj['left'], oldObj['right'])!=(obj['left'], obj['right']):
                    die('Labels mismatch between prefixed and unprefixed file')
            labelsCache[k]=obj
        if(op=='beginhunk'):
            if(not ((obj['fileformat']=='hintful' and (obj['hunktype']=='hintful' or obj['hunktype']=='unified')) or
                    (obj['fileformat']=='git' and obj['hunktype']=='unified'))):
                die(f"Illegal combination of fileformat={obj['fileformat']}, hunktype={obj['hunktype']}")
            k=obj['hunkkey']
            if k in hunkCache:
                oldObj=hunkCache[k]
                if not oldObj['prefix'] or obj['prefix']:
                    die('Duplicate hunks can only be first a prefixed and then an unprefixed.')
            hunkCache[k]=obj
            if lastHunk and lastHunk['filekey']==obj['filekey'] and lastHunk['prefix']==obj['prefix']:
                for side in ['left', 'right']:
                    if not lastHunk[f'{side}startline']+lastHunk[f'{side}linecount']<=obj[f'{side}startline']:
                        die(f'Hunk begins on {side} side before the previous one ended')
            lastHunk=obj
        if(op=='endhunk'):
            k=obj['hunkkey']
            beginhunk=hunkCache[k]
            for side in ['left', 'right']:
                if k in endHunkCache:
                    if endHunkCache[k][f'{side}content']!=obj[f'{side}content']:
                        die(f'Content mismatch on {side} side in duplicate hunk')
                content=obj[f'{side}content']
                nonl=content and not content.endswith('\n')
                if(content and not state[f'{side}allowed']):
                    die('Content on {side} side after a hunk ending without newline')
                if(nonl):
                    state[f'{side}allowed']=False
                linecount = len(content.split('\n')) - (0 if nonl else 1)
                if(linecount!=beginhunk[f'{side}linecount']):
                    die(f"Line count on {side} side declared as {beginhunk[f'{side}linecount']} but is really {linecount}")
            endHunkCache[k]=obj
        yield obj
    for hunkKey in hunkCache:
        if(hunkCache[hunkKey]['prefix']):
            die('Prefixed hunk not followed by unprefixed hunk')
    for fileKey in indexCache:
        if(indexCache[fileKey]['prefix']):
            die('Index line present for prefixed file but missing for unprefixed file')
    for fileKey in labelsCache:
        if(labelsCache[fileKey]['prefix']):
            die('Labels line present for prefixed file but missing for unprefixed file')

def assertNoUnprefixedHintfulHunks(inputObjs):
    for obj in inputObjs:
        if(obj['op']=='beginhunk' and not obj['prefix'] and obj['hunktype']=='hintful'):
            die('Unexpected unprefixed hintful hunk')
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

def latexEscape(string):
    ret=""
    for char in string:
        ret += {
            " ": '{\\spc}',
            "#": "{\\#}",
            "$": "{\\$}",
            "%": "{\\%}",
            "&": "{\\&}",
            "'": "{'}",
            "-": "{-}",
            "\\": "{\\textbackslash}",
            "^": "{\\textasciicircum}",
            "_": "{\\_}",
            "{": "{\\{}",
            "}": "{\\}}",
            "~": "{\\textasciitilde}",
        }.get(char, char)
    return ret
def latexFormatOperations(inputObjs):
    for obj in inputObjs:
        op=obj['op']
        if(op=="rename"):
            yield {**obj, 'op': 'renamefrom'}
            yield {**obj, 'op': 'renameto'}
        elif(op=="labels"):
            yield {**obj, 'op': 'labelleft'}
            yield {**obj, 'op': 'labelright'}
        elif(op.endswith('content')):
            newop=""
            if(op in ['leftcontent', 'bothcontent', 'bothlowprioritycontent']):
                newop += 'Left'
            if(op in ['rightcontent', 'bothcontent', 'bothlowprioritycontent']):
                newop += 'Right'
            if(op=='ignorecontent'):
                newop += 'Ignore'
            if(op=='bothlowprioritycontent'):
                newop += 'Lowprio'
            if(not newop):
                die('Bad content type in preLatexFormat')
            for snippetindex, snippethascontent in enumerate(obj['snippetshavecontent']):
                newop += 'Snippet' + ['one', 'two'][snippetindex] + ('yes' if snippethascontent else 'no')
            newop += 'Content'
            yield {**obj, 'op': newop}
        elif(op in ['activatesnippets', 'deactivatesnippets']):
            newop=op
            for snippetindex, snippetindicator in enumerate(obj['snippetcolumns']):
                newop+=['one', 'two'][snippetindex]
                newop+='yes' if snippetindicator else 'no'
            yield {**obj, 'op': newop}
        else:
            yield obj
def latexFormatContents(inputObjs, task):
    hunktype=''
    fileKey=None
    seenPrefixedHunks=set()
    suppressed=False
    for obj in inputObjs:
        op=obj['op']
        if(op=='beginfile'):
            fileKey=(obj['leftfile'], obj['rightfile'])
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
        if(op=='endhunk'):
            hunktype=''
        if(op in ['endsnippet', 'endhunk', 'endfile']):
            continue
        if obj['prefix']:
            yield {'op': 'begin', 'latexmacro': 'Prefix'}
            yield obj['prefix']
            yield {'op': 'end'}
        latexMacro = task
        latexMacro += hunktype.capitalize()
        if(op in [
                'beginfile',
                'index',
                'leftfilemode',
                'rightfilemode',
                'similarity-index',
                'renamefrom',
                'renameto',
        ]):
            latexMacro += 'Header'
        elif(op.endswith('Content')):
            latexMacro += op + ('Line' if obj['content'].endswith('\n') else 'Cont')
        else:
            latexMacro += op.capitalize()
        if(suppressed and (op.endswith('Content') or op=='beginhunk')):
            latexMacro += "Suppressed"
        yield {'op': 'begin', 'latexmacro': latexMacro}
        if(op=='beginhunk'):
            yield from [
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
            ]
        elif(op.endswith('Content')):
            content = obj['content']
            if content.endswith('\n'):
                contentm = m(r'^(.*[^\r])?(\r*\n)$', content)
                yield contentm[1] or ''
            else:
                yield content
        elif(m('^(activate|deactivate)snippets(one|two|yes|no)+', op)):
            yield obj['name']
        elif(op in ['labelleft']):
            yield f"--- {obj['left']}"
        elif(op in ['labelright']):
            yield f"+++ {obj['right']}"
        elif(op=='beginfile'):
            yield f"diff --{obj['fileformat']} {obj['leftfile']} {obj['rightfile']}"
        elif(op=='index'):
            yield f"index {obj['left']}..{obj['right']}"
            if obj['mode']:
                yield obj['mode']
        elif(op.endswith('filemode')):
            yield from [
                {'leftfilemode': 'deleted', 'rightfilemode': 'new'}[op],
                ' file mode ',
                obj['mode'],
            ]
        elif(op=='similarity-index'):
            yield f"similarity index {obj['similarity-index']}"
        elif(op=='renamefrom'):
            yield f"rename from {obj['left']}"
        elif(op=='renameto'):
            yield f"rename to {obj['right']}"
        else:
            die(f'latexFormat cannot process operation {op}')
        yield {'op': 'end'}
def latexFormatHighlightContents(inputObjs):
    yield from latexFormatContents(inputObjs, 'Highlight')
def latexFormatVisualizeContents(inputObjs):
    yield from latexFormatContents(inputObjs, 'Visualize')
def latexFormatGroupMacros(inputObjs):
    for obj in inputObjs:
        if(not (type(obj)==dict and obj['op']=='begin')):
            die('Bad typing in latexFormatGroupMacros')
        contents=""
        while True:
            nextObj=nextOrDie(inputObjs)
            if(type(nextObj)==str):
                contents += nextObj
            elif(type(nextObj)==int):
                contents += str(nextObj)
            elif(type(nextObj)==dict and nextObj['op']=='end'):
                yield [obj['latexmacro'], contents]
                break
            else:
                die('Bad typing in latexFormatGroupMacros')
def latexFormatCombine(inputObjs):
    def combineHelper(expr1, expr2):
        macro1 = expr1[0]
        macro2 = expr2[0]
        if(macro1.endswith('ContentLine') and m(r'^VisualizeHintful.*Deactivatesnippets(one|two|yes|no)+$', macro2)):
            return ['LineFollowedBySnippetDeactivation',expr1,expr2]
        return None
    prevObj=None
    for obj in inputObjs:
        combination=combineHelper(prevObj, obj) if prevObj and obj else None
        if(combination):
            yield combination
            prevObj=None
        elif(prevObj):
            yield prevObj
            prevObj=obj
        else:
            prevObj=obj
    if(prevObj):
        yield prevObj
def latexFormatGenerate(inputObjs):
    def generateHelper(expr):
        ret = '\\' + expr[0]
        for subexpr in expr[1:]:
            ret += '{' + (latexEscape(subexpr) if type(subexpr)==str else generateHelper(subexpr)) + '}'
        return ret
    for obj in inputObjs:
        if(not (type(obj)==list and 1<=len(obj))):
            die('Bad typing in latexFormatGenerate')
        yield generateHelper(obj) + '%\n'

def output(inputStrings):
    for text in inputStrings:
        print(text, sep='', end='')

def sink(inputObjs):
    for __ignored in inputObjs:
        pass

def main():
    # Abusing latin1 encoding lets us handle several encodings and also binary the same way
    sys.stdin.reconfigure(encoding='latin1')
    sys.stdout.reconfigure(encoding='latin1')
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
            assertNoUnprefixedHintfulHunks,
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
        'latex-highlight-diff': [
            latexFormatOperations,
            latexFormatHighlightContents,
            latexFormatGroupMacros,
            latexFormatCombine,
            latexFormatGenerate,
            output,
        ],
        'latex-visualize-diff': [
            latexFormatOperations,
            latexFormatVisualizeContents,
            latexFormatGroupMacros,
            latexFormatCombine,
            latexFormatGenerate,
            output,
        ],
    }[os.path.basename(sys.argv[0])]
    def reducer(reduced, next_generator):
        return next_generator(reduced)
    procStack=[
        glueNonewline,
        parseDiff,
        *procStack,
    ]
    functools.reduce(reducer, procStack, getInputLines())
main()
