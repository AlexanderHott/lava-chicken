import lightbulb

loader = lightbulb.Loader()


@loader.command
class Reload(lightbulb.SlashCommand, name="reload", description="reload extensions"):
    @lightbulb.invoke
    async def invoke(
        self, ctx: lightbulb.Context, client: lightbulb.GatewayEnabledClient
    ):
        await client.reload_extensions("lavachicken.extensions.player", "lavachicken.extensions.reload")
        await ctx.respond("Reloaded `extensions.player`, `extensions.reload`")
