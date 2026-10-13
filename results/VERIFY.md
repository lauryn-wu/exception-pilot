# Verify published archives offline

From the repository root, with Python 3 and no network access:

```bash
python3 - <<'PY'
import hashlib, json, zipfile
from pathlib import Path
root = Path('results')
for line in (root / 'SHA256SUMS').read_text().splitlines():
    expected, name = line.split('  ', 1)
    assert hashlib.sha256((root / name).read_bytes()).hexdigest() == expected, name
manifest = json.loads((root / 'manifest.json').read_text())
for archive in manifest['archives']:
    path = Path(archive['path'])
    assert path.stat().st_size == archive['bytes'], str(path)
    assert hashlib.sha256(path.read_bytes()).hexdigest() == archive['sha256'], str(path)
    expected = json.loads(Path(archive['member_manifest']).read_text())['members']
    with zipfile.ZipFile(path) as z:
        names = [i.filename for i in z.infolist() if not i.is_dir()]
        assert len(names) == len(set(names)) and set(names) == set(expected), str(path)
        for name in names:
            data = z.read(name)
            assert len(data) == expected[name]['bytes'], name
            assert hashlib.sha256(data).hexdigest() == expected[name]['sha256'], name
print('All archive and member checksums passed.')
PY
```

Extract only into a new temporary directory; never overwrite a frozen run. Byte integrity does not establish scientific validity, protocol success or model compatibility. Credentials and downloaded model/tokenizer assets are excluded. The checksum list omits itself.
