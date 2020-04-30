class Styles:

    Autumn = """
    @import 'https://fonts.googleapis.com/css?family=Oswald';
    @import 'https://fonts.googleapis.com/css?family=Merriweather';

    body {
        font-family: "Merriweather";
    }

    @page {
        size: 5.5in 8.5in;
        padding: 2em 4em 1em;
    }

    article {
        font-size: 16pt;
        page-break-after: always;
    }

    article>h1 {
        font-family: "Oswald";
        font-size: 26pt;
    }

    article>h4 {
        font-family: "Oswald";
        font-size: 12pt;
    }

    section {
        font-size: 12pt;
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
