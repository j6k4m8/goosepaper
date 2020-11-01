#!/bin/bash

PATH=/usr/bin /usr/local/bin/pandoc -r html $(pwd)/temp/daily.html -V fontsize=12pt -V geometry:"top=2cm, bottom=1.5cm, left=3cm, right=3cm" --latex-engine=/Library/TeX/texbin/xelatex -o $(pwd)/temp/daily.pdf
