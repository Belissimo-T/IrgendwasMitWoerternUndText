import asyncio
import dataclasses
import random
import sys
import traceback
from asyncio import Event
from typing import Callable, Union

import discord

from context_logger.context_logger import Logger, log


def route(alias: str, only_from: int = None, do_log: bool = False):
    def decorator(func: Callable):
        async def wrapper(client: discord.Client, message: discord.Message, *args, **kwargs):
            if message.author.id != only_from and only_from:
                only_from_user = await client.fetch_user(only_from)
                await message.channel.send(embed=construct_unauthorized_embed(message.author, only_from_user),
                                           reference=message)
            if do_log:
                log_object = await Log.create(message)
                with Logger(f"{message_number[0]}", log_function=log_object.log):
                    await func(client, message, *args, **kwargs)
                await log_object.close()
            else:
                with Logger(f"{message_number[0]}"):
                    await func(client, message, *args, **kwargs)

        commands.append(Command(alias, wrapper))

        return wrapper

    return decorator


class Log:
    log_list: list[str]
    log_message: discord.Message
    event: Event

    @classmethod
    async def create(cls, message: discord.Message):
        self = cls()
        self.message = message
        self.log_list = [" "]
        self.loop = True

        self.log_message = await message.channel.send(embed=self.get_log_embed(), reference=message)

        self.event = Event()

        asyncio.create_task(self.mainloop())

        return self

    def get_log_embed(self):
        return contruct_log_embed(self.log_list)

    def log(self, message: str, prefix: str, indentation: int):
        msg = prefix + ": " + (" " * indentation) + message
        print(msg)
        self.log_list.append(msg)
        self.event.set()

    async def mainloop(self):
        while self.loop:
            await self.event.wait()
            await self.log_message.edit(embed=self.get_log_embed())

    async def close(self, delete_after: int = 2 * 60):
        self.loop = False
        self.log("Closing (the end)", "", 0)
        await self.log_message.edit(content=f"Gets auto deleted after {delete_after} s.", delete_after=delete_after,
                                    embed=self.get_log_embed())


def construct_unauthorized_embed(unauthorized_user: discord.User, authorized_user: discord.User):
    return discord.Embed(title="Unauthorized", color=discord.Color(0xFFA000),
                         description=f"You ({unauthorized_user}) are not {authorized_user}.")


def construct_error_embed(err: str):
    # BTW, https://en.wikipedia.org/wiki/Minced_oath
    messages = ["Snap!", "Shoot!", "Shucks!", "Shizer!", "Darn!", "Frick!", "Juck!", "Dang!", "Frack!", "Frak!",
                "Frig!", "Fug!", "F!", "my gosh!"]
    return discord.Embed(title="Error",
                         description=f"{random.choice(['Oh ', 'Aw ', ''])}{random.choice(messages)} Something went "
                                     f"wrong:\n```{err}```"
                                     f"Don't be scared to read the error, most are simple mistakes and "
                                     f"can be easily resolved! 🧐. Sometimes, trying again 🔁 helps! Also make sure to "
                                     f"not run things in parallel.",
                         color=discord.Color(0xFF0000))


def contruct_log_embed(log_: list[str]):
    logstr = "\n".join(log_)
    return discord.Embed(title="Log", description=f"```{logstr}```")


def parse_args(message: str):
    args = []
    start = 0
    for i in range(len(message)):
        try:
            arg = eval(message[start:i + 1])
            args.append(arg)
            start = i + 1
        except Exception:
            ...
    return args


@dataclasses.dataclass
class Command:
    alias: str
    function: Callable


commands: list[Command] = []
message_number = [0]


def run():
    client = discord.Client()

    @client.event
    async def on_ready():
        log(f'{client.user} has connected to Discord!')
        await client.change_presence(activity=discord.Game(name="!wörterbuch"))

    @client.event
    async def on_message(message: discord.Message):
        message_number[0] += 1
        try:
            record_command: Union[Command, None] = None
            for command in commands:
                if message.content.startswith(command.alias) and \
                        (not record_command or len(command.alias) > len(record_command.alias)):
                    record_command = command
            if record_command is None:
                return
            end = len(record_command.alias) + 1

            with log(f"Relevant message recieved: {message.content}"):
                log(f"Decided on {message.content[:end]}, argstr is {message.content[end:]}")

                args = parse_args(message.content[end:])
                log(f"Parsed args: {args!r}")

                async with message.channel.typing():
                    with log("Running command"):
                        await record_command.function(client, message, *args)
                    log("Finished!")
        except Exception:
            err = traceback.format_exc()
            sys.stderr.write(err)
            await message.channel.send(embed=construct_error_embed(err))

    client.run(TOKEN)


with open("secret.token", "r") as f:
    TOKEN = f.read()
