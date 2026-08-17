#!/usr/bin/env python3
from __future__ import annotations
import argparse, re, urllib.error, urllib.request
from pathlib import Path
from urllib.parse import urlparse
MARKDOWN_LINK=re.compile(r"\[[^\]]+\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
RAW_URL=re.compile(r"https?://[^\s)>'\"]+")
def iter_files(root: Path):
    excluded={'.git','.venv','venv','node_modules','__pycache__'}
    seen=set()
    for pattern in ['**/*.md','**/*.rst','**/*.html','**/*.py','**/*.yml','**/*.yaml']:
        for path in root.glob(pattern):
            if path in seen or any(part in excluded for part in path.parts):
                continue
            if path.is_file():
                seen.add(path); yield path
def links_in_file(path: Path):
    text=path.read_text(encoding='utf-8', errors='ignore')
    for m in MARKDOWN_LINK.finditer(text): yield m.group(1).strip()
    for m in RAW_URL.finditer(text): yield m.group(0).strip().rstrip('.,;')
def check_local(source: Path, root: Path, link: str):
    if link.startswith('#') or link.startswith('mailto:'): return None
    parsed=urlparse(link)
    if parsed.scheme in {'http','https'}: return None
    if parsed.scheme and parsed.scheme!='file': return None
    target_text=parsed.path or link.split('#',1)[0]
    if not target_text: return None
    target=(source.parent/target_text).resolve()
    try: target.relative_to(root.resolve())
    except ValueError: return f'local link escapes project root: {link}'
    if not target.exists(): return f'broken local link: {link}'
    return None
def check_remote(link: str, timeout: int):
    if urlparse(link).scheme not in {'http','https'}: return None
    req=urllib.request.Request(link, method='HEAD', headers={'User-Agent':'TYAKXA-CI-LinkChecker/1.0'})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as res:
            if res.status>=400: return f'remote link returned HTTP {res.status}: {link}'
    except urllib.error.HTTPError as exc:
        if exc.code>=400 and exc.code!=405: return f'remote link returned HTTP {exc.code}: {link}'
    except Exception as exc: return f'remote link failed: {link} ({exc})'
    return None
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--root',default='.'); ap.add_argument('--remote',action='store_true'); ap.add_argument('--timeout',type=int,default=8); args=ap.parse_args()
    root=Path(args.root).resolve(); errors=[]; checked=0
    for f in iter_files(root):
        for link in links_in_file(f):
            checked+=1; err=check_local(f,root,link)
            if not err and args.remote: err=check_remote(link,args.timeout)
            if err: errors.append(f'{f.relative_to(root)}: {err}')
    if errors:
        print('Link check failed:'); [print(f'- {e}') for e in errors]; return 1
    print(f'Link check ok ({checked} links scanned)'); return 0
if __name__=='__main__': raise SystemExit(main())
