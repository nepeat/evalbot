import logging
import asyncio
import sys
import bottom
import ssl

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

state = {
    "running": True
}
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
    log.info(f"Connected to {host}:{port}")
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

    log.info(f"Joining channel {channel}")
    bot.send("JOIN", channel=channel)


@bot.on("CLIENT_DISCONNECT")
async def on_disconnect(**kwargs):
    log.info("Disconnected!")
    try:
        await bot.connect()
    except ssl.SSLError:
        await asyncio.sleep(30)
        log.info("Rate limited, sleeping 30 seconds before reconnecting.")
        await bot.connect()
    except Exception as e:
        print(e)
        state["running"] = False


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
    log.info("running command: " + command)
    process = await asyncio.create_subprocess_shell(command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    await asyncio.gather(
        watch(process.stdout),
        watch(process.stderr)
    )


async def main():
    # Kick off the first connection.
    await bot.connect()

    # Infinitely wait while running.
    while state["running"]:
        await asyncio.sleep(1)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())

