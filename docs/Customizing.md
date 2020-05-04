# Customizing Your Feed

You can choose what content is added to your daily goosepaper by rewriting the Goosepaper constructor. Check it out:

```python
from goosepaper import TwitterStoryProvider, Goosepaper

Goosepaper([
    TwitterStoryProvider("j6m8", limit=100),
    TwitterStoryProvider("reuters", limit=100),
])
```

