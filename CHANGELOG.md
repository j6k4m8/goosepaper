# CHANGELOG

### **???** (Unreleased)

> This version adds a test suite and improvements to the upload mechanism.

-   Improvements
    -   Add test suite
    -   Improvements to upload mechanism
    -   Add possibility to set title and subtile in config file - contribution by @traysh
    -   Parallelize fetching RSS stories - contribution by @traysh
    -   Add flag to allow replacing documents in remarkable cloud - contribution by @traysh
    -   Add class to resolve options both from command line and config file - contribution by @traysh

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
