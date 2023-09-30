from src.concepts.guild.data import GuildDataContext
from src.features.autorole.data import AutoRoleDataContext
from src.features.forum_channels.data import ForumChannelDataContext
from src.data import BaseUOW
from src.features.weather.data import WeatherDataContext


class UOW(BaseUOW):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.guilds = GuildDataContext(self.session)
        self.auto_roles = AutoRoleDataContext(self.session)
        self.forum_channels = ForumChannelDataContext(self.session)
        self.weather = WeatherDataContext(self.session)

