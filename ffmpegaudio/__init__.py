from .ffmpegaudio import Audio
import os
import subprocess

def verify_ffmpeg_avconv():
    try:
        subprocess.call(["ffmpeg", "-version"], stdout=subprocess.DEVNULL)
    except FileNotFoundError:
        pass
    else:
        return "ffmpeg"

def setup(bot):
    player = verify_ffmpeg_avconv()

    if not player:
        if os.name == "nt":
            msg = "ffmpeg isn't installed"
        else:
            msg = "Neither ffmpeg nor avconv are installed"
        raise RuntimeError(
            "{}.\nConsult the guide for your operating system "
            "and do ALL the steps in order.\n"
            "https://twentysix26.github.io/Red-Docs/\n"
            "".format(msg))

    n = Audio(bot, player=player)  # Praise 26
    bot.add_cog(n)
    bot.add_listener(n.voice_state_update, 'on_voice_state_update')
    bot.loop.create_task(n.queue_scheduler())
    bot.loop.create_task(n.disconnect_timer())
    bot.loop.create_task(n.reload_monitor())
    bot.loop.create_task(n.cache_scheduler())