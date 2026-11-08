"""Append-only SHA-256 hash chain behind the record-verified badge.

Each settled transcript segment and each amendment is appended as an entry
`{index, payload, prevHash, hash}`, where `hash` is the SHA-256 of the canonical JSON of
`{index, payload, prevHash}`. Verification recomputes the whole chain and reports the first
broken index. `HashChain.tamper` is the hidden demo control: it rewrites one stored entry
without rehashing, so the next verification shows the break.

This module is pure: no I/O, no clock, and no dependency on the rest of the server.

@implements IDR-003: SHA-256 hash chain for the record-verified badge
@see openspec/tdr/idr/idr-003-hash-chain-integrity.md
"""

import copy
import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from typing import Any

# prevHash of the first entry: there is nothing before it to link to.
GENESIS_HASH = "0" * 64
# Head hash of an empty chain, matching the empty-visit record.integrity payload.
EMPTY_HEAD = ""

_UNSET: Any = object()


def canonical_json(value: Any) -> bytes:
    """Stable UTF-8 JSON: sorted keys, no whitespace, non-ASCII text kept as itself.

    Rejects NaN and infinity, which have no JSON form, and anything else JSON cannot encode.
    Strings are hashed exactly as given; callers wanting Unicode normalisation apply it first.
    """
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def entry_hash(index: int, payload: Any, prev_hash: str) -> str:
    """SHA-256 hex digest of the canonical JSON of index, payload, and prevHash."""
    return hashlib.sha256(canonical_json({"index": index, "payload": payload, "prevHash": prev_hash})).hexdigest()


@dataclass(frozen=True)
class Entry:
    """One link in the chain."""

    index: int
    payload: Any
    prev_hash: str
    hash: str

    def wire(self) -> dict:
        """The entry in IDR-003's camelCase shape, with a copy of the payload."""
        return {
            "index": self.index,
            "payload": copy.deepcopy(self.payload),
            "prevHash": self.prev_hash,
            "hash": self.hash,
        }

    @classmethod
    def from_wire(cls, data: Mapping[str, Any]) -> "Entry":
        return cls(index=data["index"], payload=data["payload"], prev_hash=data["prevHash"], hash=data["hash"])


@dataclass(frozen=True)
class Verification:
    """Outcome of recomputing a chain.

    `head_hash` is the stored hash of the last entry (EMPTY_HEAD for an empty chain), so a
    broken chain still reports what it claims its head to be. `broken_at` is the index of the
    first entry that fails, or None when every entry checks out.
    """

    head_hash: str
    broken_at: int | None = None

    @property
    def ok(self) -> bool:
        return self.broken_at is None

    @property
    def status(self) -> str:
        """`verified` or `broken`, as record.integrity carries it (CDR-001)."""
        return "verified" if self.ok else "broken"


def verify(entries: Sequence[Entry]) -> Verification:
    """Recompute every link and report the first entry that does not check out.

    Entry i is broken when its index is not i, its prevHash is not the hash of entry i - 1
    (GENESIS_HASH for the first), or its stored hash differs from the recomputed one. A change
    to any field, a removed entry, or reordered entries is therefore caught at the first entry
    it affects.
    """
    head = entries[-1].hash if entries else EMPTY_HEAD
    expected_prev = GENESIS_HASH
    for position, entry in enumerate(entries):
        try:
            recomputed = entry_hash(entry.index, entry.payload, entry.prev_hash)
        except (TypeError, ValueError):
            return Verification(head_hash=head, broken_at=position)
        if entry.index != position or entry.prev_hash != expected_prev or entry.hash != recomputed:
            return Verification(head_hash=head, broken_at=position)
        expected_prev = entry.hash
    return Verification(head_hash=head)


class HashChain:
    """An append-only chain of JSON payloads for one visit record."""

    def __init__(self) -> None:
        self._entries: list[Entry] = []

    def __len__(self) -> int:
        return len(self._entries)

    @property
    def entries(self) -> tuple[Entry, ...]:
        """The stored entries, oldest first. Read them; tamper only through `tamper`."""
        return tuple(self._entries)

    @property
    def head_hash(self) -> str:
        """Stored hash of the newest entry, or EMPTY_HEAD when the chain is empty."""
        return self._entries[-1].hash if self._entries else EMPTY_HEAD

    def append(self, payload: Any) -> Entry:
        """Link a JSON-serialisable payload onto the head and return the new entry.

        The chain keeps its own copy, round-tripped through canonical JSON, so later changes
        to the caller's object never alter the record and what is stored is exactly what was
        hashed. Raises TypeError or ValueError for a payload JSON cannot encode.
        """
        stored = json.loads(canonical_json(payload))
        index = len(self._entries)
        prev_hash = self.head_hash or GENESIS_HASH
        entry = Entry(index=index, payload=stored, prev_hash=prev_hash, hash=entry_hash(index, stored, prev_hash))
        self._entries.append(entry)
        return entry

    def verify(self) -> Verification:
        return verify(self._entries)

    def tamper(
        self,
        index: int,
        *,
        payload: Any = _UNSET,
        prev_hash: str = _UNSET,
        hash: str = _UNSET,
    ) -> Entry:
        """Hidden demo control: overwrite fields of one stored entry without rehashing.

        Exists only to show detection on stage; nothing in the normal visit flow calls it.
        Returns the altered entry. Raises IndexError for an index the chain does not hold and
        ValueError when no field is given.
        """
        if not 0 <= index < len(self._entries):
            raise IndexError(f"no entry at index {index}")
        changes: dict[str, Any] = {}
        if payload is not _UNSET:
            changes["payload"] = copy.deepcopy(payload)
        if prev_hash is not _UNSET:
            changes["prev_hash"] = prev_hash
        if hash is not _UNSET:
            changes["hash"] = hash
        if not changes:
            raise ValueError("tamper needs a payload, prev_hash, or hash to change")
        altered = replace(self._entries[index], **changes)
        self._entries[index] = altered
        return altered

    def wire(self) -> list[dict]:
        """Every entry in IDR-003's camelCase shape, oldest first."""
        return [entry.wire() for entry in self._entries]

    @classmethod
    def from_wire(cls, data: Sequence[Mapping[str, Any]]) -> "HashChain":
        """Rebuild a chain from its wire form as is; call `verify` to check it."""
        chain = cls()
        chain._entries = [Entry.from_wire(item) for item in data]
        return chain
