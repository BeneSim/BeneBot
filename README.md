# BeneBot

BeneSim is a very simple and thus pretty easy to use python twitch bot. The code is quite ugly, but it does what it's supposed to do. The main purpose of the bot is to respond to *trigger phrases*. For example say you want a bot that posts a link to your discord server everytime a user uses the keyword *discord* in his message. This can be accomplished with the following code

```python
def discordCommand(bot, nickname, channel, args, message):
    bot.sendMessage(channel, "Join my discord server at http://foo.bar")
    
bot.addCommand(discordCommand, "discord", starts_with=False, case_sensitive=False)
```

# Installation
Actually no installation required, it's just a simple python module, just use it right away or import it into your own module. I may add a setup.py in the future though.

# Usage
Let's start with the initialization first. You can use it inside your module
```python
from benebot import Bot
```
or simply use the module itself
```python
if __name__ == "__main__":
    bot = Bot(username="botusername", password="oauth:botpassword", channels=(("#foo", 20), ("#bar", 20)))
```

Alright, **username** and **password** should be self-explanatory. **channels** must be an iterable, e.g. a list or tuple, in this case I used a tuple. Each entry of the tuple contains the channelname and the message limit and must be a iterable, too. In this case I want to joint the channel *#foo* with a message limit of 20 and the channel *#bar* with a message limit of 20. The message limit is the total number of messages that can be send to the specific channel within a time frame of 30 seconds. You may get an 8h IP ban if you send more messages than you are allowed to.

Now let's define a command. All commands need a function that gets called once the command gets triggered.
```python
def exampleCommand(bot, nickname, channel, args):
    bot.sendMessage(channel, "Command called by {} in channel {} with arguments {}".format(nickname, channel, args))
```
The signature of the command functions must always be as shown above. The individual parameters will be supplied by the bot once the command triggers:

 * **bot**: This is a reference to the bot, mainly used to send messages.
 * **nickname**: The nickname of the user that triggered the command.
 * **channel**: The channel the user triggered the command in.
 * **args**: This is an array containing all the words (seperated by a whitespace) that followed the command.
 * **message**: This is the original complete message.

Now that we have the desired functionality inside the command function lets add it to the bot.
```python
bot.addCommand(function=exampleCommand, trigger="example", nicknames=None, channels=None, case_sensitive=False, starts_with=True, cooldown=None)
```
OK, lets go over all those parameters:

 * **function**: The function that is going to be called when the command triggers.
 * **trigger**: The actual trigger phrase.
 * **nicknames**: **None** or an iterable if you want to restrict the command to some specific nicknames. Say you only want to allow a specific nickname "foobar" to use the command then you would use *nicknames=("foobar",)*.
 * **channels**: Same as with *nicknames*. **None** or an iterable containing the channels for which the command should be available.
 * **case_sensitive**: Whether the trigger phrase should be case sensitive or not.
 * **starts_with**: If true then the command will only trigger if the trigger phrase is the start of the message.
 * **cooldown**: **None** or the amount of seconds the command should be put on cooldown after usage.

The bot will now call the function **exampleCommand** everytime a user writes **example** or **ExAmple**, etc. at the beginning of a message. 

Finnaly we need to start the bot.
```python
bot.connect()
bot.run()
```

A minimal working example should look like this
```python
from benebot import Bot

def exampleCommand(bot, nickname, channel, args, message):
    bot.sendMessage(channel, "Command called by {} in channel {} with arguments {}".format(nickname, channel, args))
    
if __name__ == "__main__":
    bot = Bot(username="botusername", password="oauth:botpassword", channels=(("#foo", 20), ("#bar", 20)))
    bot.addCommand(function=exampleCommand, trigger="example", nicknames=None, channels=None, case_sensitive=False, starts_with=True, cooldown=None)
    bot.connect()
    bot.run()
```
**Important**: BeneBot uses blocking sockets! A bot using asyncio for asynchronous networking may follow.

I hope this *tutorial* will help get you started. Have a look at the module itself, atleast the user-code part contains some documentation.
