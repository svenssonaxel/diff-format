#!/usr/bin/env python3
import functools, os, sys
sys.path.append("../implementations/python3")
from implementation import m, main, nextOrDie, output

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

def getProcStack():
    procStack={
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
    return procStack
if __name__ == "__main__":
    main(getProcStack())
