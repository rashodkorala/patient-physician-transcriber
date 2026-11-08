"""Tests for the record hash chain (IDR-003)."""

import hashlib
import itertools
import json
import subprocess
import sys
from pathlib import Path

import pytest

from hash_chain import (
    EMPTY_HEAD,
    GENESIS_HASH,
    Entry,
    HashChain,
    Verification,
    canonical_json,
    entry_hash,
    verify,
)

SERVER = Path(__file__).resolve().parent.parent

GURMUKHI = "ਤੁਹਾਨੂੰ ਕਿੰਨੇ ਦਿਨਾਂ ਤੋਂ ਬੁਖਾਰ ਹੈ?"
TAMIL = "உங்களுக்கு எத்தனை நாட்களாக காய்ச்சல் இருக்கிறது?"


def turn(n: int, text: str = "Take 500 mg twice a day.") -> dict:
    """A settled turn record shaped like a CDR-002 TurnResult, as the visit store will chain it."""
    return {
        "turnId": f"t{n}",
        "speaker": "physician",
        "sourceLanguage": "en-CA",
        "targetLanguage": "pa-IN",
        "sourceText": text,
        "translation": GURMUKHI,
        "criticalValues": [{"kind": "dose", "source": "500 mg", "translated": "500 ਮਿ.ਗ੍ਰਾ.", "matched": True}],
        "confidence": 0.93,
        "status": "final",
    }


def chain_of(n: int) -> HashChain:
    chain = HashChain()
    for i in range(n):
        chain.append(turn(i))
    return chain


# ---------- canonical JSON ----------


def test_canonical_json_sorts_keys_without_whitespace_idr_003():
    assert canonical_json({"b": 1, "a": [1, {"d": 2, "c": 3}]}) == b'{"a":[1,{"c":3,"d":2}],"b":1}'


def test_canonical_json_ignores_key_order_idr_003():
    assert canonical_json({"x": 1, "y": {"p": 1, "q": 2}}) == canonical_json({"y": {"q": 2, "p": 1}, "x": 1})


def test_canonical_json_keeps_non_ascii_text_as_utf_8_idr_003():
    encoded = canonical_json({"pa": GURMUKHI, "ta": TAMIL})
    assert GURMUKHI.encode("utf-8") in encoded
    assert TAMIL.encode("utf-8") in encoded
    assert b"\\u" not in encoded


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), {1, 2}, object()])
def test_canonical_json_rejects_values_without_a_json_form_idr_003(bad):
    with pytest.raises((TypeError, ValueError)):
        canonical_json({"value": bad})


def test_entry_hash_is_sha_256_of_canonical_index_payload_and_prev_hash_idr_003():
    payload = {"text": TAMIL, "n": 1}
    expected = hashlib.sha256(
        json.dumps(
            {"index": 3, "payload": payload, "prevHash": GENESIS_HASH},
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()
    assert entry_hash(3, payload, GENESIS_HASH) == expected


# ---------- appending ----------


def test_empty_chain_verifies_with_empty_head_idr_003():
    chain = HashChain()
    result = chain.verify()
    assert result == Verification(head_hash=EMPTY_HEAD, broken_at=None)
    assert result.ok
    assert result.status == "verified"
    assert len(chain) == 0
    assert chain.head_hash == EMPTY_HEAD


def test_appends_link_each_entry_to_the_one_before_idr_003():
    chain = chain_of(4)
    entries = chain.entries
    assert [e.index for e in entries] == [0, 1, 2, 3]
    assert entries[0].prev_hash == GENESIS_HASH
    for before, after in itertools.pairwise(entries):
        assert after.prev_hash == before.hash
    for e in entries:
        assert e.hash == entry_hash(e.index, e.payload, e.prev_hash)
        assert len(e.hash) == 64
    assert chain.verify() == Verification(head_hash=entries[-1].hash)


def test_append_returns_the_stored_entry_idr_003():
    chain = HashChain()
    entry = chain.append(turn(0))
    assert chain.entries == (entry,)
    assert entry.payload == turn(0)


def test_head_hash_changes_with_every_append_idr_003():
    chain = HashChain()
    heads = [chain.head_hash]
    for i in range(5):
        chain.append(turn(i))
        heads.append(chain.head_hash)
        assert chain.verify().head_hash == chain.head_hash
    assert len(set(heads)) == len(heads)


def test_identical_payloads_still_get_distinct_hashes_idr_003():
    chain = HashChain()
    first = chain.append({"text": "yes"})
    second = chain.append({"text": "yes"})
    assert first.hash != second.hash
    assert chain.verify().ok


def test_amendments_chain_alongside_segments_idr_003():
    chain = chain_of(2)
    chain.append({"segmentId": "t1", "by": "patient", "action": "amend", "newText": TAMIL})
    assert chain.verify().ok


def test_caller_mutation_after_append_does_not_alter_the_record_idr_003():
    chain = HashChain()
    payload = turn(0)
    chain.append(payload)
    payload["sourceText"] = "Take 5000 mg twice a day."
    payload["criticalValues"][0]["source"] = "5000 mg"
    assert chain.entries[0].payload == turn(0)
    assert chain.verify().ok


def test_append_rejects_a_payload_json_cannot_encode_and_leaves_the_chain_unchanged_idr_003():
    chain = chain_of(1)
    head = chain.head_hash
    with pytest.raises(ValueError):
        chain.append({"confidence": float("nan")})
    with pytest.raises(TypeError):
        chain.append({"when": object()})
    assert len(chain) == 1
    assert chain.head_hash == head


def test_non_ascii_payloads_round_trip_and_verify_idr_003():
    chain = HashChain()
    chain.append(turn(0, GURMUKHI))
    chain.append(turn(1, TAMIL))
    assert chain.entries[0].payload["sourceText"] == GURMUKHI
    assert chain.entries[1].payload["sourceText"] == TAMIL
    assert chain.verify().ok
    restored = HashChain.from_wire(json.loads(json.dumps(chain.wire(), ensure_ascii=False)))
    assert restored.verify() == chain.verify()


def test_non_ascii_change_of_one_character_is_detected_idr_003():
    chain = HashChain()
    chain.append(turn(0, TAMIL))
    chain.tamper(0, payload=turn(0, TAMIL.replace("எத்தனை", "எத்தன")))
    assert chain.verify().broken_at == 0


# ---------- tampering ----------


@pytest.mark.parametrize("target", [0, 2, 4])
def test_altered_payload_breaks_at_that_entry_idr_003(target):
    chain = chain_of(5)
    head = chain.head_hash
    altered = turn(target, "Take 5000 mg twice a day.")
    chain.tamper(target, payload=altered)
    result = chain.verify()
    assert result.broken_at == target
    assert result.status == "broken"
    assert not result.ok
    assert result.head_hash == head
    assert chain.entries[target].payload == altered


@pytest.mark.parametrize("target", [0, 2, 4])
def test_altered_prev_hash_breaks_at_that_entry_idr_003(target):
    chain = chain_of(5)
    chain.tamper(target, prev_hash="f" * 64)
    assert chain.verify().broken_at == target


@pytest.mark.parametrize("target", [0, 2, 4])
def test_altered_hash_breaks_at_that_entry_idr_003(target):
    chain = chain_of(5)
    chain.tamper(target, hash="f" * 64)
    assert chain.verify().broken_at == target


def test_rehashed_entry_still_breaks_at_the_next_link_idr_003():
    chain = chain_of(5)
    original = chain.entries[2]
    payload = turn(2, "Take 5000 mg twice a day.")
    chain.tamper(2, payload=payload, hash=entry_hash(2, payload, original.prev_hash))
    assert chain.verify().broken_at == 3


def test_rehashed_last_entry_is_the_known_limit_of_an_unanchored_chain_idr_003():
    # IDR-003 consequence: no protection against rewriting the head; external anchoring is roadmap.
    chain = chain_of(3)
    last = chain.entries[2]
    payload = turn(2, "rewritten")
    chain.tamper(2, payload=payload, hash=entry_hash(2, payload, last.prev_hash))
    assert chain.verify().ok


def test_first_broken_index_is_reported_when_several_entries_are_altered_idr_003():
    chain = chain_of(6)
    chain.tamper(4, payload={"text": "later"})
    chain.tamper(1, payload={"text": "earlier"})
    assert chain.verify().broken_at == 1


def test_removed_entry_breaks_at_its_position_idr_003():
    entries = list(chain_of(5).entries)
    del entries[2]
    assert verify(entries).broken_at == 2


def test_removed_first_entry_breaks_at_zero_idr_003():
    assert verify(list(chain_of(3).entries)[1:]).broken_at == 0


def test_reordered_entries_break_at_the_first_moved_position_idr_003():
    entries = list(chain_of(4).entries)
    entries[1], entries[2] = entries[2], entries[1]
    assert verify(entries).broken_at == 1


def test_truncated_chain_verifies_with_the_new_head_idr_003():
    # Dropping the tail is undetectable without anchoring, but the head hash moves, so a
    # head published earlier no longer matches.
    chain = chain_of(4)
    published = chain.head_hash
    truncated = verify(list(chain.entries)[:3])
    assert truncated.ok
    assert truncated.head_hash != published


def test_unserialisable_tampered_payload_reports_broken_rather_than_raising_idr_003():
    chain = chain_of(3)
    chain.tamper(1, payload={"confidence": float("nan")})
    assert chain.verify().broken_at == 1


def test_tamper_rejects_an_index_out_of_range_idr_003():
    chain = chain_of(2)
    with pytest.raises(IndexError):
        chain.tamper(2, payload={})
    with pytest.raises(IndexError):
        chain.tamper(-1, payload={})
    with pytest.raises(IndexError):
        HashChain().tamper(0, payload={})


def test_tamper_needs_a_field_to_change_idr_003():
    chain = chain_of(1)
    with pytest.raises(ValueError):
        chain.tamper(0)
    assert chain.verify().ok


def test_entries_cannot_be_altered_in_place_idr_003():
    chain = chain_of(2)
    entries = chain.entries
    with pytest.raises(AttributeError):
        entries[0].hash = "f" * 64  # type: ignore[misc]
    assert isinstance(entries, tuple)
    assert chain.verify().ok


def test_tamper_then_append_still_reports_the_tampered_entry_idr_003():
    chain = chain_of(3)
    chain.tamper(1, payload={"text": "altered"})
    chain.append(turn(3))
    result = chain.verify()
    assert result.broken_at == 1
    assert result.head_hash == chain.head_hash


# ---------- wire shape ----------


def test_wire_shape_is_index_payload_prev_hash_and_hash_idr_003():
    chain = chain_of(2)
    wire = chain.wire()
    assert [set(item) for item in wire] == [{"index", "payload", "prevHash", "hash"}] * 2
    assert wire[1]["prevHash"] == wire[0]["hash"]
    assert [Entry.from_wire(item) for item in wire] == list(chain.entries)


def test_wire_copy_cannot_alter_the_chain_idr_003():
    chain = chain_of(1)
    chain.wire()[0]["payload"]["sourceText"] = "changed"
    assert chain.verify().ok


def test_chain_rebuilt_from_altered_wire_reports_the_break_idr_003():
    wire = chain_of(4).wire()
    wire[2]["payload"]["sourceText"] = "Take 5000 mg twice a day."
    assert HashChain.from_wire(wire).verify().broken_at == 2


# ---------- determinism ----------


def test_hashes_are_deterministic_across_chains_idr_003():
    assert chain_of(4).wire() == chain_of(4).wire()


def test_hashes_are_deterministic_across_processes_idr_003():
    # A fresh interpreter with a different hash seed must produce the same head hash.
    script = (
        "from hash_chain import HashChain\n"
        "c = HashChain()\n"
        f"c.append({{'b': {GURMUKHI!r}, 'a': [1, 2.5, None, True], 'c': {{'z': 1, 'y': {TAMIL!r}}}}})\n"
        "c.append({'turnId': 't1'})\n"
        "print(c.head_hash)\n"
    )
    heads = {
        subprocess.run(
            [sys.executable, "-c", script],
            cwd=SERVER,
            env={"PYTHONHASHSEED": seed, "PYTHONPATH": str(SERVER)},
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        for seed in ("0", "1", "12345")
    }
    in_process = HashChain()
    in_process.append({"c": {"y": TAMIL, "z": 1}, "a": [1, 2.5, None, True], "b": GURMUKHI})
    in_process.append({"turnId": "t1"})
    assert heads == {in_process.head_hash}


def test_known_vector_pins_the_hash_format_idr_003():
    # Pins canonical JSON and SHA-256 so a later refactor cannot silently change every hash.
    chain = HashChain()
    entry = chain.append({"text": "ਬੁਖਾਰ"})
    canonical = '{"index":0,"payload":{"text":"ਬੁਖਾਰ"},"prevHash":"' + GENESIS_HASH + '"}'
    assert entry.hash == hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    assert entry.hash == "a580a0ce5d19446b1a82287ea30e3153361686696d4301a9bf6a5243c5d33f1d"
