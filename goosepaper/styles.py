import pathlib


def read_stylesheets(path: pathlib.Path) -> list:
    if (path/"stylesheets.txt").is_file():
        return (path / "stylesheets.txt").read_text()\
            .strip("\n").split("\n")
    else:
        return []

def read_css(path: pathlib.Path):
    return (path / "stylesheet.css") \
        .read_text()

class Style:
    def get_stylesheets(self) -> list:
        return getattr(self,"__stylesheets__","")

    def get_css(self, font_size: int = None):
        font_size=str(font_size)
        if font_size:
            self.__css__+= f"""
        .stories {{
            font-size: {font_size}pt !important; 
        }}
        article>h4.byline {{
            font-size: {font_size}pt !important; 
        }}
        """
        return getattr(self, "__css__", "")

    def read_style(self, path):
        path = pathlib.Path("./styles/") / path
        self.__stylesheets__ = read_stylesheets(path)
        self.__css__ = read_css(path)

    def __init__(self, path = ''):
        try:
            self.read_style(path)
        except FileNotFoundError:
            if path:
                print(f"Oops! {path} style not found. Use default style.")
            else:
                self.read_style('FifthAvenue')
        return


