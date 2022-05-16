import asyncio
import io
import os
from typing import Literal

import discord

import g2p
import postermywall
import postermywall as pmw
import wörterbuch
from belissibot_framework import App, construct_help_embed
from zitat import get_image, get_zitat

if not os.path.exists("dictionaries/global.dict"):
    dictionary = wörterbuch.Dictionary("global")
else:
    dictionary = wörterbuch.Dictionary.from_file("global")

bot_app = App()


def get_wb_help(name: str, description: str):
    return construct_help_embed(
        f"!wörterbuch {name}",
        description,
        f"!wörterbuch {name} \"rein·joi·nen\" \"ˈraɪndʒɔɪnən\" \"Verb\" \"einen Internetanruf oder eine "
        f"Videospielsession betreten\" \"Ahh! Er ist wieder reingejoined.\"",
        word=("The word. This symbol might be helpful: `·`", "str"),
        ipa=("The phonetic transcription of the word. Mark the stressed syllable with one of these: `ˈ'´`.", "str"),
        part_of_speech=("The part of speech of the word. E.g. `Substantiv`, `Verb`, `Adjektiv`.", "str"),
        meaning=("The meaning of the word.", "str"),
        example=("An example usage of the word. For example an example sentence.", "str")
    )


@bot_app.add_help("!belissibot fullhelp", "Test all help functions of this bot. Can only be used by `Belissimo#1438`.",
                  "!belissibot fullhelp")
@bot_app.route("!belissibot fullhelp", only_from_users=[311516082320048128])
async def testest(client: discord.Client, message: discord.Message):
    helps = ["!belissibot",
             "!wörterbuch",
             "!postermywall",
             "!zitat help",
             "!poll",
             "!wörterbuch render help",
             "!wörterbuch add help",
             "!wörterbuch search help",
             "!wörterbuch list help",
             "!wörterbuch remove help",
             "!g2p help",
             "!postermywall render help",
             "!postermywall attrs help",
             "!postermywall search help",
             "!poll new help",
             "!poll choice help",
             "!poll remove help",
             "!poll publish help",
             "!belissibot fullhelp help"]

    await asyncio.gather(*[message.channel.send(help_) for help_ in helps])


@bot_app.add_help("!postermywall render",
                  "Renders a template with the given changes",
                  '!postermywall render "5a72a3a166d55ebea89d03ebceb1de05" [([2, 1], "This is modified!"), ([7, 1], "50'
                  '0")]',
                  template_id="The template id obtained by `!postermywall search`.",
                  changes="Of the type ```py\nlist[tuple[list[int], str]]```\nA list of changes to be performed on the template. "
                          "I am to lazy to explain the syntax of this; figure it out on your own using the example of "
                          "this and the example of `!postermywall attrs`.")
@bot_app.route("!postermywall render", do_log=True, delete_message=False)
async def postermywall_render(client: discord.Client, message: discord.Message, template_id: str, changes):
    template = await pmw.Template.from_id(template_id)

    out = discord.Embed(title=f"Custom Template based on `{template_id}`",
                        description=f"command: `!postermywall render "
                                    f"{template_id!r} {changes!r}`")
    out.set_image(url="attachment://image.png")
    file = await template.get_dc_modify_file(changes)
    await message.channel.send(embed=out, file=file)


@bot_app.add_help("!postermywall attrs",
                  "Shows all modifyable elemements with their respective path given a template id.",
                  "!postermywall attrs \"5a72a3a166d55ebea89d03ebceb1de05\"",
                  template_id="The templayte id obtained by `!postermywall search`.")
@bot_app.route("!postermywall attrs", do_log=True, delete_message=False)
async def postermywall_attrs(client: discord.Client, message: discord.Message, template_id: str):
    template = await pmw.Template.from_id(template_id)
    await message.channel.send(embed=await template.get_dc_attrs_embed(), file=await template.get_dc_file(message))


async def send_template(message: discord.Message, template: pmw.Template):
    await message.channel.send("temporary message, gets auto-deleted after 2 min.",
                               embed=template.get_dc_embed(), delete_after=2 * 60,
                               file=await template.get_dc_file(message=message))


size_help_str = ', '.join([f'`{size}`' for size in postermywall.size_options])


@bot_app.add_help("!postermywall search",
                  "Shows matching templates based on the specified search query.",
                  "!postermywall search \"Halloween\"",
                  argstr="<search_query: str> [type: str [size: str]]",
                  search_query="The search query.",
                  type="The type of the template. Can be one of `all`, `image`, `video`. Optional.",
                  size=f"The size of the template. Can be one of {size_help_str}. Optional.")
@bot_app.route("!postermywall search", delete_message=False)
async def postermywall_search(client: discord.Client, message: discord.Message, search_query: str,
                              type_: Literal["all", "image", "video"] = "all", size: str = "all"):
    await asyncio.gather(*[send_template(message, template) for template in
                           await pmw.search(search_query, type_, size)])


@bot_app.add_help("!zitat",
                  "Generates a Zitat.",
                  "!zitat \"Trapdoors und Repeater sind eigentlich das gleiche.\" \"Zwakel\"",
                  text="The text of the Zitat.",
                  author="The author of the zitat to be displayed at the bottom of it.")
@bot_app.route("!zitat")
async def zitat(client: discord.Client, message: discord.Message, text: str, author: str):
    background = get_image()
    for _ in range(5):
        img = io.BytesIO(get_zitat(text, author, background))

        file = discord.File(img, filename="zitat.png")
        await message.channel.send("pure inspiration.", file=file)

    await message.delete()


ESCAPED_CHARS = "`\\"


def escape(obj) -> str:
    try:
        if not isinstance(obj, str):
            obj = repr(obj)

        return "".join(["\\" + char if char in ESCAPED_CHARS else char for char in obj])
    except Exception as e:
        return f"Error: {e!r}"


@bot_app.route("!getmsg")
async def getmsg(client: discord.Client, message: discord.Message, id_: str):
    # message.channel: discord.TextChannel
    msg: discord.Message = await message.channel.fetch_message(int(id_))

    for key in msg.__slots__:
        # msg.__getattribute__(key)
        try:
            escaped_msg = escape(repr(msg.__getattribute__(key)))
        except Exception as e:
            escaped_msg = f"Error: {e!r}"

        snippets = [escaped_msg[i:min(len(escaped_msg), i + 1000)] for i in range(0, len(escaped_msg), 1000)]

        for i, snippet in enumerate(snippets):
            out = discord.Embed(title=f"Message: `{id_}`, Attributes",
                                description=f"{key}: `{snippet}`",
                                color=discord.Color(0x00FF00))
            out.set_footer(text=f"SNIPPET #{key}:{i}")

            await message.channel.send(embed=out)

    for i, embed in enumerate(msg.embeds):
        # val = escape(str(embed.to_dict()))
        #
        # snippets = [val[i:min(len(val), i + 1022)] for i in range(0, len(val), 1022)]
        # for j, snippet in enumerate(snippets):
        #     out = discord.Embed(title=f"Message: `{id_}`", description=f"Embeds:",
        #                         color=discord.Color(0x00FF00))
        #     out.add_field(name=f"Embed #{i + 1}", value=f"`{snippet}`")
        #     out.set_footer(text=f"SNIPPET #E{i}:{j}")
        #     await message.channel.send(embed=out)

        for key, value in embed.to_dict().items():
            escaped_msg = escape(repr(value))

            snippets = [escaped_msg[i:min(len(escaped_msg), i + 1000)] for i in range(0, len(escaped_msg), 1000)]

            for j, snippet in enumerate(snippets):
                out = discord.Embed(title=f"Message: `{id_}`, Embeds",
                                    color=discord.Color(0x00FF00))
                out.add_field(name=f"Embed #{i + 1}", value=f"{key}: `{snippet}`")
                out.set_footer(text=f"SNIPPET #E{i}:{j}")

                await message.channel.send(embed=out)


@bot_app.add_help("!belissibot",
                  "Lists all command categories and their respective help commands.",
                  "!belissibot")
@bot_app.route("!belissibot")
async def belissibot_help(client: discord.Client, message: discord.Message):
    help_embed = discord.Embed(title="Commands of the Belissibot", color=discord.Color(0xFFFF00),
                               description="Tip: Add a `help` to any command to see what it does.")
    help_embed.add_field(name="`!wörterbuch`", value="Shows all commands related to the Wörterbuch-functionality.",
                         inline=False)
    help_embed.add_field(name="`!postermywall`", value="Shows all commands related to the PosterMyWall-functionality.",
                         inline=False)
    help_embed.add_field(name="`!zitat`", value="Generates a Zitat.", inline=False)

    await message.channel.send(embed=help_embed)


@bot_app.add_help("!wörterbuch",
                  "Lists all commands of the Wörterbuch-category.",
                  "!wörterbuch")
@bot_app.route("!wörterbuch", raw_args=True)
async def wb(client: discord.Client, message: discord.Message, _=""):
    help_embed = discord.Embed(title="Wörterbuch-Commands of the Belissibot", color=discord.Color(0xFFFF00),
                               description="Tip: Add a `help` to any command to see what it does.")
    help_embed.add_field(name="`!wörterbuch render`", value="Renders one Wörterbuch-entry.", inline=False)
    help_embed.add_field(name="`!wörterbuch add`", value="Adds a word to the dictionary.", inline=False)
    help_embed.add_field(name="`!wörterbuch search`", value="Searches for a word in the dictionary.",
                         inline=False)
    help_embed.add_field(name="`!wörterbuch list`", value="Shows all words in the dictionary.", inline=False)
    help_embed.add_field(name="`!wörterbuch remove`", value="Removes a word from the dictionary.", inline=False)

    help_embed.add_field(name="`!g2p`", value="Grapheme to Phoneme: Helps getting the ipa string.", inline=False)

    await message.channel.send(embed=help_embed)


@bot_app.route("!wörterbuch render help")
async def wb_render_help(client: discord.Client, message: discord.Message):
    await message.channel.send(embed=get_wb_help("render", "Renders a dictionary entry."))


@bot_app.route("!wörterbuch render", do_log=True)
async def wb_render(client: discord.Client, message: discord.Message, word_, ipa, part_of_speech, meaning, example):
    word = wörterbuch.Word(wörterbuch.split_word(word_), ipa, part_of_speech,
                           meaning, example)

    embed, file = await word.get_dc_embed()
    await message.channel.send(file=file, embed=embed)


@bot_app.route("!wörterbuch add help")
async def wb_add_help(client: discord.Client, message: discord.Message):
    await message.channel.send(embed=get_wb_help("add", "Adds the described word to the dictionary."))


@bot_app.route("!wörterbuch add")
async def wb_add(client: discord.Client, message: discord.Message, word_, ipa, part_of_speech, meaning, example):
    word = wörterbuch.Word(wörterbuch.split_word(word_), ipa, part_of_speech,
                           meaning, example)

    dictionary.add_word(word)

    embed, file = await word.get_dc_embed("Added word to dictionary ✅")
    await message.channel.send(file=file, embed=embed)


@bot_app.add_help("!wörterbuch remove",
                  "Removes a word from the dictionary.",
                  "!wörterbuch remove \"reinjoinen\"",
                  word="The word to be deleted. Requires an exact match and is case-sensitive.")
@bot_app.route("!wörterbuch remove")
async def wb_remove(client: discord.Client, message: discord.Message, word: str):
    try:
        dictionary.remove_word(word)

        out = discord.Embed(color=discord.Color(0x00FF00), description=f"Word `{word}` successfully removed. ✅")
    except KeyError:
        out = discord.Embed(color=discord.Color(0xFF0000), description=f"Can't find a word `{word}`. 😢")

    await message.channel.send(embed=out)


@bot_app.add_help("!wörterbuch list",
                  "Lists all the word in the dictionary",
                  "!wörterbuch list")
@bot_app.route("!wörterbuch list")
async def wb_list(client: discord.Client, message: discord.Message):
    await message.channel.send("temporary message, gets auto-deleted after 2 min",
                               embed=discord.Embed(title="Wörterbuch Listing",
                                                   description=f"total word count: `{len(dictionary)}`"),
                               delete_after=2 * 60)

    words = list(dictionary)

    words.sort(key=lambda x: x.get_data_key())

    for word in words:
        word: wörterbuch.Word
        embed = discord.Embed(title=word.get_display_name())
        embed.set_image(url="attachment://image.png")
        await message.channel.send("temporary message, gets auto-deleted after 2 min", embed=embed,
                                   file=await word.get_dc_file(),
                                   delete_after=2 * 60)


@bot_app.add_help("!wörterbuch search",
                  "Searches for a word in the dictionary.",
                  "!wörterbuch search \"reinjoinen\"",
                  search_query="The search query.")
@bot_app.route("!wörterbuch search")
async def wb_search(client: discord.Client, message: discord.Message, search_query: str):
    results = dictionary.search_word(search_query)

    for i, word in enumerate(results):
        embed, file = await word.get_dc_embed(f"Search result #{i + 1}")
        await message.channel.send(file=file, embed=embed)

    if len(results) == 0:
        embed = discord.Embed(color=discord.Color(0xFF0000),
                              description=f"No search results found for query `{search_query}`. 😢")
        await message.channel.send(embed=embed)


@bot_app.route("!g2p help")
async def g2p_help(client: discord.Client, message: discord.Message):
    help_embed = discord.Embed(title="Usage of `!g2p`",
                               description="Usage: `!g2p <word> <lang>`\n\n"
                                           "Example: ```!g2p 'join' 'eng-US'```",
                               color=discord.Color(0xFFFF00))

    help_embed.add_field(name="word", value="The word that you wish to convert to ipa and get ~~accurate~~ "
                                            "predictions about the syllabic structure.")
    help_embed.add_field(name="lang",
                         value="The language of the word. E.g. `deu`, `eng-US`. Almost every three-letter code "
                               "works. If in doubt, look it up in the [api specification]"
                               "(http://clarin.phonetik.uni-muenchen.de/BASWebServices/services/help) under "
                               "`runG2P`. And if you are real cheesy you can just type an invalid language-code "
                               "and all possibilities will be listed in the error.")
    help_embed.add_field(name="**IMPORTANT NOTICE**",
                         value="This calls the [BAS API](https://clarin.phonetik.uni-muenchen.de/BASWebServices/int"
                               "erface/Grapheme2Phoneme) whose Terms Of Usage can be found [here](https://clarin.pho"
                               "netik.uni-muenchen.de/BASWebServices/help/termsOfUsage#termsofusage). It states "
                               "that the usage of this API is for **academic (non-profit research) use only** and "
                               "the user **must be part of an academic institution**.\n**Do not spam** "
                               "and **don't give away any private information**.", inline=False)

    await message.channel.send(embed=help_embed)


@bot_app.route("!g2p")
async def g2p_(client: discord.Client, message: discord.Message, _word, lang):
    phonemes = g2p.g2p(_word, lang)

    _, predicted_text_syllables = g2p.get_syllables(phonemes, _word)
    # print(predicted_text_syllables, predicted_phoneme_syllables)
    word = wörterbuch.Word(predicted_text_syllables, "".join(phonemes).replace("+", "").replace("_", ""), "", "",
                           "", True)

    description = f"word: `{word.get_display_name()}`" \
                  f"\nipa: `{word.ipa}`\n"
    out = discord.Embed(title=f"Phonetic \"analysis\" of `{_word}`", description=description,
                        color=discord.Color(0x00FF00))
    out.add_field(name="Predicted ~~Accurate~~ Syllabic Structure", inline=False,
                  value=word.get_formatted_syllabic_structure())

    await message.channel.send(embed=out)


with open("secret.token", "r") as f:
    TOKEN = f.read()

bot_app.run(discord_token=TOKEN,
            game="!belissibot")
