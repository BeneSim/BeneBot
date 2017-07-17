#   Copyright (C) 2017 Benjamin Isbarn.
#
#   This file is part of BeneBot.
#
#   BeneBot is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   BeneBot is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  Secommande the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with BeneBot.  If not, see <http://www.gnu.org/licenses/>.

import socket
import re
from datetime import datetime

class Bot():

    def __init__(self, username, password, channels):
        self.username = username
        self.password = password
        self.channels = {channel: {"limit": limit, "timestamps": []} for channel, limit in channels}
        self.commands = []
        self.subscription_hooks = []
        self.join_hooks = []
        self.socket = None

    def connect(self):
        if self.socket is None:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect(("irc.chat.twitch.tv", 6667))

            self.sendPassword()
            self.sendUsername()
            self.sendCapabilitiesRequest()

            print("Connected")

            for channel in self.channels:
                self.joinChannel(channel)


    def sendUsername(self):
        if self.socket is not None:
            self.socket.sendall("NICK {}\r\n".format(self.username))

    def sendPassword(self):
        if self.socket is not None:
            self.socket.sendall("PASS {}\r\n".format(self.password))

    def sendCapabilitiesRequest(self):
        if self.socket is not None:
            self.socket.sendall("CAP REQ :twitch.tv/membership\r\n")
            self.socket.sendall("CAP REQ :twitch.tv/tags\r\n")
            self.socket.sendall("CAP REQ :twitch.tv/commands\r\n")

    def joinChannel(self, channel):
        if self.socket is not None:
            self.socket.sendall("JOIN {}\r\n".format(channel))
            print("Joined channel {}".format(channel))

    def sendPong(self, server):
        if self.socket is not None:
            self.socket.sendall("PONG {}\r\n".format(server))
            print("Received PING. PONG!")

    def onMessage(self, nickname, channel, message, tags):

        for command in self.commands:
            current_time = datetime.now()

            if command["nicknames"] is not None and nickname not in command["nicknames"]:
                continue
            if command["channels"] is not None and channel not in command["channels"]:
                continue
            if command["cooldown"] is not None and channel in command["last_called"] and (current_time - command["last_called"][channel]).total_seconds() < command["cooldown"]:
                continue

            if command["starts_with"]:
                regex = "^(?P<trigger>{})(?P<args>.*)".format(command["trigger"])
            else:
                regex = ".*(?P<trigger>{})(?P<args>.*)".format(command["trigger"])

            match = re.match(regex, message, flags=0 if command["case_sensitive"] else re.IGNORECASE)

            if match is not None:
                command["function"](self, nickname, channel, match.group("args").strip().split(" "), message, tags)
                command["last_called"][channel] = current_time
                print("Ran command {}, triggered by {} in channel {}".format(command["trigger"], nickname, channel))

    def onSubscription(self, channel, message, tags):
        for subscription_hook in self.subscription_hooks:
            if subscription_hook["channels"] is not None and channel not in subscription_hook["channels"]:
                continue

            subscription_hook["function"](self, channel, message, tags)

    def onJoin(self, nickname, channel):
        for join_hook in self.join_hooks:
            if join_hook["nicknames"] is not None and nickname not in join_hook["nicknames"]:
                continue
            if join_hook["channels"] is not None and channel not in join_hook["channels"]:
                continue

            join_hook["function"](self, nickname, channel)

    def sendMessage(self, channel, message):
        if self.socket is not None:
            if channel not in self.channels:
                print("Channel not joined")
            else:
                current_time = datetime.now()

                self.channels[channel]["timestamps"][:] = [x for x in self.channels[channel]["timestamps"] if (current_time - x).total_seconds() <= 30]

                if len(self.channels[channel]["timestamps"]) < self.channels[channel]["limit"]:
                    self.socket.sendall("PRIVMSG {} :{}\r\n".format(channel, message))
                    self.channels[channel]["timestamps"].append(current_time)

    def addCommand(self, function, trigger, nicknames=None, channels=None, case_sensitive=False, starts_with=True, cooldown=None):
        self.commands.append({"function": function, "trigger": trigger, "nicknames": nicknames, "channels": channels, "case_sensitive": case_sensitive, "starts_with": starts_with, "cooldown": cooldown, "last_called": {}})

    def addSubscriptionHook(self, function, channels=None):
        self.subscription_hooks.append({"function": function, "channels": channels})

    def addJoinHook(self, function, nicknames=None, channels=None):
        self.join_hooks.append({"function": function, "nicknames": nicknames, "channels": channels})

    def run(self):
        while self.socket is not None:
            data = self.socket.recv(4096)
            lines = data.splitlines()

            for line in lines:
                string = line.strip()

                if string.startswith("PING"):
                    server = re.match("PING (?P<server>.*)", string).group("server")
                    self.sendPong(server)
                else:
                    match = re.match("(@(?P<tags>\S+)\s)?:((?P<nickname>[a-zA-Z0-9_]+)!(?P=nickname)@(?P=nickname)\.)?tmi\.twitch\.tv (?P<action>[A-Z]+?) (?P<channel>#[a-zA-Z0-9_]+)(\s:(?P<message>.*)?)?", string)

                    if match is not None:
                        tags = None
                        if match.group("tags") is not None:
                            tags = {val[0]: val[1] for val in [tag.split("=") for tag in match.group("tags").split(";")]}

                        if match.group("action") == "PRIVMSG":
                            self.onMessage(match.group("nickname"), match.group("channel"), match.group("message"), tags)
                        elif match.group("action") == "USERNOTICE":
                            self.onSubscription(match.group("channel"), match.group("message"), tags)
                        elif match.group("action") == "JOIN":
                            self.onJoin(match.group("nickname"), match.group("channel"))


    def __del__(self):
        if self.socket is not None:
            print("Closing connection")
            self.socket.close()


############## USER COMMANDS ###################
# The signature of the functions must always be:
#   bot: A reference to the bot, basically used for writing to a channel (e.g. bot.sendMessage(channel, message)
#   nickname: The nickname of the user that triggered the command
#   channel: The channel in which the user triggered the command
#   args: An array of all the words (seperated by a whitespace) that followed the trigger command
#   message: Contains the original message
#   tags: Additional tags by twitch. See Twitch IRC API for more information
def exampleCommand1(bot, nickname, channel, args, message, tags):
    bot.sendMessage(channel, "BeneSim is awesome Kappa!")

def exampleCommand2(bot, nickname, channel, args, message, tags):
    bot.sendMessage(channel, "Save the Children is even more awesome!")

############## SUBSCRIPTION HOOKS ###################
# The signature of the functions must always be:
#   bot: A reference to the bot, basically used for writing to a channel (e.g. bot.sendMessage(channel, message)
#   channel: The channel in which the subscription took place
#   message: Contains the subscribers message
#   tags: Additional tags by twitch. See Twitch IRC API for more information
def exampleSubscriptionHook(bot, channel, message, tags):
    if tags["msg-id"] == "resub":
        if tags["display-name"]:
            if not message:
                bot.sendMessage(channel, "Welcome back {} for {} months in a row!".format(tags["display-name"], tags["msg-param-months"]))
            else:
                bot.sendMessage(channel, "Welcome back {} for {} months in a row with the message: \"{}\"!".format(tags["display-name"], tags["msg-param-months"], message))
        else:
            if not message:
                bot.sendMessage(channel, "Welcome back {} for {} months in a row!".format(tags["login"], tags["msg-param-months"]))
            else:
                bot.sendMessage(channel, "Welcome back {} for {} months in a row with the message: \"{}\"!".format(tags["login"], tags["msg-param-months"], message))
    else:
        if tags["display-name"]:
            if not message:
                bot.sendMessage(channel, "Welcome {}!".format(tags["display-name"]))
            else:
                bot.sendMessage(channel, "Welcome {} with the message: \"{}\"!".format(tags["display-name"], message))
        else:
            if not message:
                bot.sendMessage(channel, "Welcome {}!".format(tags["login"]))
            else:
                bot.sendMessage(channel, "Welcome {} with the message: \"{}\"!".format(tags["login"], message))

############## JOIN HOOKS ###################
# The signature of the functions must always be:
#   bot: A reference to the bot, basically used for writing to a channel (e.g. bot.sendMessage(channel, message)
#   nickname: The nickname of the user that joined the channel
#   channel: The channel joined by the user
def exampleJoinHook(bot, nickname, channel):
    if nickname == "benesim" or nickname == "beneflight":
        bot.sendMessage(channel, "Welcome {}".format(nickname))

if __name__ == "__main__":
    # Initialize the bot, requires a valid username and password
    # Channels must be an iterable (e.g. list, tuple ...) containing another iterable with two entries.
    # The first entry is supposed to be the channelname and the second the message limiter.
    # The message limiter dictates how many messages can be send within 30s.
    bot = Bot(username="botusername", password="oauth:botoauthtoken", channels=(("#benesim", 20),))

    # Add the commands to the bot

    # Example of a command that triggers in every channel for every nickname and doesn't need to be the start of a sentence but has a cooldown of 10s
    bot.addCommand(exampleCommand1, "benesim", starts_with=False, cooldown=10)
    # Example of a command that only triggers for the nickname "benesim" in the channels "#benesim" and "#beneflight" and
    # it has to be the start of a sentence without a cooldown
    bot.addCommand(exampleCommand2, "children", nicknames=("benesim",), channels=("#foo", "#bar"), case_sensitive=False, starts_with=True)

    # Add the subscription hooks to the bot

    # Example of a subscription hook for all joined channels
    bot.addSubscriptionHook(exampleSubscriptionHook)

    # Add the join hooks to the bot

    # Example of a join hook for the channel "benesim"
    bot.addJoinHook(exampleJoinHook, channels=("#benesim",))

    bot.connect()
    bot.run()
