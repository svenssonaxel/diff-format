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
        'fg': "stdfg",
        'bold': False,
        'bg': "stdbg",
    }
    currentColorization=noColorization
    for obj in inputObjs:
        if(type(obj)==str):
            yield latexEscape(obj)
        elif(type(obj)==dict and obj['op']=='colorize'):
            obj={**obj}
            if(obj['bg']=="stdfg" and obj['fg']!="stdbg"):
                obj['fg']="light"+obj['fg']
            if not(obj['bg'].startswith("std")):
                obj['bg']="light"+obj['bg']
            if not((currentColorization['fg']=="stdfg" or obj['fg']) and
                   currentColorization['bold'] in [False, obj['bold']] and
                   currentColorization['bg'] in ["stdbg", obj['bg']]):
                yield contextEnd
                contextEnd=""
                currentColorization=noColorization
            if(obj['fg'] and obj['fg']!= currentColorization['fg']):
                yield from [r"\fg{", obj['fg'], r"}{"]
                contextEnd+="}"
            if(obj['bold'] and obj['bold']!= currentColorization['bold']):
                yield r"\bold{"
                contextEnd+="}"
            if(obj['bg'] and obj['bg']!=currentColorization['bg']):
                yield from [r"\bg{", obj['bg'], r"}{"]
                contextEnd+="}"
            currentColorization=obj
        elif(type(obj)==dict and obj['op']=='bar'):
            yield r"{\Bar}"
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
