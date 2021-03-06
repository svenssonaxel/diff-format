#!/usr/bin/env python3
import functools, os, sys, re
from operator import xor

def p(*data):
    print(*data, sep='', end='')

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

def parseDiff(inputLines):
    filePrefix=None
    fileKey=None
    for line in inputLines:
        linem = m(r'^(\|?).*\n$', line)
        if linem[1]!=filePrefix and not  m(r'^(\|?)diff --git.*\n$', line):
            die('Expected prefix to match previous line')
        linem = m(r'^(\|?)@@ +-([0-9]+)(,[0-9]+)? +(\([0-9]+\) +)?\+([0-9]+)(,[0-9]+)? +@@(.*)\n$', line)
        if(linem):
            prefix = linem[1]
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
            extraFields = {'filekey': fileKey, 'hunkkey': hunkKey}
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
            }
            yield hunkheader
            if(hunktype=='hintful'):
                yield from parseHintfulHunk(hunkheader, inputLines, extraFields)
            else:
                yield from parseUnifiedHunk(hunkheader, inputLines, extraFields)
            continue
        linem = m(r'^(\|?)--- ([^\r]*)\r*\n$', line)
        if(linem):
            line2 = next(inputLines)
            line2m = m(r'^(\|?)\+\+\+ ([^\r]*)\r*\n$', line2 or '')
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
            line2 = next(inputLines)
            line2m = m(r'^(\|?)rename to ([^\r]*)\r*\n$', line2 or '')
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
        if(m(r'^\|?[-+ _#<>].*\n$', line)):
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
        linem = m(r'^(\|?)diff --git ([^ ]+) +([^ \r]+)\r*\n$', line)
        if(linem):
            if(filePrefix!=None):
                yield {
                    'op': 'endfile',
                    'prefix': filePrefix,
                    'filekey': fileKey,
                }
            filePrefix=linem[1]
            fileKey=(linem[2], linem[3])
            yield {
                'op': f'beginfile',
                'prefix': filePrefix,
                'filekey': fileKey,
                'leftfile': linem[2],
                'rightfile': linem[3],
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

def nextLine(inputLines):
    try:
        line = next(inputLines)
        return line
    except StopIteration:
        die('End of file in middle of hunk')

def parseUnifiedHunk(header, inputLines, extraFields):
    leftlinecount = header['leftlinecount']
    rightlinecount = header['rightlinecount']
    leftcontent = ''
    rightcontent = ''
    while(0 < leftlinecount or 0 < rightlinecount):
        if(leftlinecount < 0 or rightlinecount < 0):
            die('Corrupt hunk line count')
        line = nextLine(inputLines)
        if not line:
            die('Incomplete hunk')
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
                'leftsnippetname': '',
                'rightsnippetname': '',
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
        'leftsnippetname': '',
        'rightsnippetname': '',
        'leftsnippetcontent': '',
        'rightsnippetcontent': '',
    }
    for index in range(header['hunklinecount']):
        line = nextLine(inputLines)
        linem = m(r'^(\|?).*\n$', line)
        if linem[1]!=header['prefix']:
            die('Expected prefix to match previous line')
        linem = m(r'^(\|?)([-+ _#])(.*)([$\\])(\r*\n)$', line)
        if(linem):
            prefix = linem[1]
            opchar = linem[2]
            content = linem[3]
            nlmarker = linem[4]
            crlf = linem[5]
            if(nlmarker=='$'):
                if(content.endswith('\r')):
                    die('CR character not allowed before $ newline marker')
                content += crlf
            op = {'-': 'leftcontent', '+': 'rightcontent', ' ': 'bothcontent', '_': 'bothlowprioritycontent', '#': 'ignorecontent'}[opchar]
            yield {
                'op': op,
                'prefix': prefix,
                'content': content,
                'leftsnippetname': state['leftsnippetname'],
                'rightsnippetname': state['rightsnippetname'],
                **extraFields,
            }
            for side in ['left', 'right']:
                if(op in [f'{side}content', 'bothcontent', 'bothlowprioritycontent']):
                    target = f'{side}snippetcontent' if state[f'{side}snippetname'] else f'{side}content'
                    if(state[target].endswith('\r') and m(r'^\r*\n', content)):
                        die(r'\r*\n sequence must not be split.')
                    state[target]+=content
            continue
        linem = m(r'^(\|?)([<>])([^\r]*)\r*\n$', line)
        if(linem):
            prefix = linem[1]
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
                            **extraFields,
                        }
                    state[f'{side}snippetname']=name
                    state[f'{side}snippetcontent']=''
            yield {
                'op': op,
                'prefix': prefix,
                'name': name,
                **extraFields,
            }
            continue
        die(f'Corrupt hunk: Strange line: {line}')
    if(state['leftsnippetname'] or state['rightsnippetname']):
        die(f'Hunk ended inside snippet')
    yield {
        'op': 'endhunk',
        'prefix': header['prefix'],
        **extraFields,
        'leftcontent': state['leftcontent'],
        'rightcontent': state['rightcontent'],
    }

def formatDiff(inputObjs):
    hunktype=None
    for obj in inputObjs:
        op=obj['op']
        prefix=obj['prefix']
        if(op=='beginhunk'):
            hunktype=obj['hunktype']
            yield from [
                prefix,
                '@@ -',
                obj['leftstartlineraw'],
                obj['leftlinecountraw'] or '',
            ]
            if(hunktype=='hintful'):
                yield from [
                    ' (',
                    obj['hunklinecount'],
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
            yield prefix
            yield {'leftcontent': '-', 'rightcontent': '+', 'bothcontent': ' ', 'bothlowprioritycontent': '_', 'ignorecontent': '#'}[op]
            content = obj['content']
            if(hunktype=='unified'):
                yield obj['content']
                if not obj['content'].endswith('\n'):
                    yield '\n\\ No newline at end of file\n'
            elif(hunktype=='hintful'):
                if content.endswith('\n'):
                    contentm = m(r'^(.*[^\r])?(\r*\n)$', content)
                    yield contentm[1] or ''
                    yield '$'
                    yield contentm[2]
                else:
                    yield content
                    yield '\\\n'
            else:
                die('Unexpected hunk type')
        elif(op in ['leftsnippet', 'rightsnippet']):
            yield from [
                prefix,
                {'leftsnippet': '<', 'rightsnippet': '>'}[op],
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
            yield f"{prefix}--- {obj['left']}\n{prefix}+++ {obj['right']}\n"
        elif(op=='beginfile'):
            yield f"{prefix}diff --git {obj['leftfile']} {obj['rightfile']}\n"
        elif(op=='index'):
            yield f"{prefix}index {obj['left']}..{obj['right']}"
            if obj['mode']:
                yield f" {obj['mode']}"
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
            die('Hunk ended inside named snippet')
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
                    'leftsnippetname': '',
                    'rightsnippetname': '',
                }
                state[var]='\n'.join(lines[1:])
        checkInvariants()
        if(op=='beginhunk'):
            yield {**obj, 'hunktype': 'unified'}
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
        elif(op in ['index', 'labels', 'leftfilemode', 'rightfilemode', 'similarity-index', 'rename', 'beginfile']):
            yield obj
        else:
            die(f'convertUnprefixedHunksToUnified cannot process operation {op}')

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
                contentObj=next(inputObjs)
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
                contentObj=next(inputObjs)
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
            for contentObj in obj['contents']:
                yield {**contentObj, 'prefix': prefix}
            yield {'op': 'endfile', 'prefix': prefix}
        else:
            yield obj

def duplicateFilesForCompat(inputObjs):
    for obj in inputObjs:
        if(obj['op']!='file'):
            die(f'duplicateFilesForCompat expects only file objects, got unexpected {obj["op"]}')
        if(obj['prefix']):
            die('duplicateFilesForCompat expects only unprefixed files')
        yield {**obj, 'prefix': '|'}
        yield obj

def convertHunksToHintful(inputObjs, onlyPrefixed=False):
    for obj in inputObjs:
        if(obj['op']=='hunk' and (not onlyPrefixed or obj['prefix'])):
            hunklinecount = len(obj['contents'])
            yield {
                **obj,
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
    lastHunk=None
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
                   die(f"Line count on {side} side declared as {hunk[f'{side}linecount']} but is really {linecount}")
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
                'contents': newContents
            }
            continue
        yield obj

def output(inputStrings):
    for text in inputStrings:
        p(text)

def sink(inputObjs):
    for __ignored in inputObjs:
        pass

def main():
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
