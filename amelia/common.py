import typing

class FlightRule(typing.NamedTuple):
    emoji: str
    name: str

    @classmethod
    def create(self, rule: str):
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


