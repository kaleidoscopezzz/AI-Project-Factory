"""Verify reference evidence file existence, PNG headers and ZIP SHA without changing it."""
import hashlib
import json
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = Path('C:/910Program')

def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def main():
    folder = REFERENCE / 'docs/screenshots/goal-0'
    evidence = json.loads((folder / 'evidence.json').read_text(encoding='utf-8-sig'))
    screenshots = []
    for entry in evidence['screenshots']:
        path = folder / entry['filename']
        with path.open('rb') as stream:
            header = stream.read(24)
        if header[:8] != b'\x89PNG\r\n\x1a\n':
            raise ValueError(f'Invalid PNG: {path}')
        size = struct.unpack('>II', header[16:24])
        expected = (entry['viewport']['width'], entry['viewport']['height'])
        screenshots.append({'file': entry['filename'], 'size': size,
                            'matches_evidence_viewport': size == expected})
    archive = REFERENCE / 'release-output/辽宁政法工作数字化平台-DEMO-Windows-x64.zip'
    actual = sha(archive)
    sidecar = Path(str(archive) + '.sha256.txt').read_text(encoding='utf-8-sig')
    result = {'method': 'read_only_file_inspection_not_business_retest',
              'screenshots': screenshots, 'screenshot_count': len(screenshots),
              'zip_sha256': actual, 'matches_external_sha_file': actual.lower() in sidecar.lower(),
              'matches_current_status_sha': actual == 'd92fa5bf324233ed6588605356c0008e0c1231ecf94b9af1b60c00a91c48e23b',
              'passed': all(s['matches_evidence_viewport'] for s in screenshots)
                        and actual.lower() in sidecar.lower()
                        and actual == 'd92fa5bf324233ed6588605356c0008e0c1231ecf94b9af1b60c00a91c48e23b'}
    out = ROOT / 'validation/reference/source-inspection.json'
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'screenshots': len(screenshots), 'zip_sha256': actual,
                      'passed': result['passed']}, ensure_ascii=False))
    return 0 if result['passed'] else 1

if __name__ == '__main__':
    raise SystemExit(main())
