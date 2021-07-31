#!/usr/bin/env python3
import functools, sys, re

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
            yield from {'unified': parseUnifiedHunk, 'iterative': parseIterativeHunk}[mode](line, inputLines)
            continue
        linem = m(r'^--- (.*)\n$', line)
        if(linem):
            line2 = next(inputLines)
            line2m = m(r'^\+\+\+ (.*)\n$', line2 or '')
            if not line2 or not line2m:
                die('Expected a +++ line')
            yield {
                'op': 'labels',
                'left': linem[1],
                'right': line2m[1],
                }
            continue
        linem = m(r'^rename from (.*)\n$', line)
        if(linem):
            line2 = next(inputLines)
            line2m = m(r'^rename to (.*)\n$', line2 or '')
            if not line2 or not line2m:
                die('Expected a "rename to" line')
            yield {
                'op': 'rename',
                'left': linem[1],
                'right': line2m[1],
                }
            continue
        if(m({'unified': r'^[-+ ].*', 'iterative': r'^[-+ _#<>].*'}[mode], line)):
           die('Hunk content without header')
        linem = m(r'^index ([0-9a-f]{7,})\.\.([0-9a-f]{7,}) +([0-7]{6})\n$', line)
        if(linem):
            yield {
                'op': 'index',
                'left': linem[1],
                'right': linem[2],
                'mode': linem[3],
            }
            continue
        linem = m(r'^(new|deleted) file mode (.*)\n$', line)
        if(linem):
            yield {
                'op': f'{linem[1]}filemode',
                'mode': linem[2],
            }
            continue
        linem = m(r'^(Reverse of: )?diff --git .*\n$', line)
        if(linem):
            yield {
                'op': f'difftitle',
                'line': line,
            }
            continue
        die(f'Cannot parse line {line}')
def parseIterativeDiff(inputLines): yield from parseDiff(inputLines, 'iterative')
def parseUnifiedDiff(inputLines): yield from parseDiff(glueNonewline(inputLines), 'unified')

def glueNonewline(inputLines):
    prevLine = ''
    for line in inputLines:
        if(m('^\\.*$', line)):
            yield prevLine + line
            prevLine = ''
        else:
            if prevLine:
                yield prevLine
            prevLine = line
    if prevLine:
        yield prevLine

def parseUnifiedHunk(header, inputLines):
    headerm = m(r'^@@( +)-([0-9]+)(,[0-9]+)?( +)\+([0-9]+)(,[0-9]+)?( +)@@(.*)\n$', header)
    if(not headerm):
        die('Corrupt hunk header')
    ws1 = headerm[1]
    leftstartlineraw = headerm[2]
    leftlinecountraw = headerm[3]
    ws2 = headerm[4]
    rightstartlineraw = headerm[5]
    rightlinecountraw = headerm[6]
    ws3 = headerm[7]
    comment = headerm[8]
    leftstartline = int(leftstartlineraw)
    rightstartline = int(rightstartlineraw)
    leftlinecount = int(leftlinecountraw[1:] if leftlinecountraw else '0')
    rightlinecount = int(rightlinecountraw[1:] if rightlinecountraw else '0')
    yield {
        'op': 'beginhunk',
        'ws1': ws1,
        'leftstartlineraw': leftstartlineraw,
        'leftlinecountraw': leftlinecountraw,
        'ws2': ws2,
        'rightstartlineraw': rightstartlineraw,
        'rightlinecountraw': rightlinecountraw,
        'ws3': ws3,
        'comment': comment,
        'leftstartline': leftstartline,
        'rightstartline': rightstartline,
        'leftlinecount': leftlinecount,
        'rightlinecount': rightlinecount,
    }
    while(0 < leftlinecount or 0 < rightlinecount):
        if(leftlinecount < 0 or rightlinecount < 0):
            die('Corrupt hunk line count')
        line = next(inputLines)
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
        die('Corrupt hunk')
    yield {
        'op': 'endhunk',
    }

def parseIterativeHunk(header, inputLines):
    headerm = m(r'^@@( +)-([0-9]+)(,[0-9]+)?( +)\(([0-9]+)\)( +)\+([0-9]+)(,[0-9]+)?( +)@@(.*)\n$', header)
    if(not headerm):
        die('Corrupt hunk header')
    ws1 = headerm[1]
    leftstartlineraw = headerm[2]
    leftlinecountraw = headerm[3]
    ws2 = headerm[4]
    hunklinecountraw = headerm[5]
    ws3 = headerm[6]
    rightstartlineraw = headerm[7]
    rightlinecountraw = headerm[8]
    ws4 = headerm[9]
    comment = headerm[10]
    leftstartline = int(leftstartlineraw)
    rightstartline = int(rightstartlineraw)
    leftlinecount = int(leftlinecountraw[1:] if leftlinecountraw else '0')
    rightlinecount = int(rightlinecountraw[1:] if rightlinecountraw else '0')
    hunklinecount = int(hunklinecountraw)
    yield {
        'op': 'beginhunk',
        'ws1': ws1,
        'leftstartlineraw': leftstartlineraw,
        'leftlinecountraw': leftlinecountraw,
        'ws2': ws2,
        'hunklinecountraw': hunklinecountraw,
        'ws3': ws3,
        'rightstartlineraw': rightstartlineraw,
        'rightlinecountraw': rightlinecountraw,
        'ws4': ws4,
        'comment': comment,
        'leftstartline': leftstartline,
        'rightstartline': rightstartline,
        'leftlinecount': leftlinecount,
        'rightlinecount': rightlinecount,
        'hunklinecount': hunklinecount,
    }
    linestoread=hunklinecount
    for line in inputLines:
        linestoread-=1
        linem = m(r'^([-+ _#])(.*)([$\\])\n$', line) or m(r'^([<>])(.*)\n$', line)
        if not linem:
            die(f'Corrupt hunk: Strange line: {line}')
        prefix = linem[1]
        content = linem[2]
        nlmarker = linem[3] if len(linem)==4 else ''
        contentWithNl = f'{content}\n' if nlmarker=='$' else content
        if(prefix in '-+ ' and not nlmarker):
            die('Corrupt hunk: Missing newline marker')
        if(prefix in '-+ _#'):
            yield {
                'op': {'-': 'leftcontent', '+': 'rightcontent', ' ': 'bothcontent', '_': 'bothlowprioritycontent', '#': 'ignorecontent'}[prefix],
                'content': contentWithNl,
            }
            continue
        if(prefix in '<>'):
            yield {
                'op':{'<': 'leftsnippet', '>': 'rightsnippet'}[prefix],
                'name': content,
            }
            continue
        die('This should never happen')
    if(not linestoread==0):
        die('Corrupt hunk')
    yield {
        'op': 'endhunk',
    }

def formatIterativeDiff(inputObjs):
    for obj in inputObjs:
        op=obj['op']
        if(op=='beginhunk'):
            yield from [
                '@@',
                obj['ws1'] or ' ',
                '-',
                obj['leftstartlineraw'],
                obj['leftlinecountraw'],
                obj['ws2'] or ' ',
                '(',
                obj['hunklinecountraw'],
                ')',
                obj['ws3'] or ' ',
                '+',
                obj['rightstartlineraw'],
                obj['rightlinecountraw'],
                (obj['ws4'] if 'ws4' in obj else obj['ws3']) or ' ',
                '@@',
                obj['comment'],
                '\n',
            ]
        elif(op.endswith('content')):
            yield {'leftcontent': '-', 'rightcontent': '+', 'bothcontent': ' ', 'bothlowprioritycontent': '_', 'ignorecontent': '#'}[op]
            content = obj['content']
            if content.endswith('\n'):
                yield content[:-1]
                yield '$\n'
            else:
                yield content
                yield '\\\n'
        elif(op.endswith('snippet')):
            yield from [
                {'leftsnippet': '<', 'rightsnippet': '>'}[op],
                obj['name'],
                '\n',
            ]
        elif(op=='endhunk'):
            pass
        elif(op=='labels'):
            yield f"--- {obj['left']}\n+++ {obj['right']}\n"
        elif(op=='difftitle'):
            yield obj['line']
        elif(op=='index'):
            yield f"index {obj['left']}..{obj['right']} {obj['mode']}\n"
        else:
            die(f'formatIterativeDiff cannot process operation {op}')

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
        elif(op=='bothcontent'):
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
        elif(op in ['labels', 'beginhunk', 'endhunk']):
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
                    if(var in ['leftcontent', 'bothcontent']):
                        state['leftended']=True
                    if(var in ['rightcontent', 'bothcontent']):
                        state['rightended']=True
            yield obj
        elif(op in ['labels', 'beginhunk']):
            yield obj
        else:
            die(f'collectLines cannot process operation {op}')

def formatUnifiedDiff(inputObjs):
    for obj in inputObjs:
        op=obj['op']
        if(op=='beginhunk'):
            yield from [
                '@@',
                obj['ws1'] or ' ',
                '-',
                obj['leftstartlineraw'],
                obj['leftlinecountraw'],
                obj['ws2'] or ' ',
                '+',
                obj['rightstartlineraw'],
                obj['rightlinecountraw'],
                (obj['ws4'] if 'ws4' in obj else obj['ws3']) or ' ',
                '@@',
                obj['comment'],
                '\n',
            ]
        elif(op.endswith('content')):
            yield {'leftcontent': '-', 'rightcontent': '+', 'bothcontent': ' ', 'bothlowprioritycontent': ' '}[op]
            yield obj['content']
            if not obj['content'].endswith('\n'):
                yield '\n\\ No newline at end of file\n'
        elif(op=='endhunk'):
            pass
        elif(op in ['labels']):
            yield f"--- {obj['left']}\n+++ {obj['right']}\n"
        elif(op=='difftitle'):
            yield obj['line']
        elif(op=='index'):
            yield f"index {obj['left']}..{obj['right']} {obj['mode']}\n"
        else:
            die(f'formatUnifiedDiff cannot process operation {op}')

def switchleftright(text):
    if(text.startswith('left')): return 'right'+text[4:]
    if(text.startswith('right')): return 'left'+text[5:]
    return text
def reverse(inputObjs):
    for obj in inputObjs:
        op=obj['op']
        if(op=='difftitle'):
            line=obj['line']
            yield {**obj, 'line': line[12:] if line.startswith('Reverse of: ') else 'Reverse of: ' + line}
        elif(m('^(left|right).*$', op)):
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

def countLines(inputObjs):
    for obj in inputObjs:
        if(obj['op']=='hunk'):
            hunklinecount = len(obj['contents'])
            yield {**obj, 'hunklinecount': hunklinecount, 'hunklinecountraw': str(hunklinecount)}
        else:
            yield obj

def validateHunks(inputObjs):
    for obj in inputObjs:
        op=obj['op']
        sidesallowed=(True, True)
        if(not op in ['difftitle', 'hunk', 'index', 'labels']):
            die(f'Operation {op} not allowed outside hunk')
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
        'convert-iterative-diff-to-unified-diff': [
            parseIterativeDiff,
            removeSnippets,
            collectLines,
            formatUnifiedDiff,
            output,
        ],
        'convert-unified-diff-to-iterative-diff': [
            parseUnifiedDiff,
            groupHunks,
            countLines,
            ungroupHunks,
            formatIterativeDiff,
            output,
        ],
        'reverse-iterative-diff': [
            parseIterativeDiff,
            reverse,
            formatIterativeDiff,
            output,
        ],
        'reverse-unified-diff': [
            parseUnifiedDiff,
            reverse,
            formatUnifiedDiff,
            output,
        ],
        'validate-iterative-diff': [
            parseIterativeDiff,
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
    }[sys.argv[1]]
    def reducer(reduced, next_generator):
        return next_generator(reduced)
    functools.reduce(reducer, procStack, getInputLines())
main()
