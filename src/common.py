import typing
from datetime import datetime, timedelta
import dateutil.parser
import discord

TFL_URL = 'http://api.theflying.life'
APP_COMMANDS_GUILDS = (
   discord.Object(id=1020393929746685973),
)

class FlightRule(typing.NamedTuple):
    emoji: str
    name: str

    @classmethod
    def create(cls, rule: str):
        """
        Returns a Named Tuple based on the flight rules. Right now this
        tuple just contains an emoji and the name, but could be expanded later.

        Parameters
        ----------
        rule

        Returns
        -------
        FlightRule -> Tuple[str, str]
        """
        formats = {
            "VFR": FlightRule(":green_circle:", "VFR"),
            "IFR": FlightRule(":red_circle:", "IFR"),
            "MVFR": FlightRule(":blue_circle:", "MVFR"),
            "LIFR": FlightRule(":purple_circle:", "LIFR")

        }
        return formats.get(rule.upper(), FlightRule(":black_circle:", rule))

class AvwxTime(typing.NamedTuple):
    is_24: bool
    text: str
    original_dt: datetime
    adjusted_dt: datetime

    @classmethod
    def create(cls, time_object: typing.Dict[str, typing.Any]):
        """
        Avwx support for 24 hour Zulu times for reporting.
        Parameters
        ----------
        time_object: The dictionary for any time object in Avwx

        Returns
        -------

        """
        repr = time_object['repr']
        dt = dateutil.parser.parse(time_object['dt'])
        hour = repr[-2:]
        is_24 = hour == "24"
        adj = dt
        text = dt.strftime("%b %d %H:%M")
        if is_24:
            # The AVWX api always reports the same day, so make it the next
            adj += timedelta(days=1)
            text = "{} 24:00".format(dt.strftime("%b %d"))
        return AvwxTime(is_24, text, dt, adj)


def td_format(td_object):
    """
    Taken from https://stackoverflow.com/questions/538666/format-timedelta-to-string
    Just make it more human readable
    Parameters
    ----------
    td_object

    Returns
    -------

    """
    seconds = int(td_object.total_seconds())
    periods = [
        ('year',        60*60*24*365),
        ('month',       60*60*24*30),
        ('day',         60*60*24),
        ('hour',        60*60),
        ('minute',      60),
        ('second',      1)
    ]

    strings=[]
    for period_name, period_seconds in periods:
        if seconds > period_seconds:
            period_value , seconds = divmod(seconds, period_seconds)
            has_s = 's' if period_value > 1 else ''
            strings.append("%s %s%s" % (period_value, period_name, has_s))

    return ", ".join(strings)

def get_member_avatar_url(member: discord.Member) -> str:
    base = "https://cdn.discordapp.com/"
    id = member.id

    return f"{base}/avatars/{id}/user_avatar.png"

