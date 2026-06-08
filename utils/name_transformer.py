import argparse
import json
import re
from pathlib import Path
from typing import Literal


class NameTransformer:
    """
    Loads a JSONL names file, applies variant-merging transformations,
    and exposes the result for saving or inspection.

    A single dataset (male *or* female) is handled per instance. To produce
    the final combined file with the nested record schema, use the
    ``build_combined()`` classmethod, which orchestrates both datasets.

    Parameters
    ----------
    filepath : str | Path
        Path to the input JSONL file.
    sex : {"male", "female"}
        Declares which dataset is being processed (stored as metadata and
        written into each record's ``description.sex``).
    """

    SEX = Literal["male", "female"]

    def __init__(self, filepath: str | Path, sex: SEX):
        if sex not in ("male", "female"):
            raise ValueError(f"sex must be 'male' or 'female', got {sex!r}")
        self.filepath = Path(filepath)
        self.sex = sex
        self.records: list[dict] = self._load(self.filepath)
        self._etymology_index: dict[str, dict] = {}
        self._etymology_index_norm: dict[str, dict] = {}
        self._base_name_index: dict[str, dict] = {}
        self._base_name_index_norm: dict[str, dict] = {}

    # -- I/O ------------------------------------------------------------------

    @staticmethod
    def _load(path: Path) -> list[dict]:
        """Read all JSON lines from *path* into a list of dicts."""
        records = []
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
        return records

    def load_base_name_source(
        self, source: "str | Path | NameTransformer"
    ) -> "NameTransformer":
        """
        Build the base-name etymology index from an external dataset.

        *source* can be:
          - a path (str / Path) to a JSONL file, or
          - an already-transformed NameTransformer instance (recommended so
            that post-transformation etymology is available).

        Must be called before transform(). Returns self for chaining.
        """
        records = source.records if isinstance(source, NameTransformer) else self._load(Path(source))
        self._base_name_index = {}
        self._base_name_index_norm = {}
        for rec in records:
            if not rec.get("etymology"):
                continue
            entry = {
                "etymology": rec["etymology"],
                "etymology_comment": rec.get("etymology_comment"),
            }
            # Index by primary name and by every official variant so that a
            # female base_name like 'АНТОНІЙ' resolves to АНТІН's etymology
            # even when 'АНТОНІЙ' only appears in АНТІН's official_vars.
            names_to_index = [rec.get("name", "").strip()] + list(rec.get("official_vars") or [])
            for name in names_to_index:
                if not name:
                    continue
                if name not in self._base_name_index:
                    self._base_name_index[name] = entry
                norm = self._normalise(name)
                if norm not in self._base_name_index_norm:
                    self._base_name_index_norm[norm] = entry
        return self

    def save(self, output_path: str | Path) -> None:
        """
        Write transformed (flat) records to a JSONL file.

        Kept for backwards compatibility / debugging of a single dataset.
        For the final combined deliverable use ``build_combined()`` instead.
        """
        output_path = Path(output_path)
        with output_path.open("w", encoding="utf-8") as fh:
            for rec in self.records:
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        print(f"[{self.sex}] Saved {len(self.records)} records -> {output_path}")

    # -- helpers --------------------------------------------------------------

    @staticmethod
    def _parse_name_list(value: str | None) -> list[str]:
        """Split a comma/semicolon-delimited name string into a list."""
        if not isinstance(value, str) or not value.strip():
            return []
        return [p.strip() for p in re.split(r"[,;]+", value) if p.strip()]

    @staticmethod
    def _append_unique(lst: list[str], *values: str) -> list[str]:
        """Append values to lst, ignoring entries already present."""
        for v in values:
            v = v.strip()
            if v and v not in lst:
                lst.append(v)
        return lst

    def _build_etymology_index(self) -> None:
        """
        Index records that carry etymology data, keyed by name.
        Two parallel dicts are maintained:
          _etymology_index      — exact name key
          _etymology_index_norm — і→и normalised key (fallback for orthographic
                                  variants where the same vowel is spelled
                                  differently across records)
        """
        self._etymology_index: dict[str, dict] = {}
        self._etymology_index_norm: dict[str, dict] = {}
        for rec in self.records:
            name = rec.get("name", "")
            if rec.get("etymology") and name not in self._etymology_index:
                entry = {
                    "etymology": rec["etymology"],
                    "etymology_comment": rec.get("etymology_comment"),
                }
                self._etymology_index[name] = entry
                norm = self._normalise(name)
                if norm not in self._etymology_index_norm:
                    self._etymology_index_norm[norm] = entry

    @staticmethod
    def _normalise(name: str) -> str:
        """
        Return a normalised key for fuzzy index lookups.
        Ukrainian і (U+0456) and и (U+0438) represent the same sound and are
        used interchangeably in many borrowed names across the source data.
        Collapsing both to и gives a stable key so 'АГРИПІНА' matches the
        record named 'АГРИПИНА', etc.
        """
        return name.replace("і", "и").replace("І", "И")

    def _etym_lookup(self, name: str) -> "dict | None":
        """Exact lookup in _etymology_index, with normalised fallback."""
        return (
            self._etymology_index.get(name)
            or self._etymology_index_norm.get(self._normalise(name))
        )

    def _lookup_etymology(self, name: str) -> "dict | None":
        """
        Look up etymology for *name* in the base-name index.
        base_name fields can contain multiple comma/semicolon-separated names
        (e.g. 'АНТІН, АНТОН'), so each candidate is tried in order.
        Both exact and і/и-normalised keys are tried for each candidate.
        """
        for candidate in re.split(r"[,;]+", name):
            candidate = candidate.strip()
            result = (
                self._base_name_index.get(candidate)
                or self._base_name_index_norm.get(self._normalise(candidate))
            )
            if result:
                return result
        return None

    # -- transformation steps -------------------------------------------------

    def _parse_list_columns(self) -> None:
        """
        Convert official_vars and unofficial_vars strings -> deduplicated lists
        in-place.  Raw strings are split on commas/semicolons and then fed
        through _append_unique so any duplicate tokens in the source are
        silently dropped (e.g. АМБРОСІЙ's unofficial_vars had 'АМБРОС' twice).
        """
        for rec in self.records:
            for field in ("official_vars", "unofficial_vars"):
                deduped: list[str] = []
                for token in self._parse_name_list(rec.get(field)):
                    self._append_unique(deduped, token)
                rec[field] = deduped

    def _merge_equivalent_name(self) -> None:
        """
        For every record that has a non-empty equivalent_name:
          - split it (field may contain several names, e.g. 'ЗОТ; ЗОТИК')
            and append each token to official_vars
          - additionally pull in *every* official variant listed in the
            referenced entry's own dictionary article. So САЛОМЕЯ, whose
            equivalent_name is СОЛОМІЯ, inherits not just 'СОЛОМІЯ' but also
            СОЛОМІЯ's official_vars (e.g. 'СОЛОХА'). The record's own name is
            stripped back out later in _remove_self_references().
          - inherit etymology / etymology_comment if the record lacks them,
            trying each token in order until a source is found

        The referenced entry's official_vars are read from a snapshot taken
        *before* any equivalent-merging mutates them, so what gets pulled is
        that entry's own listing (already including its half_official_vars,
        because _merge_half_official_vars() runs first) rather than a
        partially-merged state. Both exact and і/и-normalised name keys are
        tried. The key is removed from all records in _cleanup_merged_keys().
        """
        # Snapshot name -> official_vars before mutation (with і/и fallback).
        vars_by_name: dict[str, list[str]] = {}
        vars_by_name_norm: dict[str, list[str]] = {}
        for rec in self.records:
            nm = (rec.get("name") or "").strip()
            if not nm:
                continue
            snapshot = list(rec.get("official_vars", []))
            vars_by_name.setdefault(nm, snapshot)
            vars_by_name_norm.setdefault(self._normalise(nm), snapshot)

        for rec in self.records:
            eq_raw = rec.get("equivalent_name")
            if not isinstance(eq_raw, str) or not eq_raw.strip():
                continue

            eq_names = self._parse_name_list(eq_raw)
            for eq in eq_names:
                self._append_unique(rec["official_vars"], eq)
                ref_vars = (
                    vars_by_name.get(eq)
                    or vars_by_name_norm.get(self._normalise(eq))
                )
                if ref_vars:
                    self._append_unique(rec["official_vars"], *ref_vars)

            if not rec.get("etymology"):
                for eq in eq_names:
                    src = self._etym_lookup(eq)
                    if src:
                        rec["etymology"] = src["etymology"]
                        if src.get("etymology_comment"):
                            rec["etymology_comment"] = src["etymology_comment"]
                        break

    def _merge_half_official_vars(self) -> None:
        """
        Append non-empty half_official_vars entries into official_vars.
        The key is removed from all records in _cleanup_merged_keys().
        """
        for rec in self.records:
            half_raw = rec.get("half_official_vars")
            if not isinstance(half_raw, str) or not half_raw.strip():
                continue

            for entry in self._parse_name_list(half_raw):
                self._append_unique(rec["official_vars"], entry)

    def _cleanup_merged_keys(self) -> None:
        """
        Remove equivalent_name and half_official_vars from every record,
        regardless of whether they held a value or null.
        """
        for rec in self.records:
            rec.pop("equivalent_name", None)
            rec.pop("half_official_vars", None)

    def _inherit_from_base_name(self) -> None:
        """
        Female only. For records that have a base_name but no etymology,
        copy etymology and etymology_comment from the base-name source index.
        Skipped silently if load_base_name_source() was not called.
        """
        if not self._base_name_index:
            return

        for rec in self.records:
            base = rec.get("base_name")
            if not isinstance(base, str) or not base.strip():
                continue
            if rec.get("etymology"):
                continue

            src = self._lookup_etymology(base.strip())
            if src:
                rec["etymology"] = src["etymology"]
                if src.get("etymology_comment"):
                    rec["etymology_comment"] = src["etymology_comment"]

    def _inherit_from_official_vars(self) -> None:
        """
        For records that still lack etymology or etymology_comment, scan
        official_vars left-to-right and copy the first value found for each
        missing field.  Both fields are handled independently:

        - No etymology at all → take etymology (and etymology_comment if
          the source has one) from the first official variant that has it.
        - Has etymology but no etymology_comment → take etymology_comment
          from the first official variant that carries one, without touching
          the existing etymology.

        Relies on _etymology_index being fully up-to-date; call
        _build_etymology_index() immediately before this method.
        """
        for rec in self.records:
            needs_etymology = not rec.get("etymology")
            needs_comment   = not rec.get("etymology_comment")

            if not needs_etymology and not needs_comment:
                continue

            for var_name in rec.get("official_vars", []):
                src = self._etym_lookup(var_name)
                if not src:
                    continue

                if needs_etymology and src.get("etymology"):
                    rec["etymology"] = src["etymology"]
                    needs_etymology = False
                    # also grab the comment from the same source if still needed
                    if needs_comment and src.get("etymology_comment"):
                        rec["etymology_comment"] = src["etymology_comment"]
                        needs_comment = False

                elif needs_comment and src.get("etymology_comment"):
                    rec["etymology_comment"] = src["etymology_comment"]
                    needs_comment = False

                if not needs_etymology and not needs_comment:
                    break

    def _remove_self_references(self) -> None:
        """
        Remove a record's own name from its official_vars list.
        This can happen when equivalent_name or half_official_vars in the
        source data erroneously echoes the record's canonical name
        (e.g. ОРИНА had 'ОРИНА' in its official_vars after merging).
        """
        for rec in self.records:
            name = rec.get("name", "")
            rec["official_vars"] = [v for v in rec.get("official_vars", []) if v != name]

    def _deduplicate_records(self) -> None:
        """
        Remove exact duplicate records — records where every field except
        entry_id is identical.  Legitimate homonyms (same name, different
        etymology) are preserved.  True duplicates arise when the same source
        entry was parsed more than once (e.g. ФЕОДОСІЯ, ЄВПРАКСІЯ).
        """
        seen: set[tuple] = set()
        unique: list[dict] = []
        for rec in self.records:
            key = tuple(
                sorted(
                    (k, json.dumps(v, ensure_ascii=False, sort_keys=True))
                    for k, v in rec.items()
                    if k != "entry_id"
                )
            )
            if key not in seen:
                seen.add(key)
                unique.append(rec)
        self.records = unique

    def _reset_ids(self) -> None:
        """Reassign entry_id sequentially (1-based) across all records."""
        for new_id, rec in enumerate(self.records, start=1):
            rec["entry_id"] = new_id

    # -- nested schema --------------------------------------------------------

    @staticmethod
    def _titlecase(name: str) -> str:
        """
        Capitalise only the first letter, lower-casing the rest.

        Equivalent to str.capitalize() but applied explicitly so the intent is
        clear: 'ОЛЕКСАНДРА' -> 'Олександра'. Crucially this does NOT break on
        apostrophes the way str.title() does, so Ukrainian names keep a single
        capital: "АВЕР'ЯН" -> "Авер'ян", 'ДЕМ’ЯН' -> 'Дем’ян' (both straight '
        and curly ’ apostrophes occur in the source).
        """
        name = name.strip()
        if not name:
            return name
        return name[:1].upper() + name[1:].lower()

    @classmethod
    def _titlecase_field(cls, value: str) -> str:
        """
        Title-case a possibly multi-name field. base_name entries may hold
        several comma/semicolon-separated names (e.g. 'МАР’ЯН, МАРІАН'); each
        part is cased independently and rejoined with ', '.
        """
        parts = [p.strip() for p in re.split(r"[,;]+", value) if p.strip()]
        return ", ".join(cls._titlecase(p) for p in parts)

    @classmethod
    def _to_nested(cls, rec: dict, sex: str) -> dict:
        """
        Re-pack a single flat transformed record into the final nested schema:

            {
              "entry_id": int,
              "name": str,
              "description":  { sex, base_name, etymology, etymology_comment },
              "variant_info": { official_vars, unofficial_vars }
            }

        All name fields (name, base_name, official_vars, unofficial_vars) are
        title-cased so only the first letter is capital. Etymology fields are
        left as-is. Missing scalar fields default to "" and missing lists
        default to [].
        """
        return {
            "entry_id": rec.get("entry_id"),
            "name": cls._titlecase(rec.get("name", "")),
            "description": {
                "sex": sex,
                "base_name": cls._titlecase_field(rec.get("base_name") or ""),
                "etymology": rec.get("etymology") or "",
                "etymology_comment": rec.get("etymology_comment") or "",
            },
            "variant_info": {
                "official_vars": [cls._titlecase(v) for v in (rec.get("official_vars") or [])],
                "unofficial_vars": [cls._titlecase(v) for v in (rec.get("unofficial_vars") or [])],
            },
        }

    def to_nested_records(self) -> list[dict]:
        """Return this dataset's records in the nested output schema."""
        return [self._to_nested(rec, self.sex) for rec in self.records]

    # -- public API -----------------------------------------------------------

    def transform(self) -> "NameTransformer":
        """Run all transformation steps and return self for chaining."""
        self._parse_list_columns()
        self._inherit_from_base_name()
        self._build_etymology_index()
        self._merge_half_official_vars()   # before equivalent merge, so a
                                           # referenced entry's half vars are
                                           # already in its official_vars when
                                           # _merge_equivalent_name pulls them
        self._merge_equivalent_name()
        self._cleanup_merged_keys()
        self._remove_self_references()
        self._deduplicate_records()
        self._build_etymology_index()
        self._inherit_from_official_vars()
        self._reset_ids()
        return self

    @classmethod
    def build_combined(
        cls,
        male_filepath: str | Path,
        female_filepath: str | Path,
        output_path: str | Path,
    ) -> list[dict]:
        """
        Process both datasets and write a single combined JSONL file using the
        nested record schema.

        The male dataset is transformed first so that its post-transformation
        etymology becomes the base-name source for the female dataset (this is
        what load_base_name_source() recommends). The two transformed datasets
        are then concatenated (male first, female second), re-packed into the
        nested schema, and given fresh sequential entry_id values across the
        whole combined set.

        Returns the list of nested records that was written.
        """
        male = cls(male_filepath, "male").transform()

        female = cls(female_filepath, "female")
        female.load_base_name_source(male)   # use transformed male as source
        female.transform()

        nested = male.to_nested_records() + female.to_nested_records()
        for new_id, rec in enumerate(nested, start=1):
            rec["entry_id"] = new_id

        output_path = Path(output_path)
        with output_path.open("w", encoding="utf-8") as fh:
            for rec in nested:
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

        print(
            f"Saved {len(nested)} records "
            f"({len(male.records)} male + {len(female.records)} female) "
            f"-> {output_path}"
        )
        return nested