import os
import re
import sys

import discord
import dotenv
from sqlalchemy.orm.base import manager_of_class
from sqlmodel import Field, Session, SQLModel, create_engine, select

sys.stdout.reconfigure(line_buffering=True)

dotenv.load_dotenv()


REACTION_REQUIREMENT = 2


class NominationMessage(SQLModel, table=True):
    id: int = Field(primary_key=True)
    nomination_message_id: int | None = Field(default=None)
    accepted: bool = Field(default=False)
    removed: bool = Field(default=False)


engine = create_engine("sqlite:///data/data.db", echo=True)
SQLModel.metadata.create_all(engine)


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
    await message.add_reaction("📚")
    # now we will add the message to the database
    with Session(engine) as session:
        session.add(NominationMessage(id=message.id))
        session.commit()
    # we are done. time to listen for reactions


@bot.event
async def on_raw_reaction_add(reaction_: discord.RawReactionActionEvent):
    class Reaction:
        channel: discord.TextChannel
        message: discord.Message
        user: discord.User

        def __init__(self):
            pass

        async def _init(self) -> None:
            self.emoji = reaction_.emoji
            self.user = await bot.get_or_fetch(discord.User, reaction_.user_id)
            self.channel = await bot.get_or_fetch(
                discord.TextChannel, reaction_.channel_id
            )
            self.message = await self.channel.fetch_message(reaction_.message_id)

    reaction = Reaction()
    await reaction._init()

    user = reaction.user

    print(f"saw reaction {reaction.emoji} from {user.name}")
    if reaction.emoji != "📚" and reaction.emoji.name != "📚":
        print(f"reaction emoji is {reaction.emoji}, not 📚")
        return
    if reaction.message.channel.id != 1506087646819127437:
        print(f"channel id is {reaction.message.channel.id}, not 1506087646819127437")
        return

    # now, we will check if the reaction count meets the requirement
    reactionses = reaction.message.reactions
    reactions = None
    for r in reactionses:
        if r.emoji == reaction.emoji.name:
            reactions = await r.users().flatten()
            break
    reaction.message = await reaction.message.channel.fetch_message(reaction.message.id)
    print("about to check if reactions is none")
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

                channel: discord.TextChannel

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
        await reaction.message.add_reaction("📌")


# @bot.slash_command()
# async def hello(ctx, name: str | None = None):
#     name = name or ctx.author.name
#     await ctx.respond(f"Hello {name}!")


@bot.slash_command(default_member_permissions=discord.Permissions(manage_messages=True))
async def delete_message(ctx: discord.ApplicationContext, message_id_: str):
    message_id = int(message_id_)
    with Session(bind=engine) as session:
        message = session.exec(
            select(NominationMessage).where(NominationMessage.id == message_id)
        ).first()
        if message is not None:
            # find original message
            user_message = await (
                await bot.fetch_channel(1506087646819127437)
            ).fetch_message(message.id)
            # remove the pin reaction
            await user_message.remove_reaction("📌", user_message.guild.me)
            # now lets get the nomination message
            if message.nomination_message_id is not None:
                nomination_message = await (
                    await bot.fetch_channel(1506091012920180817)
                ).fetch_message(message.nomination_message_id)
                await nomination_message.delete()
            message.removed = True
            session.commit()
            await ctx.respond(f"Deleted message {message_id}")
        else:
            await ctx.respond(f"Message {message_id} not found")


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name}")
    # lets fetch old messages to pull them into cache
    channel = bot.get_channel(1506087646819127437)
    if channel is None:
        print("failed to get channel")
        return
    i = 0
    async for message in channel.history(limit=100):
        i += 1
    print(f"fetched {i} messages")


bot.run(os.getenv("BOT_TOKEN"))
