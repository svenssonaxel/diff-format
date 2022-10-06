all: \
 ../img/compat-format-example.compat.diff.highlighted.png \
 ../img/compat-format-example.converted-from-compat.hintful.diff.visualized.png \
 ../img/minified-js-refactor.converted-from-hintful.unified.diff.highlighted.png \
 ../img/minified-js-refactor.hintful.diff.highlighted.png \
 ../img/minified-js-refactor.hintful.diff.visualized.png \
 ../img/mixing-hunk-formats.hintful.diff.highlighted.png \
 ../img/simple-js-refactor-with-snippets.hintful.diff.visualized.png \
 ../img/simple-python-stepwise.hintful.diff.highlighted.png \
 ../img/simple-python-stepwise.hintful.diff.visualized.png \
 ../img/simple-python.hintful.diff.highlighted.png \
 ../img/simple-python.hintful.diff.visualized.png \
 ../img/simple-python.unified.diff.highlighted.png \

../img/%.png: %.dvi ../img
# Exclude some chunks to make png images reproducible and independent of LaTeX page size.
	convert \
		-density 300 \
		-quality 100 \
		-colorspace RGB \
		-define png:exclude-chunks=canv,date,text,time,ztxt \
		$< $@
# Check that input .dvi was only one page
	[ -f $@ ]
%.dvi: %.tex
	trap "rm $*.aux $*.log" EXIT; latex -halt-on-error -interaction=nonstopmode -output-comment "" $<
%.tex: %.content.tex prelude.tex
	cat prelude.tex $< > $@
	printf '\\end{document}' >> $@
%.hintful.diff.visualized.content.tex: %.hintful.diff ../implementations/python3/implementation.py
	../implementations/python3/validate-hintful-diff < $<
	./latex-visualize-diff < $< > $@
%.hintful.diff.highlighted.content.tex: %.hintful.diff ../implementations/python3/implementation.py
	../implementations/python3/validate-hintful-diff < $<
	./latex-highlight-diff < $< > $@
%.compat.diff.visualized.content.tex: %.compat.diff ../implementations/python3/implementation.py
	../implementations/python3/validate-compat-diff < $<
	./latex-visualize-diff < $< > $@
%.compat.diff.highlighted.content.tex: %.compat.diff ../implementations/python3/implementation.py
	../implementations/python3/validate-compat-diff < $<
	./latex-highlight-diff < $< > $@
%.unified.diff.highlighted.content.tex: %.unified.diff ../implementations/python3/implementation.py
	../implementations/python3/validate-unified-diff < $<
	./latex-highlight-diff < $< > $@
%.converted-from-hintful.unified.diff: %.hintful.diff ../implementations/python3/implementation.py
	../implementations/python3/validate-hintful-diff < $<
	../implementations/python3/convert-hintful-diff-to-unified-diff < $< > $@
%.converted-from-compat.hintful.diff: %.compat.diff ../implementations/python3/implementation.py
	../implementations/python3/validate-compat-diff < $<
	../implementations/python3/convert-compat-diff-to-hintful-diff < $< > $@
../img:
	mkdir ../img
.PHONY: all
