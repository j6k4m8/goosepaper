#!/bin/bash

PATH=/usr/bin /usr/local/bin/pandoc -r html daily.html -V fontsize=12pt -V geometry:"top=2cm, bottom=1.5cm, left=5cm, right=1cm" --latex-engine=/Library/TeX/texbin/xelatex -o "daily.pdf"
