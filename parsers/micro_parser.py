import re
from pathlib import Path

from utils import file_manager, custom_logger


class MicroParser:
    def __init__(self) -> None:
        self.__logger = custom_logger.get_logger("Micro Parser")
        self.__fm = file_manager.FileManager()


    def parse_entry(
        self,
        entry: str,
        pattern: re.Pattern | str,
    ) -> dict | None:
        """
        Try to match *entry* against a single *pattern* using fullmatch.

        Returns:
            A dict of named groups on success, or None on no-match / error.
        """
        try:
            match = re.fullmatch(pattern, entry)
        except Exception as e:
            self.__logger.error(f"Error occurred while matching pattern: {e}")
            return None

        if match:
            return match.groupdict()

        self.__logger.debug(f"Entry did not match the pattern: {entry}")
        return None

    def parse_entry_multi(
        self,
        entry: str,
        patterns: dict[str, re.Pattern],
    ) -> tuple[str, dict] | None:
        """
        Try each pattern in *patterns* (insertion order = priority order).

        Returns:
            (pattern_key, groupdict) for the first matching pattern,
            or None if nothing matched.
        """
        for key, pattern in patterns.items():
            result = self.parse_entry(entry, pattern)
            if result is not None:
                return key, result

        self.__logger.debug(f"No pattern matched entry: {entry}")
        return None


    def parse_dict_entries(
        self,
        entries_path: Path,
        output_path: Path,
        pattern: re.Pattern,
        name: str,
    ) -> None:
        """
        Parse a JSONL file with a **single** pattern.

        Each line in *entries_path* must be a JSON object with at least
        the keys ``"id"`` and ``"entry"``.  Matched records are written to
        *output_path / name*.
        """
        entries = self.__fm.jsonl2dict(entries_path)
        total_entries = len(entries)
        self.__logger.info(f"Total entries to parse: {total_entries}")

        parsed_entries: list[dict] = []
        for entry_data in entries:
            entry = entry_data["entry"]
            result = self.parse_entry(entry, pattern)
            if result:
                entry_dict = {"entry_id": entry_data["id"]}
                entry_dict.update(result)
                parsed_entries.append(entry_dict)

        if not parsed_entries:
            self.__logger.warning(
                f"No entries were parsed successfully from {entries_path}. "
                "The output file will be empty."
            )
            self.__fm.dict2jsonl([{}], output_path, name=name)
        else:
            self.__fm.dict2jsonl(parsed_entries, output_path, name=name)
            self.__logger.info(
                f"Successfully parsed {len(parsed_entries)} out of {total_entries} "
                f"entries from {entries_path}. Output saved to {output_path / name}."
            )

    def parse_dict_entries_multi(
        self,
        entries_path: Path,
        output_path: Path,
        patterns: dict[str, re.Pattern],
        name: str,
    ) -> None:
        """
        Parse a JSONL file against an **ordered dict of patterns**.

        Each entry is tried against every pattern in insertion order;
        the first match wins.  The matched pattern key is stored in the
        ``"pattern"`` field of every output record so you can filter /
        group results downstream.

        Unmatched entries are written to a separate file
        ``"unmatched_{name}"`` in *output_path* for pattern-iteration
        diagnostics.

        Args:
            entries_path:  Path to the source ``.jsonl`` file.
            output_path:   Directory where output files are written.
            patterns:      Ordered ``{key: compiled_pattern}`` dict.
                           Insertion order determines priority —
                           more-specific patterns must come first
                           (mirrors ``ENTRY_PATTERNS`` ordering).
            name:          Filename for the successfully parsed output.
        """
        entries = self.__fm.jsonl2dict(entries_path)
        total = len(entries)
        self.__logger.info(f"Total entries to parse: {total}")

        parsed: list[dict] = []
        unmatched: list[dict] = []
        pattern_counts: dict[str, int] = {}

        for entry_data in entries:
            entry = entry_data["entry"]
            match = self.parse_entry_multi(entry, patterns)

            if match is not None:
                key, groups = match
                parsed.append({"entry_id": entry_data["id"], **groups})
                pattern_counts[key] = pattern_counts.get(key, 0) + 1
            else:
                unmatched.append(entry_data)

        if parsed:
            self.__fm.dict2jsonl(parsed, output_path, name=name)
            self.__logger.info(
                f"Parsed {len(parsed)}/{total} entries → {output_path / name}"
            )
            self.__logger.info(f"Pattern breakdown: {pattern_counts}")
        else:
            self.__logger.warning(
                f"No entries matched any pattern from {entries_path}. "
                "The output file will be empty."
            )
            self.__fm.dict2jsonl([{}], output_path, name=name)

        if unmatched:
            unmatched_name = f"unmatched_{name}"
            self.__fm.dict2jsonl(unmatched, output_path, name=unmatched_name)
            self.__logger.warning(
                f"{len(unmatched)} unmatched entries saved to "
                f"{output_path / unmatched_name}."
            )