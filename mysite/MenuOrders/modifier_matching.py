import re

from rapidfuzz import fuzz, process


def option_names(option):
    return [option.name, *(alias.alias for alias in option.aliases.all())]


def _normalize(text):
    return " ".join(re.findall(r"\w+", (text or "").casefold()))


def _unique_option(pairs):
    options = {option.pk: option for option, _ in pairs}
    return next(iter(options.values())) if len(options) == 1 else None


def match_modifier_option(options, text, *, in_query=False, fuzzy_threshold=None):
    """Resolve active options by canonical name or alias within the supplied scope.

    Exact canonical names take precedence over aliases. In a spoken query,
    match whole phrases, preferring the longest; tied options stay unresolved.
    """
    text = _normalize(text)
    options = [option for option in options if option.active]
    if not text:
        return None

    exact = [(option, text) for option in options if _normalize(option.name) == text]
    if exact:
        return _unique_option(exact)

    pairs = [
        (option, name)
        for option in options
        for raw_name in option_names(option)
        if (name := _normalize(raw_name))
    ]
    exact = [(option, name) for option, name in pairs if name == text]
    if exact:
        return _unique_option(exact)

    if in_query:
        matches = [(option, name) for option, name in pairs if f" {name} " in f" {text} "]
        if matches:
            longest = max(len(name) for _, name in matches)
            return _unique_option([(option, name) for option, name in matches if len(name) == longest])

    if fuzzy_threshold is None:
        return None
    if in_query:
        scored = [
            (option, max((fuzz.ratio(token, name) for token in text.split()), default=0))
            for option, name in pairs if " " not in name
        ]
    else:
        scored = [
            (pairs[index][0], score)
            for _, score, index in process.extract(text, [name for _, name in pairs], scorer=fuzz.WRatio, limit=None)
        ]
    best_score = max((score for _, score in scored), default=0)
    if best_score < fuzzy_threshold:
        return None
    return _unique_option([(option, score) for option, score in scored if score == best_score])
