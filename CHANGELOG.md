# CHANGELOG

### **0.2.0**

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
