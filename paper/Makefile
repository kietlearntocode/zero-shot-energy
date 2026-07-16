# Makefile for CTU Journal LaTeX paper
# Usage:
#   make          -> compile PDF (pdflatex + biber + pdflatex x2)
#   make clean    -> remove auxiliary files
#   make distclean -> remove all generated files including PDF

MAIN = main
LATEX = pdflatex
BIBER = biber

.PHONY: all clean distclean

all: $(MAIN).pdf

$(MAIN).pdf: $(MAIN).tex references.bib
	$(LATEX) -interaction=nonstopmode $(MAIN).tex
	$(BIBER) $(MAIN)
	$(LATEX) -interaction=nonstopmode $(MAIN).tex
	$(LATEX) -interaction=nonstopmode $(MAIN).tex
	@echo ""
	@echo "=== PDF compiled successfully: $(MAIN).pdf ==="

clean:
	rm -f $(MAIN).aux $(MAIN).bbl $(MAIN).bcf $(MAIN).blg
	rm -f $(MAIN).log $(MAIN).out $(MAIN).run.xml $(MAIN).toc
	rm -f $(MAIN)-blx.bib
	@echo "Auxiliary files removed."

distclean: clean
	rm -f $(MAIN).pdf
	@echo "PDF removed."
