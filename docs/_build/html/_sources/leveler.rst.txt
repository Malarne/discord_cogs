==========
Leveler
==========

This is the guide for ``Leveler`` cog.
Be sure to have the latest version of the cog first, using ``[p]cog update`` before reading this.
``[p]`` being your bot's prefix

------------
Installation
------------

To install the cog, first load the downloader cog, included
in core Red.::

    [p]load downloader

Then you will need to install my repository::

    [p]repo add Malarne https://github.com/Malarne/discord_cogs

Finally, you can install the cog::

    [p]cog install Malarne Leveler

.. warning:: The cog is not loaded by default.
    To load it, type this::

        [p]load Leveler

-----
Configuration commands
-----

First of all, the channel whitelist is enabled by default.
Check out the config commands to set up your cog correctly.

*   ``[p]levelerset``
   This is the basic configuration command.

   *   ``[p]levelerset announce <status>``
      **<status>**: expects a boolean
      That means you can turn on levelup announce with ``[p]levelerset announce True``
      and disable them using ``[p]levelerset announce False``
      Default to False

   *   ``[p]levelerset autoregister``
      This will simply switch the autoregister on or off.
      Default turned off.
      This will simply allow your users to gain xp without having to use ``[p]register`` first.

   *   ``[p]levelerset channel``
      This is the basic channel configuration command.

      *   ``[p]levelerset channel whitelist``
         This will allow you to manage your channel whitelist.
         Any whitelisted channel will allow users sending messages to that channel to earn experience.
         Note that it is toggled on by default, and will not work if you toggle it off.

          *   ``[p]levelerset channel whitelist add <channel>``
             This will add the given channel to your server whitelist.

          *   ``[p]levelerset channel whitelist remove <channel>``
             This will remove the given channel from your server whitelist.

          *   ``[p]levelerset channel whitelist show``
             This will show you the whitelisted channels of your server.

          *   ``[p]levelerset channel whitelist toggle``
             This will toggle on or off the channel whitelist for your server.
             Default on

      *   ``[p]levelerset channel blacklist``
         This will allow you to manage your channel blacklist.
         Any blacklisted channel will not allow users sending messages to that channel to earn experience.
         Note that it is toggled off by default, and will not work if you toggle it off.

          *   ``[p]levelerset channel blacklist add <channel>``
             This will add the given channel to your server blacklist.

          *   ``[p]levelerset channel blacklist remove <channel>``
             This will remove the given channel from your server blacklist.

          *   ``[p]levelerset channel blacklist show``
             This will show you the blacklisted channels of your server.

          *   ``[p]levelerset channel blacklist toggle``
             This will toggle on or off the channel blacklist for your server.
             Default off

   *   ``[p]levelerset cooldown <cooldown>``
      Allow you to set a cooldown between an user xp gain.
      <cooldown> expects an int, put in there a cooldown in seconds
      Default to 60 seconds
      Set to 0 to disable

   *   ``[p]levelerset defaultbackground <url>``
      Allow you to put a default custom background to your guild members' profiles.
      <url> must be a direct link to your image to work.

   *   ``[p]levelerset roles``
      Basic configuration command for role given by the leveler.

       *   ``[p]levelerset roles add <level> <role>``
          <level>: int. This will be the level <role> will be given.
          <role>: The role that will be given.
          Just note that the bot should have an higher role than the role you want it to give,
          otherwise it won't be able to give it to any user.

       *   ``[p]levelerset roles remove <role>``
          This will remove <role> from being given by the leveler.

       *   ``[p]levelerset roles show``
          This will show you the configurated channels for your server.

       *   ``[p]levelerset roles defaultrole <name>``
          <name> will be the new name for the default role of users
          "New" by default

   *   ``[p]levelerset setlevel <level> <user>``
      This will set <user>'s level to <level>
      Note that setting level to higher than 1000 can throw errors

   *   ``[p]levelerset setxp <xp> <user>``
      This will set <user>'s xp to <xp>
      Note that settting xp to a really high value can throw errors.


-----
Usage
-----

*   ``[p]profileset``
   Profile customization base command.

   *   ``[p]profileset background <url>``
      Allow you to change your profile background to the image you want.
      Just note that it only accepts url for security reasons.

   *   ``[p]profileset description <description>``
      Allow you to add a description to your profile.

*   ``[p]register``
   Allow user to start gaining xp.
   Note that it's not needed if you turned on autoregister setting.

*   ``[p]profile [user]``
   Show your or user (if provided)'s profile.

*   ``[p]toplevel``
   Show the 9 highest members of your server and how many messages they sent today !