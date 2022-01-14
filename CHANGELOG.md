# CHANGELOG

### **0.5.0** (January 14 2022)

-   Improvements

    -   RSS stories now "fall back" gracefully on just rendering the title, if the full body cannot be rendered. This is in contrast with the old behavior, in which the story would not be rendered at all.
    -   RSS, Reddit, and Twitter story providers now support a `since_days_ago` argument in their `config` dictionaries that enables you to specify how many days ago to start the search for stories. Older stories will not be included.
    -   Add support for multiple styles, using the `"styles" config option. Options are `"Academy"`, `"FifthAvenue"`, and `"Autumn"`. Previous style (before v0.4.0) was `Autumn`.

-   Housekeeping

    -   Moved the story providers into their own submodule: Note that this may break backward compatibility if you import these directly.

### **0.4.0** (January 13 2022)

> Multiple fixes and improvements

-   Fixes

    -   Changed some document name comparisons to case insensitive (prevent document overwrites, esp. for Windows users)
    -   Switched upload to require named arguments rather than positional
    -   Fixes the `limit` arg in the RSS provider, which was being ignored

-   Improvements

    -   Improve typing support
    -   Added more error handling for file and syntax handling
    -   Change to using the `VissibleName` attribute in all cases rather than filename
    -   Added code for upcoming additional sanity checks
    -   Added more information on how to customize your goospaper in the docs, @kwillno (#54)
    -   Adds the option to provide a global config (thanks @sedennial! #48)
    -   Lots of new options to customize the upload and generation process (thanks @sedennial! #48)

-   Housekeeping

    -   Fixes a bunch of flake8 errors and warnings to keep things tidy

### **0.3.1** (April 29 2021)

> This version adds a test suite and improvements to the upload and config mechanisms, as well as several more performance and feature improvements.

-   Improvements
    -   Add test suite
    -   Improvements to upload mechanism
    -   Add possibility to set title and subtile in config file - contribution by @traysh
    -   Parallelize fetching RSS stories - contribution by @traysh
    -   Add flag to allow replacing documents in remarkable cloud - contribution by @traysh
    -   Add class to resolve options both from command line and config file - contribution by @traysh
    -   Allow uploading to a folder in remarkable cloud

### **0.3.0** (November 27 2020)

> Some major codebase reorganization, thanks to @sterlingbaldwin. Thank you!!

-   Bugfixes
    -   Fixed Twitter story provider; we're back in business!
-   Improvements
    -   RSS stories are now downloaded in full (when available) — thanks again @sterlingbaldwin!
    -   Specify your weather preferences in C/F units
    -   Added a Docker image! Generate your goosepapers in a box!

### **0.2.0** (November 27 2020)

> This release converts Goosepaper to a Python module. You can now call it from the command-line with `goosepaper`. See `goosepaper --help` for more details.

-   Improvements
    -   Use Goosepaper as a library, or use it as a command-line tool. Both work now! (#11)
    -   Read a config file from disk in order to build a list of story providers, rather than having to hard-code it. (#11)

### **0.1.0** (November 8 2020)

> This is the last release of Goosepaper before it was converted into a Python module. If you are still using Goosepaper as a script, this is the version for you. Please update as soon as possible!

-   Improvements
    -   Weather
        -   Optionally record the weather temperature in Celsius. Thanks @kwillno! (#10)
    -   RSS
        -   Don't break on RSS feeds that lack images. Thanks again, @kwillno! (#10)
