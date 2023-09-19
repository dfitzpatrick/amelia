from src.concepts.guild.data import GuildDataContext
from src.features.autorole.data import AutoRoleDataContext
from src.data import BaseUOW


class UOW(BaseUOW):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.guilds = GuildDataContext(self.session)
        self.auto_roles = AutoRoleDataContext(self.session)
    def foo(self):
        return "bar"

