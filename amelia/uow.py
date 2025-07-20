from .concepts.guild.data import GuildDataContext
from .features.autorole.data import AutoRoleDataContext
from .features.forum_channels.data import ForumChannelDataContext
from .data import BaseUOW
from .features.weather.data import WeatherDataContext


class UOW(BaseUOW):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.guilds = GuildDataContext(self.session)
        self.auto_roles = AutoRoleDataContext(self.session)
        self.forum_channels = ForumChannelDataContext(self.session)
        self.weather = WeatherDataContext(self.session)

