from __future__ import annotations
import typing as t

# from bot import Bot

import hikari
from hikari.api import VoiceConnection, VoiceComponent
from lavalink_rs import LavalinkClient, PlayerContext
from lavalink_rs.model.http import UpdatePlayer
from lavalink_rs.model.player import ConnectionInfo


class LavalinkVoice(VoiceConnection):
    __slots__ = (
        "lavalink",
        "player",
        "__session_id",
        "__owner",
        "__should_close",
    )
    lavalink: LavalinkClient
    player: PlayerContext

    def __init__(
        self,
        lavalink_client: LavalinkClient,
        player: PlayerContext,
        *,
        channel_id: hikari.Snowflake,
        guild_id: hikari.Snowflake,
        session_id: str,
        shard_id: int,
        owner: VoiceComponent,
    ) -> None:
        # super().__init__(channel_id, guild_id, shard_id)
        self.player = player
        self.lavalink = lavalink_client

        self.__session_id = session_id
        self.__owner = owner
        self.__should_close = True

    @staticmethod
    async def reconnect(
        player: PlayerContext, endpoint: str, token: str, session_id: str
    ) -> None:
        update_player = UpdatePlayer()
        connection_info = ConnectionInfo(endpoint, token, session_id)
        connection_info.fix()
        update_player.voice = connection_info
        await player.update_player(update_player, True)

    async def disconnect(self) -> None:
        """Signal the process to shut down."""
        if self.__should_disconnect:
            await self.lavalink.delete_player(self.guild_id)
        else:
            self.__should_disconnect = True

    async def notify(self, event: hikari.VoiceEvent) -> None:
        """Submit an event to the voice connection to be processed."""
        #     if isinstance(event, hikari.VoiceServerUpdateEvent):
        #         # Handle the bot being moved frome one channel to another
        #         assert event.raw_endpoint
        #         update_player = UpdatePlayer()
        #         connection_info = ConnectionInfo(
        #             event.raw_endpoint, event.token, self.__session_id
        #         )
        #         connection_info.fix()
        #         update_player.voice = connection_info
        #         await self.player.update_player(update_player, True)
        if not isinstance(event, hikari.VoiceServerUpdateEvent):
            return

        # TODO handle this better
        # https://discord.com/developers/docs/topics/gateway-events#voice-server-update
        assert event.raw_endpoint

        # Handle the bot being moved frome one channel to another
        await LavalinkVoice.reconnect(
            self.player, event.raw_endpoint, event.token, self.__session_id
        )

    @property
    def owner(self) -> VoiceComponent:
        """Return the component that is managing this connection."""
        return self.__owner

    @classmethod
    async def connect(
        cls,
        guild_id: hikari.Snowflake,
        channel_id: hikari.Snowflake,
        client: hikari.GatewayBot,
        lavalink_client: LavalinkClient,
        player_data: t.Any,
        deaf: bool = True,
    ) -> LavalinkVoice:
        try:
            conn = client.voice.connections.get(guild_id)
            if conn:
                assert isinstance(conn, LavalinkVoice)
                conn.__should_disconnect = False
                await client.voice.disconnect(guild_id)
        except:
            pass

        voice = await client.voice.connect_to(
            guild_id,
            channel_id,
            disconnect_existing=False,
            voice_connection_type=LavalinkVoice,
            lavalink_client=lavalink_client,
            player_data=player_data,
            deaf=deaf,
        )

        return voice

    @classmethod
    async def initialize(
        cls,
        channel_id: hikari.Snowflake,
        endpoint: str,
        guild_id: hikari.Snowflake,
        owner: VoiceComponent,
        session_id: str,
        shard_id: int,
        token: str,
        user_id: hikari.Snowflake,
        **kwargs: t.Any,
    ) -> LavalinkVoice:
        del user_id
        lavalink_client = kwargs["lavalink_client"]
        player_data = kwargs["player_data"]

        player = lavalink_client.get_player_context(guild_id)

        if player:
            await LavalinkVoice.reconnect(player, endpoint, token, session_id)
        else:
            player = await lavalink_client.create_player_context(
                guild_id, endpoint, token, session_id
            )

        if player_data:
            player.data = player_data

        self = LavalinkVoice(
            lavalink_client,
            player,
            channel_id=channel_id,
            guild_id=guild_id,
            session_id=session_id,
            shard_id=shard_id,
            owner=owner,
        )

        return self
