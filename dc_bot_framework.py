import asyncio
import dataclasses
import random
from typing import Callable, Union
import discord
import traceback
import sys


def route(alias: str, only_from: int = None):
    def decorator(func: Callable):
        async def wrapper(client: discord.Client, message: discord.Message, *args, **kwargs):
            if message.author.id != only_from and only_from:
                only_from_user = await client.fetch_user(only_from)
                await message.channel.send(embed=construct_unauthorized_embed(message.author, only_from_user),
                                           reference=message)
            await func(client, message, *args, **kwargs)

        commands.append(Command(alias, wrapper))

        return wrapper

    return decorator


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


def run():
    client = discord.Client()

    @client.event
    async def on_ready():
        print(f'{client.user} has connected to Discord!')
        await client.change_presence(activity=discord.Game(name="!wörterbuch"))

    @client.event
    async def on_message(message: discord.Message):
        try:
            record_command: Union[Command, None] = None
            for command in commands:
                if message.content.startswith(command.alias) and \
                        (not record_command or len(command.alias) > len(record_command.alias)):
                    record_command = command
            if record_command is None:
                print(f"No command found for message \"{message.content}\"")
                return
            end = len(record_command.alias) + 1
            print(message.content[end:])

            args = parse_args(message.content[end:])
            print(args)

            async with message.channel.typing():
                await record_command.function(client, message, *args)

        except Exception:
            err = traceback.format_exc()
            sys.stderr.write(err)
            await message.channel.send(embed=construct_error_embed(err))

    client.run(TOKEN)


with open("secret.token", "r") as f:
    TOKEN = f.read()
