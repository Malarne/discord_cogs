import discord
from redbot.core import commands
import threading
import os
from redbot.core import checks, Config
from random import shuffle, choice
from redbot.core.utils.chat_formatting import pagify
from urllib.parse import urlparse
import re
import logging
import collections
import copy
import asyncio
import math
from random import randint
import time
import inspect
import subprocess
import urllib.parse
import contextlib
from enum import Enum
from redbot.core.data_manager import bundled_data_path

__author__ = "Malarne#1418"
__version__ = "0.1.1"

contextlib.suppress(Exception) ##This fix A LOT of errors, don't ask how, it just does


##original code from v2 audio.py
try:
    import youtube_dl
except:
    youtube_dl = None

try:
    if not discord.opus.is_loaded():
        discord.opus.load_opus("libopus-0.dll")
except OSError:  # Incorrect bitness
    opus = False
except:  # Missing opus
    opus = None
else:
    opus = True


class MaximumLength(Exception):
    def __init__(self, m):
        self.message = m

    def __str__(self):
        return self.message


class NotConnected(Exception):
    pass


class YouTubeDlError(Exception):
    def __init__(self, m):
        self.message = m

    def __str__(self):
        return self.message


class AuthorNotConnected(NotConnected):
    pass


class VoiceNotConnected(NotConnected):
    pass


class UnauthorizedConnect(Exception):
    pass


class UnauthorizedSpeak(Exception):
    pass


class ChannelUserLimit(Exception):
    pass


class UnauthorizedSave(Exception):
    pass


class ConnectTimeout(NotConnected):
    pass


class InvalidURL(Exception):
    pass


class InvalidSong(InvalidURL):
    pass


class InvalidPlaylist(InvalidSong):
    pass


class deque(collections.deque):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def peek(self):
        ret = self.pop()
        self.append(ret)
        return copy.deepcopy(ret)

    def peekleft(self):
        ret = self.popleft()
        self.appendleft(ret)
        return copy.deepcopy(ret)


class QueueKey(Enum):
    REPEAT = 1
    PLAYLIST = 2
    VOICE_CHANNEL_ID = 3
    QUEUE = 4
    TEMP_QUEUE = 5
    NOW_PLAYING = 6
    NOW_PLAYING_CHANNEL = 7


class Song:
    def __init__(self, **kwargs):
        self.__dict__ = kwargs
        self.title = kwargs.pop("title", None)
        self.id = kwargs.pop("id", None)
        self.url = kwargs.pop("url", None)
        self.webpage_url = kwargs.pop("webpage_url", "")
        self.duration = kwargs.pop("duration", 60)
        self.start_time = kwargs.pop("start_time", None)
        self.end_time = kwargs.pop("end_time", None)


class QueuedSong:
    def __init__(self, url, channel):
        self.url = url
        self.channel = channel


class Downloader(threading.Thread):
    def __init__(
        self,
        url,
        max_duration=None,
        download=False,
        cache_path=None,
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.url = url
        self.max_duration = max_duration
        self.done = threading.Event()
        self.song = None
        self._download = download
        self.hit_max_length = threading.Event()
        self._yt = None
        self.error = None
        self.youtube_dl_options = self.ytdlopt()

    
    def ytdlopt(self):
        self.youtube_dl_options = {
            "source_address": "0.0.0.0",
            "format": "bestaudio/best",
            "extractaudio": True,
            "audioformat": "mp3",
            "nocheckcertificate": True,
            "ignoreerrors": False,
            "quiet": True,
            "no_warnings": True,
            "outtmpl": (str(bundled_data_path(self)) + "/%(id)s"),
            "default_search": "auto",
            "encoding": "utf-8",
        }
        return self.youtube_dl_options

    def run(self):
        try:
            self.get_info()
            if self._download:
                self.download()
        except youtube_dl.utils.DownloadError as e:
            self.error = str(e)
        except MaximumLength:
            self.hit_max_length.set()
        except OSError as e:
            print(
                "An operating system error occurred while downloading URL '{}':\n'{}'".format(
                    self.url, str(e)
                )
            )
        self.done.set()

    def download(self):
        self.duration_check()

        if not os.path.isfile(str(bundled_data_path(self)) + "/" + self.song.id):
            video = self._yt.extract_info(self.url)
            self.song = Song(**video)

    def duration_check(self):
        print("duration {} for songid {}".format(self.song.duration, self.song.id))
        if self.max_duration and self.song.duration > self.max_duration:
            print("songid {} too long".format(self.song.id))
            raise MaximumLength(
                "songid {} has duration {} > {}".format(
                    self.song.id, self.song.duration, self.max_duration
                )
            )

    def get_info(self):
        if self._yt is None:
            self._yt = youtube_dl.YoutubeDL(self.youtube_dl_options)
        if "[SEARCH:]" not in self.url:
            video = self._yt.extract_info(self.url, download=False, process=False)
        else:
            self.url = self.url[9:]
            yt_id = self._yt.extract_info(self.url, download=False)["entries"][0]["id"]
            # Should handle errors here ^
            self.url = "https://youtube.com/watch?v={}".format(yt_id)
            video = self._yt.extract_info(self.url, download=False, process=False)

        if video is not None:
            self.song = Song(**video)


class Audio(commands.Cog):
    """Music Streaming."""

    def __init__(self, bot, player):
        self.bot = bot
        self.queue = {}  # add deque's, repeat
        self.downloaders = {}  # sid: object
        self.settings = Config.get_conf(self, identifier=98117108108115104105116)
        default_global = {
            "AVCONV": False,
            "MAX_CACHE": 0,
            "MAX_LENGTH": 3700,
            "SOUNDCLOUD_CLIENT_ID": None,
            "TITLE_STATUS": False,
        }
        default_guild = {
            "NOPPL_DISCONNECT": True,
            "VOLUME": 30,
            "VOTE_ENABLED": True,
            "VOTE_THRESHOLD": 50,
        }
        self.settings.register_global(**default_global)
        self.settings.register_guild(**default_guild)
        self.cache_path = bundled_data_path(self)
        self._old_game = False

        self.skip_votes = {}

        self.connect_timers = {}

    async def _add_song_status(self, song):
        if self._old_game is False:
            self._old_game = list(self.bot.servers)[0].me.game
        status = list(self.bot.servers)[0].me.status
        game = discord.Activity(discord.Game(name=song.title))
        await self.bot.change_presence(status=status, activity=game)
        print("Bot status changed to song title: " + song.title)

    def _add_to_queue(self, server, url, channel):
        if server.id not in self.queue:
            self._setup_queue(server)
        queued_song = QueuedSong(url, channel)
        self.queue[server.id][QueueKey.QUEUE].append(queued_song)

    def _add_to_temp_queue(self, server, url, channel):
        if server.id not in self.queue:
            self._setup_queue(server)
        queued_song = QueuedSong(url, channel)
        self.queue[server.id][QueueKey.TEMP_QUEUE].append(queued_song)

    def _addleft_to_queue(self, server, url, channel):
        queued_song = QueuedSong(url, channel)
        self.queue[server.id][QueueKey.QUEUE].appendleft(queued_song)

    def _cache_desired_files(self):
        filelist = []
        for server in self.downloaders:
            song = self.downloaders[server].song
            try:
                filelist.append(song.id)
            except AttributeError:
                pass
        shuffle(filelist)
        return filelist

    async def _cache_max(self):
        setting_max = await self.settings.MAX_CACHE()
        return max([setting_max, self._cache_min()])  # enforcing hard limit

    def _cache_min(self):
        x = self._server_count()
        return max([60, 48 * math.log(x) * x ** 0.3])  # log is not log10

    def _cache_required_files(self):
        queue = copy.deepcopy(self.queue)
        filelist = []
        for server in queue:
            now_playing = queue[server].get(QueueKey.NOW_PLAYING)
            try:
                filelist.append(now_playing.id)
            except AttributeError:
                pass
        return filelist

    def _cache_size(self):
        songs = os.listdir(self.cache_path)
        size = sum(
            map(
                lambda s: os.path.getsize(os.path.join(self.cache_path, s)) / 10 ** 6,
                songs,
            )
        )
        return size

    async def _cache_too_large(self):
        if self._cache_size() > await self._cache_max():
            return True
        return False

    def _clear_queue(self, server):
        if server.id not in self.queue:
            return
        self.queue[server.id][QueueKey.QUEUE] = deque()
        self.queue[server.id][QueueKey.TEMP_QUEUE] = deque()

    async def _create_ffmpeg_player(
        self, server, filename, local=False, start_time=None, end_time=None
    ):
        """This function will guarantee we have a valid voice client,
            even if one doesn't exist previously."""
        voice_channel_id = self.queue[server.id][QueueKey.VOICE_CHANNEL_ID]
        voice_client = self.voice_client(server)

        if voice_client is None:
            print("not connected when we should be in sid {}".format(server.id))
            to_connect = self.bot.get_channel(voice_channel_id)
            if to_connect is None:
                raise VoiceNotConnected(
                    "Okay somehow we're not connected and"
                    " we have no valid channel to"
                    " reconnect to. In other words...LOL"
                    " REKT."
                )
            print(
                "valid reconnect channel for sid"
                " {}, reconnecting...".format(server.id)
            )
            await self._join_voice_channel(to_connect)  # SHIT
        elif voice_client.channel.id == voice_channel_id:
            # This was decided at 3:45 EST in #advanced-testing by 26
            self.queue[server.id][QueueKey.VOICE_CHANNEL_ID] = voice_channel_id
            print("reconnect chan id for sid {} is wrong, fixing".format(server.id))

        # Okay if we reach here we definitively have a working voice_client
        song_filename = os.path.join(self.cache_path, filename)

        options = "-b:a 64k -bufsize 64k"
        before_options = ""

        if start_time:
            before_options += "-ss {}".format(start_time)
        if end_time:
            options += " -to {} -copyts".format(end_time)

        try:
            voice_client.audio_player.process.kill()
            print("killed old player")
        except AttributeError:
            pass
        except ProcessLookupError:
            pass

        print("making player on sid {}".format(server.id))

        voice_client.audio_player = discord.FFmpegPCMAudio(
            song_filename,
            options=options,
            before_options=before_options,
        )

        # Set initial volume
        vol = await self.settings.guild(server).VOLUME() / 100
        voice_client.audio_player.volume = vol

        return voice_client  # Just for ease of use, it's modified in-place

    # TODO: _disable_controls()

    async def _disconnect_voice_client(self, server):
        if not self.voice_connected(server):
            return

        voice_client = self.voice_client(server)

        await voice_client.disconnect()

    async def _download_all(self, queued_song_list, channel):
        """
        Doesn't actually download, just get's info for uses like queue_list
        """
        downloaders = []
        for queued_song in queued_song_list:
            d = Downloader(queued_song.url)
            d.start()
            downloaders.append(d)

        while any([d.is_alive() for d in downloaders]):
            await asyncio.sleep(0.1)

        songs = [d.song for d in downloaders if d.song is not None and d.error is None]

        invalid_downloads = [d for d in downloaders if d.error is not None]
        invalid_number = len(invalid_downloads)
        if invalid_number > 0:
            await channel.send_message(
                "The queue contains {} item(s)"
                " that can not be played.".format(invalid_number)
            )

        return songs

    async def _download_next(self, server, curr_dl, next_dl):
        """Checks to see if we need to download the next, and does.

        Both curr_dl and next_dl should already be started."""
        if curr_dl.song is None:
            # Only happens when the downloader thread hasn't initialized fully
            #   There's no reason to wait if we can't compare
            return

        max_length = await self.settings.MAX_LENGTH()

        while next_dl.is_alive():
            await asyncio.sleep(0.5)

        error = next_dl.error
        if error is not None:
            raise YouTubeDlError(error)

        if curr_dl.song.id != next_dl.song.id:
            print(
                "downloader ID's mismatch on sid {}".format(server.id)
                + " gonna start dl-ing the next thing on the queue"
                " id {}".format(next_dl.song.id)
            )
            try:
                next_dl.duration_check()
            except MaximumLength:
                return
            self.downloaders[server.id] = Downloader(
                next_dl.url, max_length, download=True
            )
            self.downloaders[server.id].start()

    async def _dump_cache(self, ignore_desired=False):
        reqd = self._cache_required_files()
        print("required cache files:\n\t{}".format(reqd))

        opt = self._cache_desired_files()
        print("desired cache files:\n\t{}".format(opt))

        prev_size = self._cache_size()

        for file in os.listdir(self.cache_path):
            if file not in reqd:
                if ignore_desired or file not in opt:
                    try:
                        os.remove(os.path.join(self.cache_path, file))
                    except OSError:
                        # A directory got in the cache?
                        pass
                    except WindowsError:
                        # Removing a file in use, reqd failed
                        pass

        post_size = self._cache_size()
        dumped = prev_size - post_size

        if not ignore_desired and await self._cache_too_large():
            print("must dump desired files")
            return dumped + await self._dump_cache(ignore_desired=True)

        print("dumped {} MB of audio files".format(dumped))

        return dumped

    # TODO: _enable_controls()

    # returns list of active voice channels
    # assuming list does not change during the execution of this function
    # if that happens, blame asyncio.
    def _get_active_voice_clients(self):
        avcs = []
        for vc in self.bot.voice_clients:
            if hasattr(vc, "audio_player") and not vc.audio_player.is_done():
                avcs.append(vc)
        return avcs

    def _get_queue(self, server, limit):
        if server.id not in self.queue:
            return []

        ret = []
        for i in range(limit):
            try:
                ret.append(self.queue[server.id][QueueKey.QUEUE][i])
            except IndexError:
                pass

        return ret

    def _get_queue_nowplaying(self, server):
        if server.id not in self.queue:
            return None

        return self.queue[server.id][QueueKey.NOW_PLAYING]

    def _get_queue_nowplaying_channel(self, server):
        if server.id not in self.queue:
            return None

        return self.queue[server.id][QueueKey.NOW_PLAYING_CHANNEL]

    def _get_queue_playlist(self, server):
        if server.id not in self.queue:
            return None

        return self.queue[server.id][QueueKey.PLAYLIST]

    def _get_queue_repeat(self, server):
        if server.id not in self.queue:
            return None

        return self.queue[server.id][QueueKey.REPEAT]

    def _get_queue_tempqueue(self, server, limit):
        if server.id not in self.queue:
            return []

        ret = []
        for i in range(limit):
            try:
                ret.append(self.queue[server.id][QueueKey.TEMP_QUEUE][i])
            except IndexError:
                pass
        return ret

    async def _guarantee_downloaded(self, server, url):
        max_length = await self.settings.MAX_CACHE()
        if server.id not in self.downloaders:  # We don't have a downloader
            print("sid {} not in downloaders, making one".format(server.id))
            self.downloaders[server.id] = Downloader(url, max_length)

        if self.downloaders[server.id].url != url:  # Our downloader is old
            # I'm praying to Jeezus that we don't accidentally lose a running
            #   Downloader
            print("sid {} in downloaders but wrong url".format(server.id))
            self.downloaders[server.id] = Downloader(url, max_length)

        try:
            # We're assuming we have the right thing in our downloader object
            self.downloaders[server.id].start()
            print("starting our downloader for sid {}".format(server.id))
        except RuntimeError:
            # Queue manager already started it for us, isn't that nice?
            pass

        # Getting info w/o download
        self.downloaders[server.id].done.wait()

        # Youtube-DL threw an exception.
        error = self.downloaders[server.id].error
        if error is not None:
            raise YouTubeDlError(error)

        # This will throw a maxlength exception if required
        self.downloaders[server.id].duration_check()
        song = self.downloaders[server.id].song

        print("sid {} wants to play songid {}".format(server.id, song.id))

        # Now we check to see if we have a cache hit
        cache_location = os.path.join(self.cache_path, song.id)
        if not os.path.exists(cache_location):
            print("cache miss on song id {}".format(song.id))
            self.downloaders[server.id] = Downloader(url, max_length, download=True)
            self.downloaders[server.id].start()

            while self.downloaders[server.id].is_alive():
                await asyncio.sleep(0.5)

            song = self.downloaders[server.id].song
        else:
            print("cache hit on song id {}".format(song.id))

        return song

    def _is_queue_playlist(self, server):
        if server.id not in self.queue:
            return False

        return self.queue[server.id][QueueKey.PLAYLIST]

    async def _join_voice_channel(self, channel):
        server = channel.guild
        connect_time = self.connect_timers.get(server.id, 0)
        if time.time() < connect_time:
            diff = int(connect_time - time.time())
            raise ConnectTimeout(
                "You are on connect cooldown for another {}" " seconds.".format(diff)
            )
        if server.id in self.queue:
            self.queue[server.id][QueueKey.VOICE_CHANNEL_ID] = channel.id
        try:
            await asyncio.wait_for(
                channel.connect(), timeout=5, loop=self.bot.loop
            )
        except:# asyncio.futures.TimeoutError as e:
            pass
            #print(e)
            #self.connect_timers[server.id] = time.time() + 300
            #raise ConnectTimeout(
            #    "We timed out connecting to a voice channel,"
            #    " please try again in 10 minutes."
            #)
            
    def _match_sc_playlist(self, url):
        return self._match_sc_url(url)

    def _match_yt_playlist(self, url):
        if not self._match_yt_url(url):
            return False
        yt_playlist = re.compile(
            r"^(https?\:\/\/)?(www\.)?(youtube\.com|youtu\.?be)"
            r"((\/playlist\?)|\/watch\?).*(list=)(.*)(&|$)"
        )
        # Group 6 should be the list ID
        if yt_playlist.match(url):
            return True
        return False

    def _match_sc_url(self, url):
        sc_url = re.compile(r"^(https?\:\/\/)?(www\.)?(soundcloud\.com\/)")
        if sc_url.match(url):
            return True
        return False

    def _match_yt_url(self, url):
        yt_link = re.compile(
            r"^(https?\:\/\/)?(www\.|m\.)?(youtube\.com|youtu\.?be)\/.+$"
        )
        if yt_link.match(url):
            return True
        return False

    def _match_any_url(self, url):
        url = urlparse(url)
        if url.scheme and url.netloc and url.path:
            return True
        return False

    # TODO: _next_songs_in_queue

    async def _parse_playlist(self, url):
        if self._match_sc_playlist(url):
            return await self._parse_sc_playlist(url)
        elif self._match_yt_playlist(url):
            return await self._parse_yt_playlist(url)
        raise InvalidPlaylist(
            "The given URL is neither a Soundcloud or" " YouTube playlist."
        )

    async def _parse_sc_playlist(self, url):
        playlist = []
        d = Downloader(url)
        d.start()

        while d.is_alive():
            await asyncio.sleep(0.5)

        error = d.error
        if error is not None:
            raise YouTubeDlError(error)

        for entry in d.song.entries:
            if entry["url"][4] != "s":
                song_url = "https{}".format(entry["url"][4:])
                playlist.append(song_url)
            else:
                playlist.append(entry.url)

        return playlist

    async def _parse_yt_playlist(self, url):
        d = Downloader(url)
        d.start()
        playlist = []

        while d.is_alive():
            await asyncio.sleep(0.5)

        error = d.error
        if error is not None:
            raise YouTubeDlError(error)

        for entry in d.song.entries:
            try:
                song_url = "https://www.youtube.com/watch?v={}".format(entry["id"])
                playlist.append(song_url)
            except AttributeError:
                pass
            except TypeError:
                pass

        print("song list:\n\t{}".format(playlist))

        return playlist

    async def _play(self, sid, url, channel):
        """Returns the song object of what's playing"""
        if type(sid) is not discord.Guild:
            server = self.bot.get_guild(sid)
        else:
            server = sid

        assert type(server) is discord.Guild
        print('starting to play on "{}"'.format(server.name))

        if self._valid_playable_url(url) or "[SEARCH:]" in url:
            clean_url = self._clean_url(url)
            try:
                song = await self._guarantee_downloaded(server, url)
            except YouTubeDlError as e:
                message = (
                    "I'm unable to play '{}' because of an error:\n"
                    "'{}'".format(clean_url, str(e))
                )
                await channel.send(message)
                return
            except MaximumLength:
                message = (
                    "I'm unable to play '{}' because it exceeds the "
                    "maximum audio length.".format(clean_url)
                )
                await channel.send(message)
                return
            local = False
        else:  # Assume local
            pass

        voice_client = await self._create_ffmpeg_player(
            server,
            song.id,
            local=local,
            start_time=song.start_time,
            end_time=song.end_time,
        )
        # That ^ creates the audio_player property

        voice_client.play(voice_client.audio_player)
        print("starting player on sid {}".format(server.id))

        return song

    def _songlist_change_url_to_queued_song(self, songlist, channel):
        queued_songlist = []
        for song in songlist:
            queued_song = QueuedSong(song, channel)
            queued_songlist.append(queued_song)

        return queued_songlist

    def _player_count(self):
        count = 0
        queue = copy.deepcopy(self.queue)
        for sid in queue:
            server = self.bot.get_server(sid)
            try:
                vc = self.voice_client(server)
                if vc.audio_player.is_playing():
                    count += 1
            except:
                pass
        return count

    def _remove_queue(self, server):
        if server.id in self.queue:
            del self.queue[server.id]

    async def _remove_song_status(self):
        if self._old_game is not False:
            status = list(self.bot.servers)[0].me.status
            await self.bot.change_presence(game=self._old_game, status=status)
            print("Bot status returned to " + str(self._old_game))
            self._old_game = False

    def _shuffle_queue(self, server):
        shuffle(self.queue[server.id][QueueKey.QUEUE])

    def _shuffle_temp_queue(self, server):
        shuffle(self.queue[server.id][QueueKey.TEMP_QUEUE])

    def _server_count(self):
        return max([1, len(self.bot.guilds)])

    def _set_queue(self, server, songlist):
        if server.id in self.queue:
            self._clear_queue(server)
        else:
            self._setup_queue(server)
        self.queue[server.id][QueueKey.QUEUE].extend(songlist)

    def _set_queue_channel(self, server, channel):
        if server.id not in self.queue:
            return

        try:
            channel = channel.id
        except AttributeError:
            pass

        self.queue[server.id][QueueKey.VOICE_CHANNEL_ID] = channel

    def _set_queue_nowplaying(self, server, song, channel):
        if server.id not in self.queue:
            return

        self.queue[server.id][QueueKey.NOW_PLAYING] = song
        self.queue[server.id][QueueKey.NOW_PLAYING_CHANNEL] = channel

    def _set_queue_playlist(self, server, name=True):
        if server.id not in self.queue:
            self._setup_queue(server)

        self.queue[server.id][QueueKey.PLAYLIST] = name

    def _set_queue_repeat(self, server, value):
        if server.id not in self.queue:
            self._setup_queue(server)

        self.queue[server.id][QueueKey.REPEAT] = value

    def _setup_queue(self, server):
        self.queue[server.id] = {
            QueueKey.REPEAT: False,
            QueueKey.PLAYLIST: False,
            QueueKey.VOICE_CHANNEL_ID: None,
            QueueKey.QUEUE: deque(),
            QueueKey.TEMP_QUEUE: deque(),
            QueueKey.NOW_PLAYING: None,
            QueueKey.NOW_PLAYING_CHANNEL: None,
        }

    def _stop(self, server):
        self._setup_queue(server)
        self._stop_player(server)
        self._stop_downloader(server)
        self.bot.loop.create_task(self._update_bot_status())

    async def _stop_and_disconnect(self, server):
        self._stop(server)
        for client in self.bot.voice_clients:
            if client.guild.id == server.id:
                await client.disconnect()

    def _stop_downloader(self, server):
        if server.id not in self.downloaders:
            return

        del self.downloaders[server.id]

    def _stop_player(self, server):
        if not self.voice_connected(server):
            return

        voice_client = [x for x in self.bot.voice_clients if x.guild.id == server.id][0]

        if hasattr(voice_client, "audio_player"):
            voice_client.stop()

    # no return. they can check themselves.
    async def _update_bot_status(self):
        if await self.settings.TITLE_STATUS():
            song = None
            try:
                active_servers = self._get_active_voice_clients()
            except:
                print(
                    "Voice client changed while trying to update bot's" " song status"
                )
                return
            if len(active_servers) == 1:
                server = active_servers[0].server
                song = self._get_queue_nowplaying(server)
            if song:
                await self._add_song_status(song)
            else:
                await self._remove_song_status()

    def _valid_playlist_name(self, name):
        for char in name:
            if char.isdigit() or char.isalpha() or char == "_":
                pass
            else:
                return False
        return True

    def _valid_playable_url(self, url):
        yt = self._match_yt_url(url)
        sc = self._match_sc_url(url)
        if yt or sc:  # TODO: Add sc check
            return True
        return False

    def _clean_url(self, url):
        if self._valid_playable_url(url):
            return "<{}>".format(url)

        return url.replace("[SEARCH:]", "")

    @commands.group()
    async def audioset(self, ctx):
        """Audio settings."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help()
            return

    @audioset.command(name="cachemax")
    @checks.is_owner()
    async def audioset_cachemax(self, ctx, size: int):
        """Set the max cache size in MB"""
        if size < self._cache_min():
            await ctx.send(
                "Sorry, but because of the number of servers"
                " that your bot is in I cannot safely allow"
                " you to have less than {} MB of cache.".format(self._cache_min())
            )
            return

        await self.settings.MAX_LENGTH.set(size)
        await ctx.send("Max cache size set to {} MB.".format(size))

    @audioset.command(name="emptydisconnect", pass_context=True)
    @checks.mod_or_permissions(manage_messages=True)
    async def audioset_emptydisconnect(self, ctx):
        """Toggles auto disconnection when everyone leaves the channel"""
        noppl_disconnect = await self.settings.guild(ctx.guild).NOPPL_DISCONNECT()
        await self.settings.guild(ctx.guild).NOPPL_DISCONNECT.set(not noppl_disconnect)
        if not noppl_disconnect:
            await ctx.send(
                "If there is no one left in the voice channel"
                " the bot will automatically disconnect after"
                " five minutes."
            )
        else:
            await ctx.send(
                "The bot will no longer auto disconnect"
                " if the voice channel is empty."
            )

    @audioset.command(name="maxlength")
    @checks.is_owner()
    async def audioset_maxlength(self, ctx, length: int):
        """Maximum track length (seconds) for requested links"""
        if length <= 0:
            await ctx.send("Wow, a non-positive length value...aren't" " you smart.")
            return
        await self.settings.MAX_LENGTH.set(length)
        await ctx.send("Maximum length is now {} seconds.".format(length))

    @audioset.command(name="status")
    @checks.is_owner()  # cause effect is cross-server
    async def audioset_status(self, ctx):
        """Enables/disables songs' titles as status"""
        cur = await self.settings.TITLE_STATUS()
        await self.settings.TITLE_STATUS.set(not cur)
        if not cur:
            await ctx.send(
                "If only one server is playing music, songs'"
                " titles will now show up as status"
            )
            # not updating on disable if we say disable
            #   means don't mess with it.
            await self._update_bot_status()
        else:
            await ctx.send("Songs' titles will no longer show up as" " status")

    @audioset.command(pass_context=True, name="volume", no_pm=True)
    @checks.mod_or_permissions(manage_messages=True)
    async def audioset_volume(self, ctx, percent: int = None):
        """Sets the volume (0 - 100)
        Note: volume may be set up to 200 but you may experience clipping."""
        if percent is None:
            vol = await self.settings.guild(ctx.guild).VOLUME()
            msg = "Volume is currently set to %d%%" % vol
        elif percent >= 0 and percent <= 200:
            await self.settings.guild(ctx.guild).VOLUME.set(percent)
            msg = "Volume is now set to %d." % percent
            if percent > 100:
                msg += "\nWarning: volume levels above 100 may result in" " clipping"

            # Set volume of playing audio
            vc = self.voice_client(ctx.guild)
            if vc:
                vc.audio_player.volume = percent / 100

        else:
            msg = "Volume must be between 0 and 100."
        await ctx.send(msg)

    @audioset.command(pass_context=True, name="vote", no_pm=True)
    @checks.mod_or_permissions(manage_messages=True)
    async def audioset_vote(self, ctx, percent: int):
        """Percentage needed for the masses to skip songs. 0 to disable."""

        if percent < 0:
            await ctx.send("Can't be less than zero.")
            return
        elif percent > 100:
            percent = 100

        if percent == 0:
            enabled = False
            await ctx.send("Voting disabled. All users can stop or skip.")
        else:
            enabled = True
            await ctx.send("Vote percentage set to {}%".format(percent))

        await self.settings.guild(ctx.guild).VOTE_THRESHOLD.set(percent)
        await self.settings.guild(ctx.guild).VOTE_ENABLED.set(enabled)

    @commands.group(pass_context=True)
    async def audiostat(self, ctx):
        """General stats on audio stuff."""
        pass

    @audiostat.command(name="servers")
    async def audiostat_servers(self, ctx):
        """Number of servers currently playing."""

        count = self._player_count()

        await ctx.send("Currently playing music in {} servers.".format(count))

    @commands.group(pass_context=True)
    async def cache(self, ctx):
        """Cache management tools."""
        pass

    @cache.command(name="dump")
    @checks.is_owner()
    async def cache_dump(self, ctx):
        """Dumps the cache."""
        dumped = await self._dump_cache()
        await ctx.send("Dumped {:.3f} MB of audio files.".format(dumped))

    @cache.command(name="stats")
    async def cache_stats(self, ctx):
        """Reports info about the cache.
            - Current size of the cache.
            - Maximum cache size. User setting or minimum, whichever is higher.
            - Minimum cache size. Automatically determined by number of servers Red is running on.
        """
        await ctx.send(
            "Cache stats:\n"
            "Current size: {:.2f} MB\n"
            "Maximum: {:.1f} MB\n"
            "Minimum: {:.1f} MB".format(
                self._cache_size(), await self._cache_max(), self._cache_min()
            )
        )

    @commands.group(pass_context=True, hidden=True, no_pm=True, auto_help=False)
    @checks.is_owner()
    async def disconnect(self, ctx):
        """Disconnects from voice channel in current server."""
        if ctx.invoked_subcommand is None:
            server = ctx.guild
            await self._stop_and_disconnect(server)

    @disconnect.command(name="all", hidden=True, no_pm=True)
    async def disconnect_all(self, ctx):
        """Disconnects from all voice channels."""
        for client in self.bot.voice_clients:
            await client.disconnect()
        await ctx.send("done.")

    @commands.command(hidden=True, pass_context=True, no_pm=True)
    @checks.is_owner()
    async def joinvoice(self, ctx):
        """Joins your voice channel"""
        author = ctx.message.author
        server = ctx.guild
        voice_channel = author.voice.channel

        if voice_channel is not None:
            self._stop(server)

        await self._join_voice_channel(voice_channel)

    @commands.command(pass_context=True, no_pm=True)
    async def pause(self, ctx):
        """Pauses the current song, `[p]resume` to continue."""
        server = ctx.guild
        if not self.voice_connected(server):
            await ctx.send("Not voice connected in this server.")
            return

        # We are connected somewhere
        voice_client = self.voice_client(server)

        if not hasattr(voice_client, "audio_player"):
            await ctx.send("Nothing playing, nothing to pause.")
        elif voice_client.audio_player.is_playing():
            voice_client.pause()
            await ctx.send("Paused.")
        else:
            await ctx.send("Nothing playing, nothing to pause.")

    @commands.command(pass_context=True, no_pm=True)
    async def play(self, ctx, *, url_or_search_terms):
        """Plays a link / searches and play"""

        if randint(0,20) <= 2:
            return await ctx.send("Not now, i'm too lazy ...")
        url = url_or_search_terms
        server = ctx.guild
        author = ctx.message.author
        voice_channel = author.voice.channel
        channel = ctx.message.channel

        # Checking if playing in current server

        if self.is_playing(server):
            await ctx.invoke(self._queue, url=url)
            return  # Default to queue

        # Checking already connected, will join if not

        try:
            self.has_connect_perm(author, server)
        except AuthorNotConnected:
            await ctx.send(
                "You must join a voice channel before I can" " play anything."
            )
            return
        except UnauthorizedConnect:
            await ctx.send("I don't have permissions to join your" " voice channel.")
            return
        except UnauthorizedSpeak:
            await ctx.send(
                "I don't have permissions to speak in your" " voice channel."
            )
            return
        except ChannelUserLimit:
            await ctx.send("Your voice channel is full.")
            return

        if not self.voice_connected(server):
            await self._join_voice_channel(voice_channel)
        else:  # We are connected but not to the right channel
            if self.voice_client(server).channel != voice_channel:
                await self._stop_and_disconnect(server)
                await self._join_voice_channel(voice_channel)


        if self.currently_downloading(server):
            await ctx.send("I'm already downloading a file!")
            return

        url = url.strip("<>")

        if self._match_any_url(url):
            if not self._valid_playable_url(url):
                await ctx.send("That's not a valid URL.")
                return
        else:
            url = url.replace("/", "&#47")
            url = "[SEARCH:]" + url

        if "[SEARCH:]" not in url and "youtube" in url:
            parsed_url = urllib.parse.urlparse(url)
            query = urllib.parse.parse_qs(parsed_url.query)
            query.pop("list", None)
            parsed_url = parsed_url._replace(query=urllib.parse.urlencode(query, True))
            url = urllib.parse.urlunparse(parsed_url)

        self._stop_player(server)
        self._clear_queue(server)
        self._add_to_queue(server, url, channel)

    @commands.command(pass_context=True, no_pm=True)
    async def prev(self, ctx):
        """Goes back to the last song."""
        # Current song is in NOW_PLAYING
        server = ctx.guild
        channel = ctx.message.channel

        if self.is_playing(server):
            curr_url = self._get_queue_nowplaying(server).webpage_url
            last_url = None
            if self._is_queue_playlist(server):
                # need to reorder queue
                try:
                    last_url = self.queue[server.id][QueueKey.QUEUE].pop()
                except IndexError:
                    pass

            print("prev on sid {}, curr_url {}".format(server.id, curr_url))

            self._addleft_to_queue(server, curr_url, channel)
            if last_url:
                self._addleft_to_queue(server, last_url, channel)
            self._set_queue_nowplaying(server, None, None)

            self.voice_client(server).audio_player.stop()

            await ctx.send("Going back 1 song.")
        else:
            await ctx.send("Not playing anything on this server.")

    @commands.command(pass_context=True, no_pm=True, name="queue")
    async def _queue(self, ctx, *, url=None):
        """Queues a song to play next. Extended functionality in `[p]help`

        If you use `queue` when one song is playing, your new song will get
            added to the song loop (if running). If you use `queue` when a
            playlist is running, it will temporarily be played next and will
            NOT stay in the playlist loop."""
        if url is None:
            return await self._queue_list(ctx)
        server = ctx.guild
        channel = ctx.message.channel
        if not self.voice_connected(server):
            await ctx.invoke(self.play, url_or_search_terms=url)
            return

        # We are connected somewhere
        if server.id not in self.queue:
            print("Something went wrong, we're connected but have no" " queue entry.")
            raise VoiceNotConnected(
                "Something went wrong, we have no internal"
                " queue to modify. This should never"
                " happen."
            )

        url = url.strip("<>")

        if self._match_any_url(url):
            if not self._valid_playable_url(url):
                await ctx.send("That's not a valid URL.")
                return
        else:
            url = "[SEARCH:]" + url

        if "[SEARCH:]" not in url and "youtube" in url:
            parsed_url = urllib.parse.urlparse(url)
            query = urllib.parse.parse_qs(parsed_url.query)
            query.pop("list", None)
            parsed_url = parsed_url._replace(query=urllib.parse.urlencode(query, True))
            url = urllib.parse.urlunparse(parsed_url)

        # We have a queue to modify
        if self.queue[server.id][QueueKey.PLAYLIST]:
            print("queueing to the temp_queue for sid {}".format(server.id))
            self._add_to_temp_queue(server, url, channel)
        else:
            print("queueing to the actual queue for sid {}".format(server.id))
            self._add_to_queue(server, url, channel)
        await ctx.send("Queued.")

    async def _queue_list(self, ctx):
        """Not a command, use `queue` with no args to call this."""
        server = ctx.guild
        channel = ctx.message.channel
        if server.id not in self.queue:
            await ctx.send("Nothing playing on this server!")
            return
        elif len(self.queue[server.id][QueueKey.QUEUE]) == 0:
            await ctx.send("Nothing queued on this server.")
            return

        msg = ""

        now_playing = self._get_queue_nowplaying(server)

        if now_playing is not None:
            msg += "\n***Now playing:***\n{}\n".format(now_playing.title)

        queued_song_list = self._get_queue(server, 5)
        tempqueued_song_list = self._get_queue_tempqueue(server, 5)

        await ctx.send("Gathering information...")

        queue_song_list = await self._download_all(queued_song_list, channel)
        tempqueue_song_list = await self._download_all(tempqueued_song_list, channel)

        song_info = []
        for num, song in enumerate(tempqueue_song_list, 1):
            try:
                song_info.append("{}. {.title}".format(num, song))
            except AttributeError:
                song_info.append("{}. {.webpage_url}".format(num, song))

        for num, song in enumerate(queue_song_list, len(song_info) + 1):
            if num > 5:
                break
            try:
                song_info.append("{}. {.title}".format(num, song))
            except AttributeError:
                song_info.append("{}. {.webpage_url}".format(num, song))
        msg += "\n***Next up:***\n" + "\n".join(song_info)

        await ctx.send(msg)

    @commands.group(pass_context=True, no_pm=True)
    async def repeat(self, ctx):
        """Toggles REPEAT"""
        server = ctx.guild
        if ctx.invoked_subcommand is None:
            if self.is_playing(server):
                if self.queue[server.id][QueueKey.REPEAT]:
                    msg = "The queue is currently looping."
                else:
                    msg = "The queue is currently not looping."
                await ctx.send(msg)
                await ctx.send(
                    "Do `{}repeat toggle` to change this.".format(ctx.prefix)
                )
            else:
                await ctx.send("Play something to see this setting.")

    @repeat.command(pass_context=True, no_pm=True, name="toggle")
    async def repeat_toggle(self, ctx):
        """Flips repeat setting."""
        server = ctx.guild
        if not self.is_playing(server):
            await ctx.send(
                "I don't have a repeat setting to flip." " Try playing something first."
            )
            return

        self._set_queue_repeat(server, not self.queue[server.id][QueueKey.REPEAT])
        repeat = self.queue[server.id][QueueKey.REPEAT]
        if repeat:
            await ctx.send("Repeat toggled on.")
        else:
            await ctx.send("Repeat toggled off.")

    @commands.command(pass_context=True, no_pm=True)
    async def resume(self, ctx):
        """Resumes a paused song or playlist"""
        server = ctx.guild
        if not self.voice_connected(server):
            await ctx.send("Not voice connected in this server.")
            return

        # We are connected somewhere
        voice_client = self.voice_client(server)

        if not hasattr(voice_client, "audio_player"):
            await ctx.send("Nothing paused, nothing to resume.")
        elif (
            not voice_client.audio_player.is_done()
            and not voice_client.audio_player.is_playing()
        ):
            voice_client.resume()
            await ctx.send("Resuming.")
        else:
            await ctx.send("Nothing paused, nothing to resume.")

    @commands.command(pass_context=True, no_pm=True, name="shuffle")
    async def _shuffle(self, ctx):
        """Shuffles the current queue"""
        server = ctx.guild
        if server.id not in self.queue:
            await ctx.send("I have nothing in queue to shuffle.")
            return

        self._shuffle_queue(server)
        self._shuffle_temp_queue(server)

        await ctx.send("Queues shuffled.")

    @commands.command(pass_context=True, aliases=["next"], no_pm=True)
    async def skip(self, ctx):
        """Skips a song, using the set threshold if the requester isn't
        a mod or admin. Mods, admins and bot owner are not counted in
        the vote threshold."""
        msg = ctx.message
        server = ctx.guild
        if self.is_playing(server):
            vchan = server.me.voice.channel
            vc = self.voice_client(server)
            if msg.author.voice.channel == vchan:
                if msg.author.id in self.skip_votes[server.id]:
                    self.skip_votes[server.id].remove(msg.author.id)
                    reply = "I removed your vote to skip."
                else:
                    self.skip_votes[server.id].append(msg.author.id)
                    reply = "you voted to skip."

                num_votes = len(self.skip_votes[server.id])
                # Exclude bots and non-plebs
                num_members = sum(not (m.bot) for m in vchan.voice_members)
                vote = int(100 * num_votes / num_members)
                thresh = await self.settings.guild(server).vote_THRESHOLD()

                if vote >= thresh:
                    vc.audio_player.stop()
                    if self._get_queue_repeat(server) is False:
                        self._set_queue_nowplaying(server, None, None)
                    self.skip_votes[server.id] = []
                    await ctx.send("Vote threshold met. Skipping...")
                    return
                else:
                    reply += " Votes: %d/%d" % (num_votes, num_members)
                    reply += " (%d%% out of %d%% needed)" % (vote, thresh)
                await ctx.send(reply)
            else:
                await ctx.send("You need to be in the voice channel to skip the music.")
        else:
            await ctx.send("Can't skip if I'm not playing.")

    @commands.command(pass_context=True, no_pm=True)
    async def sing(self, ctx):
        """Makes Red sing one of her songs"""
        ids = (
            "zGTkAVsrfg8",
            "cGMWL8cOeAU",
            "vFrjMq4aL-g",
            "WROI5WYBU_A",
            "41tIUr_ex3g",
            "f9O2Rjn1azc",
        )
        url = "https://www.youtube.com/watch?v={}".format(choice(ids))
        await ctx.invoke(self.play, url_or_search_terms=url)

    @commands.command(pass_context=True, no_pm=True)
    async def song(self, ctx):
        """Info about the current song."""
        server = ctx.guild
        if not self.is_playing(server):
            await ctx.send("I'm not playing on this server.")
            return

        song = self._get_queue_nowplaying(server)
        if song:
            if not hasattr(song, "creator"):
                song.creator = None
            if not hasattr(song, "view_count"):
                song.view_count = None
            if not hasattr(song, "uploader"):
                song.uploader = None
            if hasattr(song, "duration"):
                m, s = divmod(song.duration, 60)
                h, m = divmod(m, 60)
                if h:
                    dur = "{0}:{1:0>2}:{2:0>2}".format(h, m, s)
                else:
                    dur = "{0}:{1:0>2}".format(m, s)
            else:
                dur = None
            msg = (
                "\n**Title:** {}\n**Author:** {}\n**Uploader:** {}\n"
                "**Views:** {}\n**Duration:** {}\n\n<{}>".format(
                    song.title,
                    song.creator,
                    song.uploader,
                    song.view_count,
                    dur,
                    song.webpage_url,
                )
            )
            await ctx.send(
                msg.replace("**Author:** None\n", "")
                .replace("**Views:** None\n", "")
                .replace("**Uploader:** None\n", "")
                .replace("**Duration:** None\n", "")
            )
        else:
            await ctx.send("Darude - Sandstorm.")

    @commands.command(name="yt", pass_context=True, no_pm=True)
    async def yt_search(self, ctx, *, search_terms: str):
        """Searches and plays a video from YouTube"""
        await ctx.send("Searching...")
        await ctx.invoke(self.play, url_or_search_terms=search_terms)

    def is_playing(self, server):
        if not self.voice_connected(server):
            return False
        if self.voice_client(server) is None:
            return False
        if not hasattr(self.voice_client(server), "audio_player"):
            return False
        if not self.voice_client(server).is_playing():
            return False
        return True

    async def cache_manager(self):
        while self == self.bot.get_cog("Audio"):
            if await self._cache_too_large():
                # Our cache is too big, dumping
                print(
                    "cache too large ({} > {}), dumping".format(
                        self._cache_size(), await self._cache_max()
                    )
                )
                await self._dump_cache()
            await asyncio.sleep(5)  # No need to run this every half second

    async def cache_scheduler(self):
        await asyncio.sleep(30)  # Extra careful

        self.bot.loop.create_task(self.cache_manager())

    def currently_downloading(self, server):
        if server.id in self.downloaders:
            if self.downloaders[server.id].is_alive():
                return True
        return False

    async def disconnect_timer(self):
        stop_times = {}
        while self == self.bot.get_cog("Audio"):
            for vc in self.bot.voice_clients:
                server = vc.guild
                if not hasattr(vc, "audio_player") and (
                    server not in stop_times or stop_times[server] is None
                ):
                    print("putting sid {} in stop loop, no player".format(server.id))
                    stop_times[server] = int(time.time())

                if hasattr(vc, "audio_player"):
                    if not vc.is_playing():
                        if server not in stop_times or stop_times[server] is None:
                            print("putting sid {} in stop loop".format(server.id))
                            stop_times[server] = int(time.time())

                    if vc.is_playing():
                        stop_times[server] = None

            for server in stop_times:
                if stop_times[server] and int(time.time()) - stop_times[server] > 300:
                    # 5 min not playing to d/c
                    print("dcing from sid {} after 300s".format(server.id))
                    self._clear_queue(server)
                    await self._stop_and_disconnect(server)
                    stop_times[server] = None
            await asyncio.sleep(5)

    def has_connect_perm(self, author, server):
        channel = author.voice.channel

        if channel:
            is_admin = channel.permissions_for(server.me).administrator
            if channel.user_limit == 0:
                is_full = False
            else:
                is_full = len(channel.members) >= channel.user_limit

        if channel is None:
            raise AuthorNotConnected
        elif channel.permissions_for(server.me).connect is False:
            raise UnauthorizedConnect
        elif channel.permissions_for(server.me).speak is False:
            raise UnauthorizedSpeak
        elif is_full and not is_admin:
            raise ChannelUserLimit
        else:
            return True
        return False

    async def queue_manager(self, sid):
        """This function assumes that there's something in the queue for us to
            play"""
        server = self.bot.get_guild(sid)
        max_length = await self.settings.MAX_LENGTH()

        # This is a reference, or should be at least
        temp_queue = self.queue[server.id][QueueKey.TEMP_QUEUE]
        queue = self.queue[server.id][QueueKey.QUEUE]
        repeat = self.queue[server.id][QueueKey.REPEAT]
        last_song = self.queue[server.id][QueueKey.NOW_PLAYING]
        last_song_channel = self.queue[server.id][QueueKey.NOW_PLAYING_CHANNEL]

        assert temp_queue is self.queue[server.id][QueueKey.TEMP_QUEUE]
        assert queue is self.queue[server.id][QueueKey.QUEUE]

        # _play handles creating the voice_client and player for us

        if not self.is_playing(server):
            print(
                "not playing anything on sid {}".format(server.id)
                + ", attempting to start a new song."
            )
            self.skip_votes[server.id] = []
            # Reset skip votes for each new song
            if len(temp_queue) > 0:
                # Fake queue for irdumb's temp playlist songs
                print("calling _play because temp_queue is non-empty")
                try:
                    queued_song = temp_queue.popleft()
                    url = queued_song.url
                    channel = queued_song.channel
                    song = await self._play(sid, url, channel)
                except MaximumLength:
                    return
            elif len(queue) > 0:  # We're in the normal queue
                queued_song = queue.popleft()
                url = queued_song.url
                channel = queued_song.channel
                print("calling _play on the normal queue")
                try:
                    song = await self._play(sid, url, channel)
                except MaximumLength:
                    return
                if repeat and last_song:
                    queued_last_song = QueuedSong(
                        last_song.webpage_url, last_song_channel
                    )
                    queue.append(last_song.webpage_url)
            else:
                song = None
            self._set_queue_nowplaying(server, song, channel)
            print("set now_playing for sid {}".format(server.id))
            self.bot.loop.create_task(self._update_bot_status())

        elif server.id in self.downloaders:
            # We're playing but we might be able to download a new song
            curr_dl = self.downloaders.get(server.id)
            if len(temp_queue) > 0:
                queued_next_song = temp_queue.peekleft()
                next_url = queued_next_song.url
                next_channel = queued_next_song.channel
                next_dl = Downloader(next_url, max_length)
            elif len(queue) > 0:
                queued_next_song = queue.peekleft()
                next_url = queued_next_song.url
                next_channel = queued_next_song.channel
                next_dl = Downloader(next_url, max_length)
            else:
                next_dl = None

            if next_dl is not None:
                try:
                    # Download next song
                    next_dl.start()
                    await self._download_next(server, curr_dl, next_dl)
                except YouTubeDlError as e:
                    if len(temp_queue) > 0:
                        temp_queue.popleft()
                    elif len(queue) > 0:
                        queue.popleft()
                    clean_url = self._clean_url(next_url)
                    message = (
                        "I'm unable to play '{}' because of an "
                        "error:\n'{}'".format(clean_url, str(e))
                    )
                    await self.bot.send_message(next_channel, message)

    async def queue_scheduler(self):
        while self == self.bot.get_cog("Audio"):
            tasks = []
            queue = self.queue #copy.deepcopy(self.queue)
            for sid in queue:
                if (
                    len(queue[sid][QueueKey.QUEUE]) == 0
                    and len(queue[sid][QueueKey.TEMP_QUEUE]) == 0
                ):
                    continue
                # print("scheduler found a non-empty queue"
                #           " for sid: {}".format(sid))
                tasks.append(self.bot.loop.create_task(self.queue_manager(sid)))
            completed = [t.done() for t in tasks]
            while not all(completed):
                completed = [t.done() for t in tasks]
                await asyncio.sleep(0.5)
            await asyncio.sleep(1)

    async def reload_monitor(self):
        while self == self.bot.get_cog("Audio"):
            await asyncio.sleep(0.5)

        for vc in self.bot.voice_clients:
            try:
                vc.audio_player.stop()
            except:
                pass


    def voice_client(self, server):
        return [x for x in self.bot.voice_clients if x.guild.id == server.id][0]

    def voice_connected(self, server):
        if server.voice_client:
            return True
        return False

    async def voice_state_update(self, member, before, after):
        server = member.guild
        # Member objects
        if after.channel != before.channel:
            try:
                self.skip_votes[server.id].remove(member.id)
            except (ValueError, KeyError):
                pass
                # Either the server ID or member ID already isn't in there
        if after is None:
            return
        if server.id not in self.queue:
            return
        if after != server.me:
            return

        # Member is the bot

        if before.channel != after.channel:
            self._set_queue_channel(server, after.channel)

        if before.mute != after.mute:
            vc = self.voice_client(server)
            if after.mute and vc.audio_player.is_playing():
                print("Just got muted, pausing")
                vc.audio_player.pause()
            elif not after.mute and (
                not vc.audio_player.is_playing() and not vc.audio_player.is_done()
            ):
                print("just got unmuted, resuming")
                vc.audio_player.resume()

    def __unload(self):
        for vc in self.bot.voice_clients:
            self.bot.loop.create_task(vc.disconnect())
