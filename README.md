<p align=center><img align=center src='docs/goose.svg' width=600 /></p>
<h6 align=center>a daily newsfeed delivered to your remarkable tablet</h6>

<p align=center>
  <a href="https://pypi.org/project/goosepaper/"><img alt="PyPI" src="https://img.shields.io/pypi/v/goosepaper?style=for-the-badge"></a>
  <a href="https://github.com/j6k4m8/goosepaper/" alt="GitHub repo size"><img src="https://img.shields.io/github/repo-size/j6k4m8/goosepaper?style=for-the-badge" /></a>
  <a href="#" alt="GitHub last commit"><img src="https://img.shields.io/github/last-commit/j6k4m8/goosepaper?style=for-the-badge" /></a>
  <a href="#" alt="This repo is pretty dope."><img src="https://img.shields.io/badge/pretty%20dope-%F0%9F%91%8C-blue?style=for-the-badge" /></a>
  <a href="#" alt="This repo is licensed under Apache 2.0"><img src="https://img.shields.io/github/license/j6k4m8/goosepaper?style=for-the-badge" /></a>
</p>

## what's up

goosepaper is a utility that delivers a daily newspaper to your remarkable tablet. that's cute!

you can include RSS feeds, Twitter feeds, news articles, wikipedia articles-of-the-day, weather, and more. I read it when I wake up so that I can feel anxious without having to get my phone.

## get started with docker

By far the easiest way to get started with Goosepaper is to use Docker.

### step 0: write your config file

Write a config file to tell Goosepaper what news you want to read. An example is provided in `example-config.json`.

### step 1: generate your paper

From the directory that has the config file in it, run the following:

```shell
docker run -it --rm -v $(pwd):/goosepaper j6k4m8/goosepaper goosepaper -c example-config.json
```

(where `example-config.json` is the name of the config file to use).

### step 2: you are done!

If you want to both generate the PDF as well as upload it to your reMarkable tablet, you can pass the `--upload` flag to the docker command above. You must additionally mount your `~/.rmapy` file:

```shell
docker run -it --rm -v $(pwd):/goosepaper -v $HOME/.rmapy:/root/.rmapy j6k4m8/goosepaper goosepaper -c example-config.json --upload
```

Otherwise, you can now email this PDF to your tablet, perhaps using [ReMailable](https://github.com/j6k4m8/remailable).

## get started without docker: installation

### dependencies:

this tool uses `weasyprint` to generate PDFs. You can install all of the python libraries you need with `pip3 install -r ./requirements.txt` from this repo, but you may need these prerequisites before getting started.

more details [here](https://weasyprint.readthedocs.io/en/latest/install.html).

#### mac:

```shell
brew install cairo pango gdk-pixbuf libffi
```

#### ubuntu-flavored:

```shell
sudo apt-get install build-essential python3-dev python3-pip python3-setuptools python3-wheel python3-cffi libcairo2 libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 libffi-dev shared-mime-info
```

#### windows:

[Follow these instructions carefully](https://weasyprint.readthedocs.io/en/latest/install.html#windows).

## and then:

From inside the goosepaper repo,

```shell
pip3 install -e .
```

## get started

You can customize your goosepaper by editing `config.json`. (More instructions, and customization tools, all coming soon!)

```shell
goosepaper --config myconfig.json --output mypaper.pdf
```

If you don't pass an output flag, one will be generated based upon the time of generation. You DO need to pass a config file for now.

An example config file is included here: [example-config.json](example-config.json).

---

Check out [this example PDF](https://github.com/j6k4m8/goosepaper/blob/master/docs/Example-Nov-1-2020.pdf), generated on Nov 1 2020.

## existing story providers ([want to write your own?](https://github.com/j6k4m8/goosepaper/blob/master/CONTRIBUTING.md))

-   [Wikipedia Top News / Current Events](https://github.com/j6k4m8/goosepaper/blob/master/goosepaper/__init__.py#L112)
-   [Tweets](https://github.com/j6k4m8/goosepaper/blob/master/goosepaper/__init__.py#L154) (Note: Currently borked, see [Issue #5](https://github.com/j6k4m8/goosepaper/issues/5))
-   [Weather](https://github.com/j6k4m8/goosepaper/blob/master/goosepaper/__init__.py#L258). These stories appear in the "ear" of the front page, just like a regular ol' newspaper
-   [RSS Feeds](https://github.com/j6k4m8/goosepaper/blob/master/goosepaper/__init__.py#L283)
-   [Reddit Subreddits](https://github.com/j6k4m8/goosepaper/blob/master/goosepaper/__init__.py#L307)

# More Questions, Infrequently Asked

### yes but pardon me — i haven't a remarkable tablet

Do you have another kind of tablet? You may generate a print-ready PDF which you can use on another kind of robot as well! Just remove the last line of `main.py`.

### very nice! may i have it in comic sans?

yes! you may do anything that you find to be fun and welcoming :)

Check out the `styles.Styles` enum in the goosepaper library. You will find there what you seek.

### do all dogs' names start with the letter "B"?

I do not think so, but it is a good question!

### may i use this to browse twitter?

yes you may! you can add a list of usernames to the feed generator and it will make a print-ready version of twitter. this is helpful for when you are on twitter on your laptop but wish you had Other Twitter as well, in print form.

# You May Also Like...

-   [remailable](https://github.com/j6k4m8/remailable): Email PDF documents to your reMarkable tablet
