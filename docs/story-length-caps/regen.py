import sys
from nlnews import script
from nlnews.models import Briefing
b = Briefing.model_validate_json(open(sys.argv[1]).read())
open(sys.argv[2], "w").write(script.write_script(b).model_dump_json(indent=2))
