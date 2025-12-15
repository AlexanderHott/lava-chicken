import lavalink_rs
import lightbulb

loader = lightbulb.Loader()


@loader.command
class Pause(
    lightbulb.SlashCommand, name="pause", description="pause the current track"
):
    @lightbulb.invoke
    async def invoke(
        self, ctx: lightbulb.Context, lavalink_client: lavalink_rs.LavalinkClient
    ):
        if not ctx.guild_id:
            return

        player_ctx = lavalink_client.get_player_context(ctx.guild_id)
        if not player_ctx:
            await ctx.respond("no player_ctx")
            return

        await player_ctx.set_pause(True)
        await ctx.respond("paused")

@loader.command
class Resume(
    lightbulb.SlashCommand,
    name="resume",
    description="resume the current track",
):
    @lightbulb.invoke
    async def invoke(
            self, ctx: lightbulb.Context,
            lavalink_client: lavalink_rs.LavalinkClient
    ):
        if not ctx.guild_id:
            return

        player_ctx = lavalink_client.get_player_context(ctx.guild_id)
        if not player_ctx:
            await ctx.respond("no player_ctx")
            return

        await player_ctx.set_pause(False)
        await ctx.respond("resumed")