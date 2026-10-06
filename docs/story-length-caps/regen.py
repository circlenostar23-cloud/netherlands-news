"""Plan airtime for a saved briefing and write a script from it: regen.py briefing.json out-prefix
writes out-prefix.json (the script) and out-prefix.plan.json (the briefing with airtime filled in)."""
import sys
from nlnews import script
from nlnews.models import Briefing
b = script.plan_airtime(Briefing.model_validate_json(open(sys.argv[1]).read()))
open(sys.argv[2] + ".plan.json", "w").write(b.model_dump_json(indent=2))
open(sys.argv[2] + ".json", "w").write(script.write_script(b).model_dump_json(indent=2))
