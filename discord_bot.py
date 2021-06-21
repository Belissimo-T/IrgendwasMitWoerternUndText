import discord
import main
from io import BytesIO
import traceback
import sys
import g2p

client = discord.Client()

wb_usage = discord.Embed(title="Usage of `!wörterbuch`",
                         description="Usage: `!wörterbuch [word] [ipa] [part_of_speech] "
                                     "[meaning] [example] <zoom>`\n\nExample: ```!wörterbuch \"rein·joi·nen\" "
                                     "\"ˈraɪndʒɔɪnən\" \"Verb\" \"einen Internetanruf oder eine Videospielsession "
                                     "betreten\" '\"Ahh! Er ist wieder reingejoined.\"'```",
                         color=discord.Color(0xFFFF00))

wb_usage.add_field(name="word", value="The word. This symbol might be helpful: `·`")
wb_usage.add_field(name="ipa", value="The phonetic transcription of the word. Mark the stressed syllable with a `ˈ`.")
wb_usage.add_field(name="part_of_speech",
                   value="The part of speech of the word. E.g. `Substantiv`, `Verb`, `Adjektiv`.")
wb_usage.add_field(name="meaning", value="The meaning of the word.")
wb_usage.add_field(name="example", value="An example usage of the word. Contain inside double quotes "
                                         "(`'\"example\"'`).")
wb_usage.add_field(name="zoom", value="Optional. Can be any float < `5` (I think). "
                                      "Specifies the magnification factor. Default is `3`.")

wb_usage.set_footer(text="There is also a !g2p (grapheme to phoneme) command that helps getting the ipa strings.")

g2p_usage = discord.Embed(title="Usage of `!g2p`",
                          description="Usage: `!g2p [word] [lang]`\n\n"
                                      "Example: ```!g2p 'join' 'eng-US'```",
                          color=discord.Color(0xFFFF00))

g2p_usage.add_field(name="word", value="The word that you wish to convert to ipa.")
g2p_usage.add_field(name="lang", value="The language of the word. E.g. `deu`, `eng-US`. Almost every three-letter code "
                                       "works. If in doubt, look it up in the [api specification]"
                                       "(http://clarin.phonetik.uni-muenchen.de/BASWebServices/services/help) under "
                                       "`runG2P`. If you are real cheesy you can just type an invalid language-code "
                                       "and all possibilities will be listed in the error.")
g2p_usage.add_field(name="**IMPORTANT NOTICE**",
                    value="This calls the [BAS API]"
                          "(https://clarin.phonetik.uni-muenchen.de/BASWebServices/interface/Grapheme2Phoneme) whose "
                          "Terms Of Usage can be found [here]"
                          "(https://clarin.phonetik.uni-muenchen.de/BASWebServices/help/termsOfUsage#termsofusage). "
                          "It states that the usage of this API is for **academic (non-profit research) use only** and "
                          "the user **must be part of an academic institution**.\nThis means: **Do not spam** and "
                          "**don't give away any private information**.", inline=False)
g2p_usage.set_footer(text="Also have a look at the !wörterbuch command.")


def construct_error_embed(err: str):
    return discord.Embed(title="Error", description=f"Oh snap! Something went wrong:\n```{err}```",
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


@client.event
async def on_ready():
    print(f'{client.user} has connected to Discord!')
    await client.change_presence(activity=discord.Game(name="!wörterbuch"))


@client.event
async def on_message(message: discord.Message):
    try:
        if message.content.startswith("!wörterbuch"):
            # message.channel: discord.TextChannel

            args = parse_args(message.content[12:])
            if 5 > len(args) or len(args) > 6:
                # message.channel: discord.TextChannel
                await message.channel.send(embed=wb_usage)
            else:
                try:
                    stream = BytesIO(main.get_image(*args))
                    # message.channel: discord.TextChannel
                    # message.author: discord.User
                    word = args[0].replace("·", "")
                    await message.channel.send(f"{word} von {message.author.mention}",
                                               file=discord.File(stream, filename=f"{word.replace(' ', '_')}.png"))
                except Exception:
                    err = traceback.format_exc()
                    sys.stderr.write(err)
                    await message.channel.send(embed=construct_error_embed(err))
        elif message.content.startswith("!g2p"):
            args = parse_args(message.content[4:])

            if len(args) != 2:
                await message.channel.send(embed=g2p_usage)
            else:
                await message.channel.send(f'"{args[0]}" ({args[1]}) in ipa is `{g2p.g2p(*args)}`.')

    except Exception:
        err = traceback.format_exc()
        sys.stderr.write(err)
        await message.channel.send(embed=construct_error_embed(err))


with open("secret.token", "r") as f:
    TOKEN = f.read()

client.run(TOKEN)
