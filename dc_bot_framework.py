import dataclasses
from typing import Callable, Union
import discord
import traceback
import sys


def route(alias: str):
    def decorator(func: Callable):
        commands.append(Command(alias, func))
        return func

    return decorator


def construct_error_embed(err: str):
    return discord.Embed(title="Error", description=f"Oh snap! Something went wrong:\n```{err}```"
                                                    f"Don't be scared to read the error, most are simple mistakes and "
                                                    f"can be easily resolved! 🧐",
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

            with message.channel.typing():
                await record_command.function(message, *args)

        except Exception:
            err = traceback.format_exc()
            sys.stderr.write(err)
            await message.channel.send(embed=construct_error_embed(err))

    client.run(TOKEN)


with open("secret.token", "r") as f:
    TOKEN = f.read()
