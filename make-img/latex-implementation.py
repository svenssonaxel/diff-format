#!/usr/bin/env python3.9
import functools, os, sys
sys.path.append("../implementations/python3")
from implementation import die, formatDiffHelper, main, output

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
            "\n": "\\nl%\n",
        }.get(char, char)
    return ret

def formatDiffHighlight(inputObjs):
    yield from formatDiffHelper(inputObjs, "highlight")

def formatDiffVisualize(inputObjs):
    yield from formatDiffHelper(inputObjs, "visualize")

def formatLatex(inputObjs):
    contextEnd=""
    noColorization={
        'fg': None,
        'bold': False,
        'bg': None,
        'bg2': None,
    }
    currentColorization=noColorization
    for obj in inputObjs:
        if(type(obj)==str):
            yield latexEscape(obj)
        elif(type(obj)==dict and obj['op']=='colorize'):
            if not((currentColorization['fg']==None or obj['fg']) and
                   currentColorization['bold'] in [False, obj['bold']] and
                   (currentColorization['bg'], currentColorization['bg2']) in [(None, None), (obj['bg'], obj['bg2'])]):
                yield contextEnd
                contextEnd=""
                currentColorization=noColorization
            if(obj['fg'] and obj['fg']!= currentColorization['fg']):
                yield from [r"\fg{", obj['fg'], r"}{"]
                contextEnd+="}"
            if(obj['bold'] and obj['bold']!= currentColorization['bold']):
                yield r"\bold{"
                contextEnd+="}"
            if((obj['bg'] or obj['bg2']) and (obj['bg'], obj['bg2']) != (currentColorization['bg'], currentColorization['bg2'])):
                if(obj['bg2']):
                    yield from [r"\twobg{", obj['bg'], r"}{", obj['bg2'], r"}{"]
                else:
                    yield from [r"\bg{", obj['bg'], r"}{"]
                contextEnd+="}"
            currentColorization=obj
        elif(type(obj)==dict and obj['op']=='bar'):
            yield r"{\Bar}"
        elif(type(obj)==dict and obj['op']=='greybar'):
            yield r"\fg{grey}{\Bar}"
        else:
            die('Weird object in formatLatex')
    yield contextEnd

def getProcStack():
    procStack={
        'latex-highlight-diff': [
            formatDiffHighlight,
            formatLatex,
            output,
        ],
        'latex-visualize-diff': [
            formatDiffVisualize,
            formatLatex,
            output,
        ],
    }[os.path.basename(sys.argv[0])]
    return procStack
if __name__ == "__main__":
    main(getProcStack())
