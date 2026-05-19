import os

import discord
import dotenv
from sqlmodel import Field, Session, SQLModel, create_engine, select

dotenv.load_dotenv()

engine = create_engine("sqlite:///data.db")
SQLModel.metadata.create_all(engine)

REACTION_REQUIREMENT = 3


class NominationMessage(SQLModel, table=True):
    id: int = Field(primary_key=True)
    nomination_message_id: int | None = Field(default=None)
    accepted: bool = Field(default=False)
    removed: bool = Field(default=False)


intents = discord.Intents.default()
intents.message_content = True

bot = discord.Bot(intents=intents)


@bot.event
async def on_message(message: discord.Message):
    if message.author == bot.user:
        return
    if message.channel.id != 1506087646819127437:
        return
    # now, we will add a reaction to the message
    await message.add_reaction("books")
    # now we will add the message to the database
    with Session(engine) as session:
        session.add(NominationMessage(id=message.id))
        session.commit()
    # we are done. time to listen for reactions


@bot.event
async def on_reaction_add(reaction: discord.Reaction, user: discord.User):
    if reaction.emoji != "books":
        return
    if reaction.message.channel.id != 1506087646819127437:
        return

    # now, we will check if the reaction count meets the requirement
    reactionses = reaction.message.reactions
    reactions = None
    for r in reactionses:
        if r.emoji == reaction.emoji:
            reactions = await r.users().flatten()
            break
    if reactions is None:
        return
    print("printing reaction users")
    for r in reactions:
        if isinstance(r, discord.Member):
            print(r.nick or r.name)
        else:
            print(r.name)
    reactions_filtered = [
        r for r in reactions if r != bot.user and r != reaction.message.author
    ]
    print("printing filtered reactions")
    for r in reactions_filtered:
        if isinstance(r, discord.Member):
            print(r.nick or r.name)
        else:
            print(r.name)

    if len(reactions_filtered) >= REACTION_REQUIREMENT:
        print("reaction count meets requirement")
        with Session(engine) as session:
            message = session.exec(
                select(NominationMessage).where(
                    NominationMessage.id == reaction.message.id
                )
            ).first()
            if message:
                nomination_message = discord.Embed(
                    title=f"Nominated with {len(reactions_filtered)} votes",
                    description=reaction.message.content,
                    color=discord.Color.purple(),
                    author=discord.EmbedAuthor(
                        name=reaction.message.author.name,
                        icon_url=reaction.message.author.avatar.url
                        if reaction.message.author.avatar is not None
                        else None,
                    ),
                )

                # send our nomination message
                guild = reaction.message.guild
                if guild is None:
                    print("guild is None")
                    return
                channel = guild.get_channel(1506091012920180817)
                if channel is None or isinstance(channel, discord.TextChannel) is False:
                    print("channel is None")
                    return

                if message.accepted:
                    print("message already accepted")
                    # get the message
                    if message.nomination_message_id is not None:
                        nomination_message = await channel.fetch_message(
                            message.nomination_message_id
                        )
                        if nomination_message is None:
                            print("nomination_message is None")
                            return
                        # else edit the message to reflect the new vote number
                        await nomination_message.edit(
                            embed=nomination_message.embeds[0]
                        )
                    return
                if message.removed:
                    print("message removed")
                    return

                sent_message = await channel.send(embed=nomination_message)

                message.accepted = True
                message.nomination_message_id = sent_message.id

                session.add(message)
                session.commit()
        await reaction.message.add_reaction("pushpin")


# @bot.slash_command()
# async def hello(ctx, name: str | None = None):
#     name = name or ctx.author.name
#     await ctx.respond(f"Hello {name}!")


bot.run(os.getenv("BOT_TOKEN"))
