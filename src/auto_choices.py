from dataclasses import dataclass
from typing import Optional, Callable, List, Tuple, Dict, Coroutine, Any, Awaitable

from discord import app_commands
from fuzzywuzzy import fuzz, process


@dataclass()
class AutoCompleteItem:
    param_value: str
    choices_cache: List[app_commands.Choice]


def fuzzy_ratio(text: str, names: Tuple[str, ...]):
    return process.extract(text, names, scorer=fuzz.partial_ratio)


def fuzzy_best(text: str, items: List[str], threshold: int) -> List[str]:
    ratios = fuzzy_ratio(text, tuple(items))
    highest_ratio = ratios[0][1]
    if text == '':
        # No threshold
        return items[:24]
    return [r[0] for r in ratios if highest_ratio - r[1] < threshold]


class FuzzyChoicesCache:

    def __init__(self, fetch_method: Callable[[], Awaitable[list[str]]], threshold: int = 7):
        self.fetch_method = fetch_method
        self.threshold = threshold
        self.cache: List[str] = []

    async def refresh(self):
        self.cache = await self.fetch_method()

    async def retrieve(self, fuzzy_string: str) -> List[app_commands.Choice]:
        if not self.cache:
            self.cache = await self.fetch_method()
        best_matches = fuzzy_best(fuzzy_string, self.cache, self.threshold)
        return [app_commands.Choice(name=c, value=c) for c in self.cache if c in best_matches]


class DependentFuzzyChoicesCache:

    def __init__(
            self, 
            fetch_method: Callable[[Any], Coroutine[None, Any, AutoCompleteItem]], 
            sanitizer: Optional[Callable[[str], str]] = None, 
            threshold: int = 7
    ):
        self.fetch_method = fetch_method
        self.threshold = threshold
        self.sanitizer = sanitizer or (lambda s: s)
        self.cache: Dict[int, AutoCompleteItem] = {}

    async def retrieve(self, key: int, param_value: str, fuzzy_string: str) -> List[app_commands.Choice]:
        cache = self.cache.get(key)
        value_is_different = cache and cache.param_value != param_value
        if cache is None or value_is_different:
            self.cache[key] = cache = await self.fetch_method(param_value)
        best_matches = fuzzy_best(fuzzy_string, [c.name for c in cache.choices_cache], self.threshold)
        return [c for c in cache.choices_cache if c.name in best_matches]



