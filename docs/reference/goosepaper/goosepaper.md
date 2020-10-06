## *Function* `htmlize(text: str) -> str`


Generate HTML text from a text string, correctly formatting paragraphs etc.


## *Class* `StoryProvider(abc.ABC)`


An abstract class for a class that provides stories to be rendered.


## *Function* `get_stories(self, limit: int = 5)`


Get a list of stories from this Provider.


## *Class* `WikipediaCurrentEventsStoryProvider(StoryProvider)`


A story provider that reads from today's current events on Wikipedia.


## *Function* `get_stories(self, limit: int = 10) -> List[Story]`


Get a list of current stories from Wikipedia.


## *Function* `get_stories(self, limit: int = 10) -> List[Story]`


Get a list of stories.

Here, the headline is the @username, and the body text is the tweet.


## *Function* `get_stories(self, limit: int = 42) -> List[Story]`


Get a list of tweets where each tweet is a story.

### Arguments
> - **limit** (`int`: `15`): The maximum number of tweets to fetch

### Returns
> - **List[Story]** (`None`: `None`): A list of tweets

