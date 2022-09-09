all: \
 ../img/minified-js-refactor.hintful.diff.highlighted.png \
 ../img/minified-js-refactor.hintful.diff.visualized.png \
 ../img/minified-js-refactor.converted-from-hintful.unified.diff.highlighted.png \
 ../img/simple-js-refactor-with-snippets.hintful.diff.visualized.png \
 ../img/simple-python-twostep.hintful.diff.visualized.png \
 ../img/simple-python.hintful.diff.highlighted.png \
 ../img/simple-python.hintful.diff.visualized.png \
 ../img/simple-python.unified.diff.highlighted.png \

../img/%.png: %.dvi ../img
	convert \
		-quality 300 \
		-colorspace RGB \
		-trim \
		-border 10 \
		-bordercolor white \
		-define png:exclude-chunks=canv,date,phys,text,time,ztxt \
		$< $@ # Exclude some chunks to make png images reproducible and independent of LaTeX page size.
	[ -f $@ ] # Check that input .dvi was only one page
%.dvi: %.tex
	latex -halt-on-error $<
	rm $*.aux $*.log
%.tex: %.content.tex prelude.tex
	cat prelude.tex $< > $@
	printf '\\end{document}' >> $@
%.hintful.diff.visualized.content.tex: %.hintful.diff ../implementations/python3/implementation.py
	../implementations/python3/validate-hintful-diff < $<
	./latex-visualize-diff < $< > $@
%.hintful.diff.highlighted.content.tex: %.hintful.diff ../implementations/python3/implementation.py
	../implementations/python3/validate-hintful-diff < $<
	./latex-highlight-diff < $< > $@
%.unified.diff.highlighted.content.tex: %.unified.diff ../implementations/python3/implementation.py
	../implementations/python3/validate-unified-diff < $<
	./latex-highlight-diff < $< > $@
%.converted-from-hintful.unified.diff: %.hintful.diff ../implementations/python3/implementation.py
	../implementations/python3/validate-hintful-diff < $<
	../implementations/python3/convert-hintful-diff-to-unified-diff < $< > $@
../img:
	mkdir ../img
.PHONY: all
