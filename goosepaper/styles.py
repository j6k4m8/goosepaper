class Styles:

    Autumn = """
    @import 'https://fonts.googleapis.com/css?family=Oswald';
    @import 'https://fonts.googleapis.com/css?family=Merriweather';

    * {
        box-sizing: border-box;
    }

    body {
        font-family: "Merriweather";
    }

    @media print {
        body {
            font-size: 90%;
            margin: 0;
            padding: 0;
        }
    }

    @page {
        size: 8.5in 11in;
        margin: 0.5in 0.2in 0.1in 0.5in;
    }

    .header {
        width: 100%;
        margin: 1em;
        padding: 1em;
        font-size: 1.5em;
        display: grid;
        grid-template-columns: auto auto auto;
    }

    .ear article {
        border: 1px groove black;
        padding: 1em;
        margin: 1em;
        font-size: 11pt;
    }
    .ear article h1 {
        font-family: "Merriweather";
        font-size: 10pt;
        font-weight: normal;
    }

    .stories {
        column-count: 2;
        column-gap: 2em;
        column-width: 16em;
        margin: 1em;
    }

    article {
        font-size: 12pt;
        text-align: justify;
        text-indent: 3em;
        line-height: 1.45em;
    }

    .longform {
        page-break-after: always;
    }

    article>h1 {
        font-family: "Oswald";
        font-size: 23pt;
        text-indent: 0;
        margin-bottom: 0.25em;
    }
    article>h1.priority-low {
        font-family: "Oswald";
        font-size: 18pt;
        font-weight: normal;
        text-indent: 0;
        border-bottom: 1px solid #dedede;
        margin-bottom: 0.15em;
    }

    article>h4.byline {
        font-family: "Oswald";
        font-size: 12pt;
        font-weight: normal;
        text-indent: 0;
        border-bottom: 1px solid #dedede;
    }

    article>h3 {
        font-family: "Oswald";
        font-weight: normal;
        font-size: 13pt;
        text-indent: 0;
    }

    section>h1,
    section>h2,
    section>h3,
    section>h4,
    section>h5 {
        /* font-size: 0.8em; */
        border-left: 5px solid #dedede;
        padding-left: 1em;
    }

    figure {
        border: 1px solid black;
        padding: 2em;
        float: right;
        width: 50%;
    }

    figure>img {
        width: 100%;
    }

    figure>span {
        font-size: 0;
    }
    """
