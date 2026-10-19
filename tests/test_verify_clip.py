"""--verify (check Gemini's cited timestamps against real frames) and --clip (cut a range)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

import gemini
import watch
from frames import get_metadata


def test_cited_timestamps_keeps_valid_stamps_in_order():
    text = 'At 00:10 the hook; 1:02:03 the demo; 00:10 again; range 01:20–01:35. Not 10:30:99 or 123:45.'
    assert gemini.cited_timestamps(text) == ['00:10', '1:02:03', '01:20', '01:35']


def _gemini(monkeypatch, text):
    monkeypatch.setenv('GEMINI_API_KEY', 'unit-key')
    monkeypatch.setattr(gemini, 'ask', lambda video, q, **kw: {
        'text': text, 'model': kw['model'], 'processing': 'agentic', 'total_tokens': 1})
    monkeypatch.setattr(gemini, 'upload_file', lambda path, key, **kw: {'name': 'files/x', 'uri': 'u', 'mime_type': 'video/mp4'})
    monkeypatch.setattr(gemini, 'delete_file', lambda name, key: None)


def _verify_paths(out: str) -> list[Path]:
    return [Path(line.split('`')[1]) for line in out.splitlines() if line.startswith('- `') and 'cited' in line]


def test_verify_extracts_a_frame_per_cited_timestamp(monkeypatch, capsys, cut_clip):
    _gemini(monkeypatch, 'Red at 00:01, then yellow at 00:04.')
    monkeypatch.setattr(sys, 'argv', ['watch', str(cut_clip), '--verify'])
    assert watch.main() == 0
    out = capsys.readouterr().out
    assert '## Verify frames' in out and 'Gemini cited 2 timestamps; 2 real frames' in out
    paths = _verify_paths(out)
    assert len(paths) == 2 and all(p.is_file() for p in paths), 'frames must survive for the agent to read'
    assert 'cited 00:01' in out and 'cited 00:04' in out


def test_verify_downloads_youtube_only_when_asked(monkeypatch, capsys, cut_clip, tmp_path):
    _gemini(monkeypatch, 'It changes at 00:02.')
    calls = []
    monkeypatch.setattr(watch, 'download', lambda src, out_dir, **kw: calls.append(src) or {'video_path': str(cut_clip)})
    monkeypatch.setattr(sys, 'argv', ['watch', 'https://youtu.be/abc', '--verify'])
    assert watch.main() == 0
    assert calls == ['https://youtu.be/abc']
    assert len(_verify_paths(capsys.readouterr().out)) == 1


def test_verify_without_stamps_keeps_the_answer_and_cleans_up(monkeypatch, capsys, cut_clip, tmp_path):
    _gemini(monkeypatch, 'It is a colourful video.')
    out_dir = tmp_path / 'out'
    monkeypatch.setattr(sys, 'argv', ['watch', str(cut_clip), '--verify', '--out-dir', str(out_dir)])
    assert watch.main() == 0
    out = capsys.readouterr().out
    assert 'It is a colourful video.' in out and 'Verification unavailable: Gemini cited no timestamps' in out
    assert list(out_dir.iterdir()) == []


def test_clip_cuts_the_exact_range(monkeypatch, capsys, cut_clip, tmp_path):
    target = tmp_path / 'cuts' / 'clip.mp4'
    monkeypatch.setattr(sys, 'argv', ['watch', str(cut_clip), '--clip', str(target), '--start', '1', '--end', '3'])
    assert watch.main() == 0
    assert '**Saved:**' in capsys.readouterr().out
    assert get_metadata(str(target))['duration_seconds'] == pytest.approx(2.0, abs=0.15)
    assert cut_clip.is_file()


def test_clip_needs_a_range(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, 'argv', ['watch', 'video.mp4', '--clip', str(tmp_path / 'c.mp4'), '--start', '1'])
    with pytest.raises(SystemExit) as exc:
        watch.main()
    assert exc.value.code == 2


def test_clip_never_overwrites(monkeypatch, cut_clip, tmp_path):
    target = tmp_path / 'clip.mp4'
    target.write_bytes(b'keep me')
    monkeypatch.setattr(sys, 'argv', ['watch', str(cut_clip), '--clip', str(target), '--start', '1', '--end', '2'])
    with pytest.raises(SystemExit, match='already exists'):
        watch.main()
    assert target.read_bytes() == b'keep me'
