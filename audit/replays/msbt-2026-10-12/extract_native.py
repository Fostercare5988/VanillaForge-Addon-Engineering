"""Record deployed native-reference provenance outside the selected game."""
import json
from _native_reference import PROVENANCE, output_directory

output = output_directory() / "native-provenance.json"
output.write_text(json.dumps(PROVENANCE, indent=2) + "\n", encoding="utf-8")
print(json.dumps(PROVENANCE, indent=2))
