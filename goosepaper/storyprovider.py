import abc


class StoryProvider(abc.ABC):
    """
    An abstract class for a class that provides stories to be rendered.
    """

    def get_stories(self, limit: int = 5):
        """
        Get a list of stories from this Provider.
        """
        ...

