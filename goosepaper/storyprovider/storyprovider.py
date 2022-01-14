import abc
from typing import List
from ..story import Story


class StoryProvider(abc.ABC):
    """
    An abstract class for a class that provides stories to be rendered.
    """

    def get_stories(self, limit: int = 5) -> List["Story"]:
        """
        Get a list of stories from this Provider.
        """
        ...


class LoremStoryProvider(StoryProvider):
    def __init__(self, limit: int = 5):
        self.text = [
            "Lorem ipsum! dolor sit amet, consectetur adipiscing elit. Duis eget velit sem. In elementum eget lorem non luctus. Vivamus tempus justo in pulvinar ultrices. Aliquam ac maximus leo. Quisque ipsum sapien, vestibulum viverra tempus ac, vestibulum quis justo. Nullam ut purus varius, bibendum metus ac, viverra enim. Phasellus sodales ullamcorper sapien pretium tristique. Duis dapibus felis quis tincidunt ultrices. Etiam purus sapien, tincidunt ac turpis vel, eleifend placerat enim. In sed mauris justo. Suspendisse ac tincidunt nunc. Nullam luctus porta pretium. Donec porttitor, nulla ut finibus pretium, augue turpis posuere ante, ac congue nunc nulla eu nisl. Phasellus imperdiet vel augue id gravida.",
            "Morbi mattis egestas quam, in tempus elit efficitur sagittis. Sed in maximus lorem. Aliquam erat volutpat. Phasellus mattis varius velit, vitae varius justo. Sed imperdiet eget dolor non consequat. Cras non felis neque. Nam eget arcu sapien. Morbi ultrices tristique cursus. Sed tempor ex lorem, vel ultrices sem placerat non. Nullam tortor arcu, imperdiet id lobortis a, commodo nec mi. Duis rhoncus in est sit amet tristique. Mauris condimentum nisl a erat tristique, id dictum risus euismod. Phasellus at sapien ante. Morbi facilisis tortor id leo porta, condimentum mollis dolor suscipit.",
            "Phasellus ut nibh vitae turpis congue venenatis. Morbi mollis justo dolor, ac finibus erat suscipit vitae. Donec libero erat, luctus quis sapien vel, sagittis dapibus est. Ut non quam et nisl hendrerit sodales. Pellentesque habitant morbi tristique senectus et netus et malesuada fames ac turpis egestas. Integer sodales ut augue a lacinia. Phasellus mattis sapien eget nibh auctor porttitor. Sed feugiat consectetur risus, a tempus ipsum scelerisque eu. Maecenas suscipit erat quis neque vulputate, ornare vehicula tellus lobortis. Duis tempor elit scelerisque ex tincidunt imperdiet. Curabitur dictum condimentum turpis, vitae ultrices ante sodales a. Praesent eu erat nec odio placerat placerat. Sed et dolor augue.",
            "Curabitur consectetur, nisi eget consequat ultrices, erat ante tincidunt ipsum, eget varius mauris turpis ac enim. Vivamus rutrum condimentum metus ut egestas. Nulla consectetur tincidunt laoreet. Vivamus tortor sem, imperdiet sodales facilisis quis, elementum nec erat. Curabitur imperdiet, nulla vel mattis gravida, risus eros sollicitudin magna, nec feugiat mauris mauris eu lorem. In hac habitasse platea dictumst. Sed tincidunt facilisis sem, non commodo metus volutpat nec. Fusce nulla mauris, vulputate sit amet magna id, blandit ornare leo. Nam vel faucibus ipsum, ac congue dolor.",
            "Vivamus pretium purus vel libero finibus blandit. Donec vitae nisl sollicitudin, consectetur nunc ac, volutpat libero. Maecenas ac leo ut velit viverra aliquet non id turpis. Morbi ut euismod erat. Vestibulum congue sed erat nec dapibus. Donec semper consectetur vestibulum. Praesent egestas dolor a ante sodales maximus. Suspendisse a odio vitae odio sagittis sollicitudin in quis massa. Praesent at convallis nulla. Mauris a nisl tincidunt, iaculis lacus eget, lobortis sapien. Nullam condimentum neque quis nisi consequat, eget accumsan tellus fermentum. Quisque dictum, nunc et pretium accumsan, lacus eros pharetra odio, ac euismod orci lorem sed turpis. ",
        ]
        self.limit = limit

    def get_stories(self, limit: int = 5, **kwargs) -> List[Story]:
        return [
            Story(headline="Lorem Ipsum Dolor Sit Amet", body_text=self.text)
            for _ in range(min(self.limit, limit))
        ]
