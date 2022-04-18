## *Function* `__init__(self)`


Creates a new MultiParser, which abstracts acessing command line arguments and config file entries.



## *Function* `argumentOrConfig(self, key, default=None, dependency=None)`


Returns a command line argument or an entry from the config file

### Arguments
> - **key** (`None`: `None`): the command line option name (as in --key) or config entry
> - **default** (`str`: `None`): the default value, returned if the key was not
        set both as a command line argument and a config entry
> - **dependency** (`str`: `None`): the name of a dependency command line
        argument or config entry that must be present for this call to         be valid

### Returns
    If a command line option with 'key' name was set, returns it. Else,
        if a config entry named 'key' was set, returns it. If none of         the previous was returned, returns the default value specified         by the 'default' argument.

