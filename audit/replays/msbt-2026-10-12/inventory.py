"""Compile, resolve loaded XML callbacks, and check every referenced addon asset."""
from pathlib import Path
import json
import re
import xml.etree.ElementTree as ET
from audit_replays import HERE, SOURCE, WORKSPACE, runtime, settings_runtime, table
from _native_reference import output_directory
import sys
sys.path.insert(0, str(WORKSPACE / "tools"))
from audit_addon import audit

baseline = audit(SOURCE)
assert not baseline["graph_errors"], baseline["graph_errors"]
l = settings_runtime()
compile_source = l.eval("function(s,n) local fn,err=loadstring(s,n);return fn~=nil,err end")
lua_modules = []
xml = []
callback_references = set()
assets = set()
for module in baseline["modules"]:
    path = SOURCE / module["path"]
    text = path.read_text("utf-8-sig")
    if path.suffix.lower() == ".lua":
        ok, error = compile_source(text, path.name)
        assert ok, (path.name, error)
        lua_modules.append(path.name)
    if path.suffix.lower() == ".xml":
        root = ET.fromstring(text)
        scripts = []
        for parent in root.iter():
            if parent.tag.split("}")[-1] != "Scripts":
                continue
            for child in parent:
                code = child.text or ""
                ok, error = compile_source("return function() " + code + " end", path.name)
                assert ok, (path.name, error)
                scripts.append(child.tag.split("}")[-1])
                callback_references.update(re.findall(r"\b(MikSBTOpt|MikSBT|MikCEH)\.(\w+)\s*\(", code))
        xml.append({"file": path.name, "scriptBodies": len(scripts),
                    "namedElements": len([e for e in root.iter() if e.get("name")]),
                    "events": sorted(set(scripts))})
    # Lua paths use doubled backslashes; XML paths use single backslashes.
    normalized = text.replace("\\\\", "\\")
    for match in re.finditer(r"Interface\\AddOns\\MikScrollingBattleText\\([^\"\s]+)", normalized, re.I):
        relative = match.group(1).replace("\\", "/")
        if Path(relative).suffix.lower() in {".ttf", ".tga", ".mp3", ".wav", ".blp"}:
            assets.add(relative)

for namespace, method in callback_references:
    assert l.eval(f"type({namespace}.{method})") == "function", (namespace, method)
for asset in assets:
    assert (SOURCE / asset).is_file(), asset

l.execute('''
optionEvents={};local seen={};
for _,area in ipairs({"INCOMING","OUTGOING","NOTIFICATION"}) do
  optionEvents[area]=0;
  for _,row in ipairs(MikSBTOpt[area.."_EVENTS"]) do
    assert(row.EventType and MikSBT.CurrentProfile.EventSettings[row.EventType],area);
    assert(not seen[row.EventType],row.EventType);seen[row.EventType]=true;optionEvents[area]=optionEvents[area]+1;
  end;
end;
unexposedDefaults={};for key in pairs(MikSBT.CurrentProfile.EventSettings) do if not seen[key] then table.insert(unexposedDefaults,key) end end;
defaultTriggerCount=0;for _ in pairs(MikSBT.CurrentProfile.Triggers) do defaultTriggerCount=defaultTriggerCount+1 end;
suppressionCount=0;for _ in pairs(MikSBT.CurrentProfile.Suppressions) do suppressionCount=suppressionCount+1 end;
''')
report = {
    "source": str(SOURCE), "loadedModules": baseline["module_count"],
    "lua51SyntaxCompiledOriginalSource": lua_modules,
    "lua50CompilerUsed": False,
    "xml": xml, "xmlCallbackReferences": sorted(".".join(v) for v in callback_references),
    "allAddonCallbackReferencesResolved": True,
    "uniqueAddonAssets": len(assets), "allAddonAssetsExist": True,
    "assets": sorted(assets), "nativeAssetsVerified": False,
    "eventRows": table(l.globals().optionEvents),
    "defaultEventsWithoutOptionsRow": list(l.globals().unexposedDefaults.values()),
    "defaultTriggers": l.globals().defaultTriggerCount, "defaultSuppressions": l.globals().suppressionCount,
}
(output_directory() / "inventory.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print(json.dumps(report, indent=2))
