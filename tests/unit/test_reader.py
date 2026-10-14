"""U-RD-* 文件读取。"""
from pathlib import Path

from project_context.engine.reader import read_all, read_text_file


def test_read_utf8(tmp_path):
    p = tmp_path / "a.txt"
    p.write_text("hello\n世界\n", encoding="utf-8")
    text, trunc = read_text_file(p, 10 * 1024)
    assert text == "hello\n世界\n"
    assert trunc is False


def test_read_gbk(tmp_path):
    p = tmp_path / "a.py"
    p.write_bytes("# 注释\nprint('x')\n".encode("gbk"))
    text, _ = read_text_file(p, 10 * 1024)
    assert "注释" in text


def test_read_binary_returns_none(tmp_path):
    p = tmp_path / "b.bin"
    p.write_bytes(b"\x00\x01\x02" * 100)
    assert read_text_file(p, 10 * 1024) is None


def test_read_truncate(tmp_path):
    p = tmp_path / "big.txt"
    p.write_text("x" * 10000, encoding="utf-8")
    text, trunc = read_text_file(p, 1024)
    assert trunc is True
    assert len(text.encode("utf-8")) <= 1024


def test_read_crlf_normalized(tmp_path):
    p = tmp_path / "a.txt"
    p.write_bytes(b"a\r\nb\rc\n")
    text, _ = read_text_file(p, 1024)
    assert text == "a\nb\nc\n"


def test_read_missing(tmp_path):
    assert read_text_file(tmp_path / "nope.txt", 1024) is None


def test_read_all_only_py(py_node):
    contents = read_all(
        list(py_node.rglob("*")), py_node, max_file_size_kb=200, only_py=True,
    )
    assert "backend/app.py" in contents
    assert not any(k.endswith(".ts") for k in contents)