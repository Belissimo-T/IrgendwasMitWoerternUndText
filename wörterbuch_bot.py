import asyncio
import io
import os
import discord
from typing import Literal

import postermywall as pmw
import wörterbuch
import g2p
from dc_bot_framework import route, run
from zitat import get_zitat, get_image

if not os.path.exists("dictionaries/global.dict"):
    dictionary = wörterbuch.Dictionary("global")
else:
    dictionary = wörterbuch.Dictionary.from_file("global")

ESCAPED_CHARS = "`~_()[]*<>"


def get_wb_help(name: str):
    help_embed = discord.Embed(title=f"Usage of `!wörterbuch {name}`",
                               description="Usage: `!wörterbuch add <word> <ipa> <part_of_speech> "
                                           f"<meaning> <example> `\n\nExample: ```!wörterbuch {name} \"rein·joi·nen\" "
                                           "\"ˈraɪndʒɔɪnən\" \"Verb\" \"einen Internetanruf oder eine "
                                           "Videospielsession betreten\" \"Ahh! Er ist wieder reingejoined.\"```",
                               color=discord.Color(0xFFFF00))

    help_embed.add_field(name="word", value="The word. This symbol might be helpful: `·`")
    help_embed.add_field(name="ipa",
                         value="The phonetic transcription of the word. Mark the stressed syllable with one of these: "
                               "`ˈ'´`.")
    help_embed.add_field(name="part_of_speech",
                         value="The part of speech of the word. E.g. `Substantiv`, `Verb`, `Adjektiv`.")
    help_embed.add_field(name="meaning", value="The meaning of the word.")
    help_embed.add_field(name="example", value="An example usage of the word.")
    # wb_usage.add_field(name="zoom", value="Optional. Can be any float < `5` (I think). "
    #                                       "Specifies the magnification factor. Default is `3`.")
    return help_embed


def escape(string: str) -> str:
    return "".join(["\\" * (char in ESCAPED_CHARS) + char for char in string])


@route("!wörterbuch mastertest", only_from=311516082320048128)
async def testest(client: discord.Client, message: discord.Message, echo: str = ""):
    if echo:
        await message.channel.send(echo)


@route("!postermywall render", do_log=True)
async def postermywall_render(client: discord.Client, message: discord.Message, id_: str, changes):
    template = await pmw.Template.from_id(id_)

    out = discord.Embed(title=f"Custom Template based on `{id_}`", description=f"command: `!postermywall render "
                                                                               f"{id_!r} {changes!r}`")
    out.set_image(url="attachment://image.png")
    file = await template.get_dc_modify_file(changes)
    await message.channel.send(embed=out, file=file)


@route("!postermywall attrs", do_log=True)
async def postermywall_attrs(client: discord.Client, message: discord.Message, template_id: str):
    template = await pmw.Template.from_id(template_id)
    await message.channel.send(embed=await template.get_dc_attrs_embed())


@route("!postermywall search", do_log=True)
async def postermywall_search(client: discord.Client, message: discord.Message, search_str: str,
                              type_: Literal["all", "image", "video"] = "all", size: str = "all"):
    await asyncio.gather(*[message.channel.send("temporary message, gets auto-deleted after 2 min.",
                                                embed=template.get_dc_embed(), delete_after=2 * 60,
                                                file=await template.get_dc_file()) for template in
                           await pmw.search(search_str, type_, size)])


@route("!zitat help")
async def zitat_help(client: discord.Client, message: discord.Message):
    help_embed = discord.Embed(title="Usage of `!zitat`",
                               description="Usage: `!zitat <text> <author>`\n\nExample: "
                                           "```!zitat \"Trapdoors und Repeater sind eigentlich das gleiche.\" "
                                           "\"Zwakel\"```",
                               color=discord.Color(0xFFFF00))

    help_embed.add_field(name="text", value="The text of the Zitat.")
    help_embed.add_field(name="author", value="The author of the Zitat.")

    await message.channel.send(embed=help_embed)


@route("!zitat")
async def zitat(client: discord.Client, message: discord.Message, text: str, author: str):
    background = get_image()
    for _ in range(5):
        img = io.BytesIO(get_zitat(text, author, background))

        file = discord.File(img, filename="zitat.png")
        await message.channel.send("pure inspiration.", file=file)

    await message.delete()


@route("!getmsg")
async def getmsg(client: discord.Client, message: discord.Message, id_: str):
    # message.channel: discord.TextChannel
    msg: discord.Message = await message.channel.fetch_message(int(id_))

    out = discord.Embed(title=f"Message: `{id_}`", description=f"`{escape(msg.content)}`",
                        color=discord.Color(0x00FF00))

    for i, embed in enumerate(msg.embeds):
        val = f"`{escape(str(embed.to_dict()))}`"
        out.add_field(name=f"Embed #{i + 1}", value=val)
    await message.channel.send(embed=out)


# @route("!wörterbuch fullhelp")
# async def fullhelp(message: discord.Message):
#     await message.channel.send("!wörterbuch render help")
#     await message.channel.send("!wörterbuch add help")
#     await message.channel.send("!wörterbuch search help")
#     await message.channel.send("!wörterbuch list help")
#     await message.channel.send("!wörterbuch remove help")
#     await message.channel.send("!wörterbuch help")
#     await message.channel.send("!wörterbuch fullhelp help")
#     await message.channel.send("!g2p help")


@route("!wörterbuch help")
@route("!wörterbuch")
async def wb(client: discord.Client, message: discord.Message):
    help_embed = discord.Embed(title="Commands of the Wörterbuch-Bot", color=discord.Color(0xFFFF00),
                               description="Tip: Add a `help` to any command to show its help.")
    help_embed.add_field(name="`!wörterbuch render`", value="Renders one Wörterbuch-entry.", inline=False)
    help_embed.add_field(name="`!wörterbuch add`", value="Adds a word to the dictionary.", inline=False)
    help_embed.add_field(name="`!wörterbuch search`", value="Searches for a word in the dictionary.",
                         inline=False)
    help_embed.add_field(name="`!wörterbuch list`", value="Shows all words in the dictionary.", inline=False)
    help_embed.add_field(name="`!wörterbuch remove`", value="Removes a word from the dictionary.", inline=False)
    help_embed.add_field(name="`!wörterbuch`", value="Shows this help.",
                         inline=False)
    help_embed.add_field(name="`!wörterbuch fullhelp`", value="Calls the help of every function.", inline=False)

    help_embed.add_field(name="`!g2p`", value="Grapheme to Phoneme: Helps getting the ipa string.", inline=False)

    help_embed.add_field(name="`!zitat`", value="Generates a Zitat.", inline=False)

    await message.channel.send(embed=help_embed)


@route("!wörterbuch render help")
async def wb_render_help(client: discord.Client, message: discord.Message):
    await message.channel.send(embed=get_wb_help("render"))


@route("!wörterbuch render", do_log=True)
async def wb_render(client: discord.Client, message: discord.Message, word_, ipa, part_of_speech, meaning, example):
    word = wörterbuch.Word(wörterbuch.split_word(word_, "·*"), ipa, part_of_speech,
                           meaning, example)

    embed, file = await word.get_dc_embed()
    await message.channel.send(file=file, embed=embed)


@route("!wörterbuch add help")
async def wb_add_help(client: discord.Client, message: discord.Message):
    await message.channel.send(embed=get_wb_help("add"))


@route("!wörterbuch add")
async def wb_add(client: discord.Client, message: discord.Message, word_, ipa, part_of_speech, meaning, example):
    word = wörterbuch.Word(wörterbuch.split_word(word_, "·*"), ipa, part_of_speech,
                           meaning, example)

    dictionary.add_word(word)

    embed, file = await word.get_dc_embed("Added word to dictionary ✅")
    await message.channel.send(file=file, embed=embed)


@route("!wörterbuch remove help")
async def wb_search_help(client: discord.Client, message: discord.Message):
    help_embed = discord.Embed(title="Usage of `!wörterbuch search`",
                               description="Usage: `!wörterbuch remove <word>`\n\nExample: "
                                           "```!wörterbuch remove \"reinjoinen\"```",
                               color=discord.Color(0xFFFF00))

    help_embed.add_field(name="word", value="The word to be deleted.")

    # wb_usage.add_field(name="zoom", value="Optional. Can be any float < `5` (I think). "
    #                                       "Specifies the magnification factor. Default is `3`.")

    await message.channel.send(embed=help_embed)


@route("!wörterbuch remove")
async def wb_remove(client: discord.Client, message: discord.Message, word: str):
    try:
        dictionary.remove_word(word)

        out = discord.Embed(color=discord.Color(0x00FF00), description=f"Word `{word}` successfully removed. ✅")
    except KeyError:
        out = discord.Embed(color=discord.Color(0xFF0000), description=f"Can't find a word `{word}`. 😢")

    await message.channel.send(embed=out)


@route("!wörterbuch list help")
async def wb_list_help(client: discord.Client, message: discord.Message):
    help_embed = discord.Embed(title="Usage of `!wörterbuch list`",
                               description="Usage: `!wörterbuch list`\n\nExample: "
                                           "```!wörterbuch list```",
                               color=discord.Color(0xFFFF00))
    await message.channel.send(embed=help_embed)


@route("!wörterbuch list")
async def wb_list(client: discord.Client, message: discord.Message):
    await message.channel.send("temporary message, gets auto-deleted after 2 min",
                               embed=discord.Embed(title="Wörterbuch Listing",
                                                   description=f"total word count: `{len(dictionary)}`"),
                               delete_after=2 * 60)

    for word in dictionary:
        word: wörterbuch.Word
        embed = discord.Embed(title=word.get_display_name())
        embed.set_image(url="attachment://image.png")
        await message.channel.send("temporary message, gets auto-deleted after 2 min", embed=embed,
                                   file=await word.get_dc_file(),
                                   delete_after=2 * 60)


@route("!wörterbuch search help")
async def wb_search_help(client: discord.Client, message: discord.Message):
    help_embed = discord.Embed(title="Usage of `!wörterbuch search`",
                               description="Usage: `!wörterbuch search <query>`\n\nExample: "
                                           "```!wörterbuch search \"reinjoinen\"```",
                               color=discord.Color(0xFFFF00))

    help_embed.add_field(name="query", value="The search query.")

    # wb_usage.add_field(name="zoom", value="Optional. Can be any float < `5` (I think). "
    #                                       "Specifies the magnification factor. Default is `3`.")

    await message.channel.send(embed=help_embed)


@route("!wörterbuch search")
async def wb_search(client: discord.Client, message: discord.Message, query: str):
    results = dictionary.search_word(query)

    for i, word in enumerate(results):
        embed, file = await word.get_dc_embed(f"Search result #{i + 1}")
        await message.channel.send(file=file, embed=embed)

    if len(results) == 0:
        embed = discord.Embed(color=discord.Color(0xFF0000),
                              description=f"No search results found for query `{query}`. 😢")
        await message.channel.send(embed=embed)


@route("!g2p help")
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
                               "the user **must be part of an academic institution**.\nThis means: **Do not spam** "
                               "and **don't give away any private information**.", inline=False)
    help_embed.set_footer(text="Also have a look at the !wörterbuch command.")

    await message.channel.send(embed=help_embed)


@route("!g2p")
async def g2p_(client: discord.Client, message: discord.Message, _word, lang):
    phonemes = g2p.g2p(_word, lang)

    _, predicted_text_syllables = g2p.get_syllables(phonemes, _word)
    # print(predicted_text_syllables, predicted_phoneme_syllables)
    word = wörterbuch.Word(predicted_text_syllables, "".join(phonemes).replace("+", "").replace("_", ""), "", "", "", True)

    description = f"word: `{word.get_display_name()}`" \
                  f"\nipa: `{word.ipa}`\n"
    out = discord.Embed(title=f"Phonetic \"analysis\" of `{_word}`", description=description,
                        color=discord.Color(0x00FF00))
    out.add_field(name="Predicted ~~Accurate~~ Syllabic Structure", inline=False,
                  value=word.get_formatted_syllabic_structure())

    await message.channel.send(embed=out)


run()
