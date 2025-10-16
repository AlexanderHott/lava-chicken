# Import the libraries
import logging
import os
import typing as t

import hikari
import lavalink_rs
import lightbulb
from lavalink_rs.model import events
from lavalink_rs.model.search import SearchEngines
from lavalink_rs.model.track import TrackData, TrackLoadType

from lavachicken.lavalink_voice import LavalinkVoice

# Create a GatewayBot instance
bot = hikari.GatewayBot(
    token=os.environ["DISCORD_BOT_TOKEN"],
    intents=hikari.Intents.GUILDS
    | hikari.Intents.GUILD_VOICE_STATES
    | hikari.Intents.GUILD_MEMBERS,
)
client = lightbulb.client_from_app(bot)
bot.subscribe(hikari.StartingEvent, client.start)
bot.subscribe(hikari.StoppedEvent, client.stop)


async def lavalink_factory():
    node = lavalink_rs.NodeBuilder(
        "localhost:2333",
        False,  # is the server SSL?
        "youshallnotpass",  # os.environ["LAVALINK_PASSWORD"],
        10,  # event.my_user.id,
    )
    lavalink_client = await lavalink_rs.LavalinkClient.new(
        Events(),
        [node],
        lavalink_rs.NodeDistributionStrategy.sharded(),
    )
    return lavalink_client


registry = client.di.registry_for(lightbulb.di.Contexts.DEFAULT)
registry.register_factory(
    lavalink_rs.LavalinkClient,
    lavalink_factory,
)


class Events(lavalink_rs.EventHandler):
    async def ready(
        self,
        client: lavalink_rs.LavalinkClient,
        session_id: str,
        event: events.Ready,
    ) -> None:
        del client, session_id, event
        logging.info("HOLY READY")

    async def track_start(
        self,
        client: lavalink_rs.LavalinkClient,
        session_id: str,
        event: events.TrackStart,
    ) -> None:
        del session_id

        logging.info(
            f"Started track {event.track.info.author} - {event.track.info.title} in {event.guild_id.inner}"
        )

        player_ctx = client.get_player_context(event.guild_id.inner)

        assert player_ctx
        assert player_ctx.data

        data = t.cast(t.Tuple[hikari.Snowflake, hikari.api.RESTClient], player_ctx.data)

        print(event.track, event.track.user_data)
        # assert event.track.user_data and isinstance(event.track.user_data, dict)

        # if event.track.info.uri:
        #     await data[1].create_message(
        #         data[0],
        #         f"Started playing [`{event.track.info.author} - {event.track.info.title}`](<{event.track.info.uri}>) | Requested by <@!{event.track.user_data['requester_id']}>",
        #     )
        # else:
        #     await data[1].create_message(
        #         data[0],
        #         f"Started playing `{event.track.info.author} - {event.track.info.title}` | Requested by <@!{event.track.user_data['requester_id']}>",
        #     )


# Register the command with the client
@client.register()
class Ping(
    # Command type - builtins include SlashCommand, UserCommand, and MessageCommand
    lightbulb.SlashCommand,
    # Command declaration parameters
    name="ping",
    description="checks the bot is alive",
):
    # Define the command's invocation method. This method must take the context as the first
    # argument (excluding self) which contains information about the command invocation.
    @lightbulb.invoke
    async def invoke(self, ctx: lightbulb.Context) -> None:
        # Send a message to the channel the command was used in
        await ctx.respond("Pong!")


async def _join(
    ctx: lightbulb.Context,
    bot: hikari.GatewayBot,
    lavalink_client: lavalink_rs.LavalinkClient,
) -> t.Optional[hikari.Snowflake]:
    if not ctx.guild_id or not ctx.member:
        return None

    channel_id = None

    if not channel_id:
        voice_state = bot.cache.get_voice_state(ctx.guild_id, ctx.member.id)

        if not voice_state or not voice_state.channel_id:
            return None

        channel_id = voice_state.channel_id

    voice = bot.voice.connections.get(ctx.guild_id)

    if not voice:
        await LavalinkVoice.connect(
            ctx.guild_id,
            channel_id,
            bot,
            lavalink_client,
            (ctx.channel_id, bot.rest),
        )
    else:
        assert isinstance(voice, LavalinkVoice)

        await LavalinkVoice.connect(
            ctx.guild_id,
            channel_id,
            bot,
            lavalink_client,
            (ctx.channel_id, bot.rest),
            # old_voice=voice,
        )

    return channel_id


@client.register()
class Play(lightbulb.SlashCommand, name="play", description="play a song"):
    query = lightbulb.string("query", "what do you want to play")

    @lightbulb.invoke
    async def invoke(
        self,
        ctx: lightbulb.Context,
        bot: hikari.GatewayBot,
        lavalink_client: lavalink_rs.LavalinkClient,
    ):
        if not ctx.guild_id or not ctx.member:
            return
        channel_id = await _join(ctx, bot, lavalink_client)
        if channel_id is None:
            await ctx.respond(
                "can't find channel to play in. Please join or specify one"
            )
            return

        voice = bot.voice.connections.get(ctx.guild_id)
        assert isinstance(voice, LavalinkVoice)

        player_ctx = voice.player

        query = self.query
        if not query.startswith("https://"):
            query = SearchEngines.youtube(self.query)

        print(f"searching {query=}")

        # tracks = await lavalink_client.load_tracks(ctx.guild_id, query)

        tracks = await lavalink_client.load_tracks(
            ctx.guild_id, "https://files.vicky.rs/burp%20artist.mp3"
        )
        loaded_tracks = tracks.data
        match tracks.load_type:
            case TrackLoadType.Track:
                assert isinstance(loaded_tracks, TrackData)
                await player_ctx.play_now(loaded_tracks)
            case TrackLoadType.Search:
                assert isinstance(loaded_tracks, list)

                loaded_tracks[0].user_data = {"requester_id": int(ctx.member.id)}

                await player_ctx.play_now(loaded_tracks[0])

                if loaded_tracks[0].info.uri:
                    await ctx.respond(
                        f"Added to queue: [`{loaded_tracks[0].info.author} - {loaded_tracks[0].info.title}`](<{loaded_tracks[0].info.uri}>)"
                    )
                else:
                    await ctx.respond(
                        f"Added to queue: `{loaded_tracks[0].info.author} - {loaded_tracks[0].info.title}`"
                    )
            case track_type:
                print(f"unknown track type {track_type=}")
                await ctx.respond(f"unknown track type {track_type=}")


@client.register
class NowPlaying(
    lightbulb.SlashCommand,
    name="nowplaying",
    description="see what is currently playing",
):
    @lightbulb.invoke
    async def invoke(
        self, ctx: lightbulb.Context, lavalink_client: lavalink_rs.LavalinkClient
    ):
        if not ctx.guild_id:
            return

        player_ctx = lavalink_client.get_player_context(ctx.guild_id)
        if player_ctx is None:
            return

        player = await player_ctx.get_player()

        if player.track:
            await ctx.respond(
                f"{player.paused=} {player.state=} {player.track} {player.state.position=}"
            )
        else:
            await ctx.respond("no track playing")


# Run the bot
# Note that this is blocking meaning no code after this line will run
# until the bot is shut off
bot.run(
    # activity=hikari.Activity(
    #     name="La-la-la-lava, ch-ch-ch-chicken",
    #     type=hikari.ActivityType.LISTENING,
    # )
)
