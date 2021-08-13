#!/usr/bin/env python3
import functools, os, sys, re

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

def parseDiff(inputLines, mode):
    for line in inputLines:
        if(m(r'^@@.*\n$', line)):
            yield from {'unified': parseUnifiedHunk, 'hintful': parseHintfulHunk}[mode](line, inputLines)
            continue
        linem = m(r'^--- ([^\r]*)\r*\n$', line)
        if(linem):
            line2 = next(inputLines)
            line2m = m(r'^\+\+\+ ([^\r]*)\r*\n$', line2 or '')
            if not line2 or not line2m:
                die('Expected a +++ line')
            yield {
                'op': 'labels',
                'left': linem[1],
                'right': line2m[1],
                }
            continue
        linem = m(r'^similarity index ([0-9]+%)\r*\n$', line)
        if(linem):
            yield {
                'op': 'similarity-index',
                'similarity-index': linem[1],
                }
            continue
        linem = m(r'^rename from ([^\r]*)\r*\n$', line)
        if(linem):
            line2 = next(inputLines)
            line2m = m(r'^rename to ([^\r]*)\r*\n$', line2 or '')
            if not line2 or not line2m:
                die('Expected "rename to" line')
            yield {
                'op': 'rename',
                'left': linem[1],
                'right': line2m[1],
                }
            continue
        if(m({'unified': r'^[-+ ].*\n$', 'hintful': r'^[-+ _#<>].*\n$'}[mode], line)):
            die(f'Hunk content without header: {line}')
        linem = m(r'^index ([0-9a-f]{7,})\.\.([0-9a-f]{7,}) +([0-7]{6})\r*\n$', line)
        if(linem):
            yield {
                'op': 'index',
                'left': linem[1],
                'right': linem[2],
                'mode': linem[3],
                }
            continue
        linem = m(r'^index ([0-9a-f]{7,})\.\.([0-9a-f]{7,})\r*\n$', line)
        if(linem):
            yield {
                'op': 'index',
                'left': linem[1],
                'right': linem[2],
                }
            continue
        linem = m(r'^(new|deleted) file mode ([^\r]*)\r*\n$', line)
        if(linem):
            side={'deleted': 'left', 'new': 'right'}[linem[1]]
            yield {
                'op': f'{side}filemode',
                'mode': linem[2],
            }
            continue
        linem = m(r'^diff --git ([^ ]+) +([^ \r]+)\r*\n$', line)
        if(linem):
            yield {
                'op': f'difftitle',
                'leftfile': linem[1],
                'rightfile': linem[2],
            }
            continue
        die(f'Cannot parse line {line}')
def parseUnifiedDiff(inputLines): yield from parseDiff(glueNonewline(inputLines), 'unified')
def parseHintfulDiff(inputLines): yield from parseDiff(inputLines, 'hintful')

def glueNonewline(inputLines):
    prevLine = ''
    for line in inputLines:
        if(m(r'^\\.*\n$', line)):
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

def parseUnifiedHunk(header, inputLines):
    headerm = m(r'^@@ +-([0-9]+)(,[0-9]+)? +\+([0-9]+)(,[0-9]+)? +@@(.*)\n$', header)
    if(not headerm):
        die(f'Corrupt unified hunk header: {header}')
    leftstartlineraw = headerm[1]
    leftlinecountraw = headerm[2]
    rightstartlineraw = headerm[3]
    rightlinecountraw = headerm[4]
    comment = headerm[5]
    leftstartline = int(leftstartlineraw)
    rightstartline = int(rightstartlineraw)
    leftlinecount = int(leftlinecountraw[1:] if leftlinecountraw else '1')
    rightlinecount = int(rightlinecountraw[1:] if rightlinecountraw else '1')
    yield {
        'op': 'beginhunk',
        'leftstartlineraw': leftstartlineraw,
        'leftlinecountraw': leftlinecountraw,
        'rightstartlineraw': rightstartlineraw,
        'rightlinecountraw': rightlinecountraw,
        'comment': comment,
        'leftstartline': leftstartline,
        'rightstartline': rightstartline,
        'leftlinecount': leftlinecount,
        'rightlinecount': rightlinecount,
    }
    while(0 < leftlinecount or 0 < rightlinecount):
        if(leftlinecount < 0 or rightlinecount < 0):
            die('Corrupt hunk line count')
        line = nextLine(inputLines)
        if not line:
            die('Incomplete hunk')
        linem = m(r'^([-+ ])(.*)\n\\ .*\n$', line) or m(r'^([-+ ])(.*\n)$', line)
        if linem:
            prefix = linem[1]
            content = linem[2]
            yield {
                'op': {'-': 'leftcontent', '+': 'rightcontent', ' ': 'bothcontent'}[prefix],
                'content': content,
            }
            if(prefix in '- '): leftlinecount-=1
            if(prefix in '+ '): rightlinecount-=1
            continue
        die(f'Corrupt hunk, contained line: {line}')
    yield {
        'op': 'endhunk',
    }

def parseHintfulHunk(header, inputLines):
    headerm = m(r'^@@ +-([0-9]+)(,[0-9]+)? +\(([0-9]+)\) +\+([0-9]+)(,[0-9]+)? +@@(.*)\n$', header)
    if(not headerm):
        die(f'Corrupt hintful hunk header: {header}')
    leftstartlineraw = headerm[1]
    leftlinecountraw = headerm[2]
    hunklinecountraw = headerm[3]
    rightstartlineraw = headerm[4]
    rightlinecountraw = headerm[5]
    comment = headerm[6]
    leftstartline = int(leftstartlineraw)
    rightstartline = int(rightstartlineraw)
    leftlinecount = int(leftlinecountraw[1:] if leftlinecountraw else '1')
    rightlinecount = int(rightlinecountraw[1:] if rightlinecountraw else '1')
    hunklinecount = int(hunklinecountraw)
    yield {
        'op': 'beginhunk',
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
    }
    for index in range(hunklinecount):
        line = nextLine(inputLines)
        linem = m(r'^([-+ _#])(.*)([$\\])(\r*)\n$', line) or m(r'^([<>])([^\r]*)(\r*)\n$', line)
        if not linem:
            die(f'Corrupt hunk: Strange line: {line}')
        prefix = linem[1]
        content = linem[2]
        nlmarker = linem[3] if len(linem)==5 else ''
        cr = linem[4] if len(linem)==5 else linem[3]
        if(nlmarker=='$'):
            if(content.endswith('\r')):
                die('CR character not allowed before $ newline marker')
            content += f'{cr}\n'
        if(prefix in '-+ _#'):
            yield {
                'op': {'-': 'leftcontent', '+': 'rightcontent', ' ': 'bothcontent', '_': 'bothlowprioritycontent', '#': 'ignorecontent'}[prefix],
                'content': content,
            }
            continue
        if(prefix in '<>'):
            yield {
                'op':{'<': 'leftsnippet', '>': 'rightsnippet'}[prefix],
                'name': content,
            }
            continue
        die('This should never happen')
    yield {
        'op': 'endhunk',
    }

def formatCommonLine(obj):
        op=obj['op']
        if(op=='endhunk'):
            pass
        elif(op in ['labels']):
            yield f"--- {obj['left']}\n+++ {obj['right']}\n"
        elif(op=='difftitle'):
            yield f"diff --git {obj['leftfile']} {obj['rightfile']}\n"
        elif(op=='index'):
            if('mode' in obj):
                yield f"index {obj['left']}..{obj['right']} {obj['mode']}\n"
            else:
                yield f"index {obj['left']}..{obj['right']}\n"
        elif(op.endswith('filemode')):
            yield from [
                {'leftfilemode': 'deleted', 'rightfilemode': 'new'}[op],
                ' file mode ',
                obj['mode'],
                '\n',
            ]
        elif(op=='similarity-index'):
            yield f"similarity index {obj['similarity-index']}\n"
        elif(op=='rename'):
            yield f"rename from {obj['left']}\n"
            yield f"rename to {obj['right']}\n"
        else:
            die(f'formatCommonLine cannot process operation {op}')

def formatUnifiedDiff(inputObjs):
    for obj in inputObjs:
        op=obj['op']
        if(op=='beginhunk'):
            yield from [
                '@@ -',
                obj['leftstartlineraw'],
                obj['leftlinecountraw'] or '',
                ' +',
                obj['rightstartlineraw'],
                obj['rightlinecountraw'] or '',
                ' @@',
                obj['comment'],
                '\n',
            ]
        elif(op.endswith('content')):
            yield {'leftcontent': '-', 'rightcontent': '+', 'bothcontent': ' ', 'bothlowprioritycontent': ' '}[op]
            yield obj['content']
            if not obj['content'].endswith('\n'):
                yield '\n\\ No newline at end of file\n'
        else:
            yield from formatCommonLine(obj)

def formatHintfulDiff(inputObjs):
    for obj in inputObjs:
        op=obj['op']
        if(op=='beginhunk'):
            yield from [
                '@@ -',
                obj['leftstartlineraw'],
                obj['leftlinecountraw'] or '',
                ' (',
                obj['hunklinecountraw'],
                ') +',
                obj['rightstartlineraw'],
                obj['rightlinecountraw'] or '',
                ' @@',
                obj['comment'],
                '\n',
            ]
        elif(op.endswith('content')):
            yield {'leftcontent': '-', 'rightcontent': '+', 'bothcontent': ' ', 'bothlowprioritycontent': '_', 'ignorecontent': '#'}[op]
            content = obj['content']
            if content.endswith('\n'):
                contentm = m(r'^(.*[^\r])?(\r*\n)$', content)
                yield contentm[1] or ''
                yield '$'
                yield contentm[2]
            else:
                yield content
                yield '\\\n'
        elif(op.endswith('snippet')):
            yield from [
                {'leftsnippet': '<', 'rightsnippet': '>'}[op],
                obj['name'],
                '\n',
            ]
        else:
            yield from formatCommonLine(obj)

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
        elif(op=='endhunk' and
           (leftsnippetname!='' or
            rightsnippetname!='')):
            die('Hunk ended inside named snippet')
        elif(op in ['difftitle', 'index', 'labels', 'leftfilemode', 'rightfilemode', 'similarity-index', 'rename', 'beginhunk', 'endhunk']):
            yield obj
        else:
            die(f'removeSnippets cannot process operation {op}')

def collectLines(inputObjs):
    state = {
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
            die('Broken invariant in collectLines')
    for obj in inputObjs:
        op=obj['op']
        content=obj['content'] if op.endswith('content') else None
        checkInvariants()
        for var in ['leftcontent', 'rightcontent', 'bothcontent']:
            while('\n' in state[var]):
                lines=state[var].split('\n')
                yield {
                    'op': var,
                    'content': lines[0]+'\n',
                }
                state[var]='\n'.join(lines[1:])
        checkInvariants()
        if(op in ['leftcontent', 'rightcontent']):
            if(state['bothcontent']):
                state['leftcontent']=state['bothcontent']
                state['rightcontent']=state['bothcontent']
                state['bothcontent']=''
            state[op]+=content
        elif(op in ['bothcontent', 'bothlowprioritycontent']):
            if(not state['leftcontent'] and not state['rightcontent']):
                state['bothcontent']+=content
            else:
                state['leftcontent']+=content
                state['rightcontent']+=content
        elif(op=='endhunk'):
            for var in ['leftcontent', 'rightcontent', 'bothcontent']:
                if(state[var]):
                    yield {
                        'op': var,
                        'content': state[var],
                    }
                    state[var]=''
                    if(var in ['leftcontent', 'bothcontent']):
                        state['leftended']=True
                    if(var in ['rightcontent', 'bothcontent']):
                        state['rightended']=True
            yield obj
        elif(op=='difftitle'):
            state['leftended']=False
            state['rightended']=False
            yield obj
        elif(op in ['index', 'labels', 'leftfilemode', 'rightfilemode', 'similarity-index', 'rename', 'beginhunk']):
            yield obj
        else:
            die(f'collectLines cannot process operation {op}')

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
    state={
        'leftsnippetname': '',
        'leftsnippetcontent': '',
        'rightsnippetname': '',
        'rightsnippetcontent': '',
    }
    for obj in inputObjs:
        op=obj['op']
        if(op.endswith('snippet')):
            side=op[:-7]
            oldname=state[f'{side}snippetname']
            newname=obj['name']
            if(oldname):
                if(oldname in snippetcache and snippetcache[oldname]!=state[f'{side}snippetcontent']):
                    die(f'Snippet {oldname} did not match previous use')
                snippetcache[oldname]=state[f'{side}snippetcontent']
            state[f'{side}snippetname']=newname
            state[f'{side}snippetcontent']=''
        elif(op.endswith('content')):
            for side in ['left', 'right']:
                if(state[f'{side}snippetname'] and op in [f'{side}content', 'bothcontent', 'bothlowprioritycontent']):
                    state[f'{side}snippetcontent']+=obj['content']
        elif(op=='endhunk'):
            if(state['leftsnippetname'] or state['rightsnippetname']):
                die('Hunk ended inside snippet')
        yield obj

def groupHunks(inputObjs):
    for obj in inputObjs:
        if(obj['op']=='beginhunk'):
            beginhunk=obj
            contents=[]
            while True:
                contentObj=next(inputObjs)
                if(contentObj['op']=='endhunk'):
                    break
                contents.append(contentObj)
            yield {**beginhunk, 'op': 'hunk', 'contents': contents}
        else:
            yield obj

def ungroupHunks(inputObjs):
    for obj in inputObjs:
        if(obj['op']=='hunk'):
            beginhunk={**obj, 'op': 'beginhunk'}
            del beginhunk['contents']
            yield beginhunk
            yield from obj['contents']
            yield {'op': 'endhunk'}
        else:
            yield obj

def recountLines(inputObjs):
    for obj in inputObjs:
        if(obj['op']=='hunk'):
            hunklinecount = len(obj['contents'])
            yield {**obj, 'hunklinecount': hunklinecount, 'hunklinecountraw': str(hunklinecount)}
        else:
            yield obj

def validateHunks(inputObjs):
    sidesallowed=(True, True)
    for obj in inputObjs:
        op=obj['op']
        if(not op in ['difftitle', 'hunk', 'index', 'labels', 'leftfilemode', 'rightfilemode', 'similarity-index', 'rename']):
            die(f'Operation {op} not allowed outside hunk')
        if(op=='difftitle'):
            sidesallowed=(True, True)
        if(op=='hunk'):
            sidesallowed = validateHunk(obj, sidesallowed)
        yield obj

def validateHunk(hunk, sidesallowed):
    state={
        'leftsnippetname': '',
        'rightsnippetname': '',
        'leftcontent': '',
        'rightcontent': '',
        'leftallowed': sidesallowed[0],
        'rightallowed': sidesallowed[1],
    }
    for obj in hunk['contents']:
        op=obj['op']
        if(not op in ['leftcontent', 'rightcontent', 'bothcontent', 'bothlowprioritycontent', 'ignorecontent', 'leftsnippet', 'rightsnippet']):
            die(f'Operation {op} not allowed inside hunk')
        if(op.endswith('snippet')):
            state[f'{op[:-7]}snippetname']=obj['name']
        elif(op.endswith('content')):
            for side in ['left', 'right']:
                if(not state[f'{side}snippetname'] and op in [f'{side}content', 'bothcontent', 'bothlowprioritycontent']):
                    if(state[f'{side}content'].endswith('\r') and m(r'^\r*\n$', obj['content'])):
                        die(r'\r*\n sequence must not be split.')
                    state[f'{side}content']+=obj['content']
                    if(state[f'{side}content'] and not state[f'{side}allowed']):
                        die('Content on {side} side after a hunk ending without newline')
    for side in ['left', 'right']:
        if(state[f'{side}snippetname']):
            die(f'Hunk ended inside snippet on {side} side')
        content=state[f'{side}content']
        nonl=content and not content.endswith('\n')
        if(nonl):
            state[f'{side}allowed']=False
        linecount = len(content.split('\n')) - (0 if nonl else 1)
        if(linecount!=hunk[f'{side}linecount']):
           die(f"Line count on {side} side declared as {hunk[f'{side}linecount']} but is really {linecount}")
    return (state['leftallowed'], state['rightallowed'])

def output(inputStrings):
    for text in inputStrings:
        p(text)

def sink(inputObjs):
    for __ignored in inputObjs:
        pass

def main():
    procStack={
        'convert-hintful-diff-to-unified-diff': [
            parseHintfulDiff,
            removeSnippets,
            collectLines,
            formatUnifiedDiff,
            output,
        ],
        'convert-unified-diff-to-hintful-diff': [
            parseUnifiedDiff,
            groupHunks,
            recountLines,
            ungroupHunks,
            formatHintfulDiff,
            output,
        ],
        'reverse-hintful-diff': [
            parseHintfulDiff,
            reverse,
            formatHintfulDiff,
            output,
        ],
        'reverse-unified-diff': [
            parseUnifiedDiff,
            reverse,
            formatUnifiedDiff,
            output,
        ],
        'validate-hintful-diff': [
            parseHintfulDiff,
            validateSnippets,
            groupHunks,
            validateHunks,
            sink,
        ],
        'validate-unified-diff': [
            parseUnifiedDiff,
            groupHunks,
            validateHunks,
            sink,
        ],
    }[os.path.basename(sys.argv[0])]
    def reducer(reduced, next_generator):
        return next_generator(reduced)
    functools.reduce(reducer, procStack, getInputLines())
main()
