class Style:
    def get_stylesheets(self) -> list:
        ...

    def get_css(self, font_size: str = "14pt"):
        ...


class AutumnStyle(Style):
    def get_stylesheets(self) -> list:
        return [
            "https://fonts.googleapis.com/css?family=Oswald",
            "https://fonts.googleapis.com/css?family=Playfair+Display",
        ]

    def get_css(self, font_size: str = "14pt"):
        return (
            """
        @page {
            margin-top: 0.5in;
            margin-right: 0.2in;
            margin-left: 0.65in;
        }

        body {
            font-family: "Playfair Display";
        }

        .header {
            padding: 1em;
            height: 10em;
        }

        .header div {
            float: left;
            display: block;
        }

        .header .ear {
            float: right;
        }

        ul, li, ol {
            margin-left: 0; padding-left: 0.15em;
        }

        .stories {
            font-size: """
            + font_size
            + """;
        }

        .ear article {
            border: 1px groove black;
            padding: 1em;
            margin: 1em;
            font-size: 11pt;
        }
        .ear article h1 {
            font-family: "Playfair Display";
            font-size: 10pt;
            font-weight: normal;
        }

        article {
            text-align: justify;
            line-height: 1.25em;
        }

        .longform {
            page-break-after: always;
        }

        article>h1 {
            font-family: "Oswald";
            font-weight: 400;
            font-size: 23pt;
            text-indent: 0;
            margin-bottom: 0.25em;
            line-height: 1.2em;
            text-align: left;
        }
        article>h1.priority-low {
            font-family: "Oswald";
            font-size: 18pt;
            font-weight: 400;
            text-indent: 0;
            border-bottom: 1px solid #dedede;
            margin-bottom: 0.15em;
        }

        article>h4.byline {
            font-family: "Oswald";
            font-size: 12pt;
            font-weight: 400;
            text-indent: 0;
            border-bottom: 1px solid #dedede;
        }

        article>h3 {
            font-family: "Oswald";
            font-weight: 400;
            font-size: 18pt;
            text-indent: 0;
        }

        section>h1,
        section>h2,
        section>h3,
        section>h4,
        section>h5 {
            border-left: 5px solid #dedede;
            padding-left: 1em;
        }

        figure {
            border: 1px solid black;
            text-indent: 0;
            width: auto;
        }

        .stories article.story img {
            width: 100%;
        }

        figure>span {
            font-size: 0;
        }

        .row {
            column-count: 2;
        }

        """
        )
